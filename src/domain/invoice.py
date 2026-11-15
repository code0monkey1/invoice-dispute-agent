"""Invoice rules: balances, invoice numbers, what an approval may commit,
escalation, and which client details can be saved.

Pure functions over plain dicts. Reading and writing invoices is the
caller's job (src/services/invoice_service.py).

Status values: active (default) -> pending (client promised to pay by
follow_up_date) -> paid (settled). Nothing leaves paid.
"""
import base64
import math
import re
from datetime import date
from typing import Optional

INVOICE_ID_SEPARATOR = "__inv__"

# What approving each payment tool may commit: the fields it may change and
# the statuses it may set. Approving anything else (an email draft) commits no
# payment or status change, whatever the resumed run left in agent state.
# "paid" can also come from update_invoice when amount_paid reaches the total.
COMMITTABLE_BY_TOOL = {
    "mark_invoice_paid": ({"amount_paid", "status"}, {"paid"}),
    "record_partial_payment": ({"amount_paid", "status"}, {"active", "pending", "paid"}),
    "mark_invoice_pending": ({"status", "follow_up_date"}, {"pending"}),
}
MAX_ESCALATION_LEVEL = 3
MAX_CLIENT_NAME_LENGTH = 200
MAX_EMAIL_LENGTH = 254
# One plain address: no spaces, commas, semicolons or angle brackets, so it
# can't turn into a recipient list.
_SINGLE_EMAIL_RE = re.compile(r'^[^\s@,;<>"]+@[^\s@,;<>"]+\.[^\s@,;<>"]+$')


class InvalidClientDetails(ValueError):
    """A client name or email the user submitted can't be saved."""


def compute_balance(invoice_amount: float, amount_paid: float) -> float:
    return max(0, float(invoice_amount or 0) - float(amount_paid or 0))


def parse_follow_up_date(value) -> Optional[str]:
    """Return *value* as a YYYY-MM-DD string, or None if it isn't a real date."""
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip()).isoformat()
    except ValueError:
        return None


def build_invoice_storage_id(user_id: str, invoice_id: str) -> str:
    """Create a per-user storage ID while preserving the public invoice number."""
    encoded = base64.urlsafe_b64encode(invoice_id.encode()).decode().rstrip("=")
    return f"{user_id}{INVOICE_ID_SEPARATOR}{encoded}"


def parse_public_invoice_id(storage_id: str) -> str:
    """Recover the original invoice number from a storage ID when possible."""
    if INVOICE_ID_SEPARATOR not in storage_id:
        return storage_id

    _, encoded = storage_id.split(INVOICE_ID_SEPARATOR, 1)
    try:
        padding = "=" * (-len(encoded) % 4)
        return base64.urlsafe_b64decode(f"{encoded}{padding}".encode()).decode()
    except Exception:
        return storage_id


def invoice_state(invoice: dict) -> dict:
    """The invoice as the agent sees it, with the database's blanks filled in."""
    amount_paid = float(invoice.get("amount_paid", 0) or 0)
    invoice_amount = float(invoice.get("invoice_amount", 0) or 0)
    return {
        "client_name": invoice.get("client_name", ""),
        "client_email": invoice.get("client_email", ""),
        "invoice_id": parse_public_invoice_id(invoice["id"]),
        "invoice_amount": invoice_amount,
        "amount_paid": amount_paid,
        "balance_due": compute_balance(invoice_amount, amount_paid),
        "days_overdue": invoice.get("days_overdue", 0) or 0,
        "jurisdiction": invoice.get("jurisdiction", "") or "",
        "escalation_level": invoice.get("escalation_level", 1) or 1,
        "status": invoice.get("status", "active") or "active",
        "follow_up_date": invoice.get("follow_up_date") or "",
    }


def approved_changes(invoice: dict, response: dict, approved_tool: Optional[str]) -> tuple[dict, list[tuple[str, object]]]:
    """What approving *approved_tool* commits to *invoice*, from the agent's *response*.

    Returns (updates, rejected): the fields to save, and the (field, value)
    pairs the agent proposed that may not be saved. Only the fields the tool
    may change are read. A settled invoice is never changed.
    """
    if (invoice.get("status") or "active") == "paid" or approved_tool not in COMMITTABLE_BY_TOOL:
        return {}, []
    fields, statuses = COMMITTABLE_BY_TOOL[approved_tool]
    invoice_amount = float(invoice.get("invoice_amount", 0) or 0)
    updates: dict = {}
    rejected: list[tuple[str, object]] = []

    new_paid_raw = response.get("amount_paid")
    if (
        "amount_paid" in fields
        and isinstance(new_paid_raw, (int, float))
        and not isinstance(new_paid_raw, bool)
        and math.isfinite(new_paid_raw)
    ):
        new_paid = max(0.0, min(invoice_amount, float(new_paid_raw)))
        if abs(new_paid - float(invoice.get("amount_paid", 0) or 0)) > 0.005:
            updates["amount_paid"] = new_paid
    elif new_paid_raw is not None and "amount_paid" in fields:
        rejected.append(("amount_paid", new_paid_raw))

    new_status = response.get("status")
    if "status" in fields and isinstance(new_status, str) and new_status != (invoice.get("status") or "active"):
        if new_status in statuses:
            updates["status"] = new_status
        else:
            rejected.append(("status", new_status))

    if "follow_up_date" in fields and "follow_up_date" in response and response.get("status") == "pending":
        follow_up_date = parse_follow_up_date(response.get("follow_up_date"))
        if follow_up_date is None:
            rejected.append(("follow_up_date", response.get("follow_up_date")))
        elif follow_up_date != invoice.get("follow_up_date"):
            updates["follow_up_date"] = follow_up_date
    if updates.get("status") == "pending" and "follow_up_date" not in updates and not invoice.get("follow_up_date"):
        # A promise without a readable date isn't a promise we can follow up on.
        updates.pop("status")
    return updates, rejected


def is_escalation_level(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def escalation_target(current: int, requested: int) -> Optional[int]:
    """The level to move to, or None. Escalation never goes down and stops at Legal."""
    target = min(MAX_ESCALATION_LEVEL, requested)
    return target if target > current else None


def clean_client_details(updates: dict) -> dict:
    """The client name and email from *updates*, tidied. Other fields are dropped.

    Raises InvalidClientDetails if either value is unusable.
    """
    allowed = {}
    name = updates.get("client_name")
    if name is not None:
        name = " ".join(str(name).split())
        if not name or len(name) > MAX_CLIENT_NAME_LENGTH:
            raise InvalidClientDetails(f"Client name must be 1-{MAX_CLIENT_NAME_LENGTH} characters.")
        allowed["client_name"] = name
    email = updates.get("client_email")
    if email is not None:
        email = str(email).strip()
        if len(email) > MAX_EMAIL_LENGTH or not _SINGLE_EMAIL_RE.match(email):
            raise InvalidClientDetails("Client email must be a single email address.")
        allowed["client_email"] = email
    return allowed
