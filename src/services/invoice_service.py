"""Invoice business rules: the one place invoice facts are written.

Routes call these functions; tools never write the database. A tool that
changes money or status is HITL-gated, so it only proposes the change in agent
state. Once the user approves, the resume route hands the agent's response to
apply_approved_outcome, which validates it and commits it.

    tool ──(state)──▶ user approves ──▶ resume route ──▶ apply_approved_outcome ──▶ db
                                                                                   │
    agent checkpoint ◀── sync_agent_state_from_invoice (api/index.py) ◀────────────┘

Status values: active (default) → pending (client promised to pay by
follow_up_date) → paid (settled). Nothing leaves paid.
"""
import logging
import math
import re
from datetime import date
from typing import Optional

from src import db

logger = logging.getLogger("invoicechaser")

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


def invoice_state_from_db(invoice: dict) -> dict:
    amount_paid = float(invoice.get("amount_paid", 0) or 0)
    invoice_amount = float(invoice.get("invoice_amount", 0) or 0)
    return {
        "client_name": invoice.get("client_name", ""),
        "client_email": invoice.get("client_email", ""),
        "invoice_id": db.parse_public_invoice_id(invoice["id"]),
        "invoice_amount": invoice_amount,
        "amount_paid": amount_paid,
        "balance_due": compute_balance(invoice_amount, amount_paid),
        "days_overdue": invoice.get("days_overdue", 0) or 0,
        "jurisdiction": invoice.get("jurisdiction", "") or "",
        "escalation_level": invoice.get("escalation_level", 1) or 1,
        "status": invoice.get("status", "active") or "active",
        "follow_up_date": invoice.get("follow_up_date") or "",
    }


def apply_approved_outcome(invoice_id: str, response: dict, approved_tool: Optional[str]) -> Optional[dict]:
    """Commit the payment and status changes the user just approved.

    Only the fields *approved_tool* is allowed to change are read from
    *response* (the agent state after the approved run). Returns the saved
    invoice as agent state, or None if the invoice is gone. A settled invoice
    is never changed, even by a request racing the settle.
    """
    invoice = db.get_invoice(invoice_id)
    if not invoice:
        logger.warning("apply_approved_outcome: invoice %s not found", invoice_id)
        return None
    if (invoice.get("status") or "active") == "paid" or approved_tool not in COMMITTABLE_BY_TOOL:
        return invoice_state_from_db(invoice)
    fields, statuses = COMMITTABLE_BY_TOOL[approved_tool]

    invoice_amount = float(invoice.get("invoice_amount", 0) or 0)
    updates = {}

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
        logger.warning("Ignoring invalid amount_paid %r for invoice %s", new_paid_raw, invoice_id)

    new_status = response.get("status")
    if "status" in fields and isinstance(new_status, str) and new_status != (invoice.get("status") or "active"):
        if new_status in statuses:
            updates["status"] = new_status
        else:
            logger.warning("Ignoring status %r from %s for invoice %s", new_status, approved_tool, invoice_id)

    if "follow_up_date" in fields and "follow_up_date" in response and response.get("status") == "pending":
        follow_up_date = parse_follow_up_date(response.get("follow_up_date"))
        if follow_up_date is None:
            logger.warning("Ignoring invalid follow_up_date %r for invoice %s", response.get("follow_up_date"), invoice_id)
        elif follow_up_date != invoice.get("follow_up_date"):
            updates["follow_up_date"] = follow_up_date
    if updates.get("status") == "pending" and "follow_up_date" not in updates and not invoice.get("follow_up_date"):
        # A promise without a readable date isn't a promise we can follow up on.
        updates.pop("status")

    if not updates:
        return invoice_state_from_db(invoice)
    updated = db.update_invoice(invoice_id, only_if_unpaid=True, **updates)
    return invoice_state_from_db(updated) if updated else None


def set_escalation_level(invoice_id: str, new_level) -> bool:
    """Raise the invoice's escalation level. Never lowers it. Returns True if it changed."""
    if not isinstance(new_level, int) or isinstance(new_level, bool):
        return False
    invoice = db.get_invoice(invoice_id)
    if not invoice:
        return False
    current = int(invoice.get("escalation_level") or 0)
    target = min(MAX_ESCALATION_LEVEL, new_level)
    if target <= current:
        return False
    db.update_invoice(invoice_id, escalation_level=target)
    return True


def settle(invoice_id: str, user_id: Optional[str]) -> bool:
    """Mark the invoice paid and log it, exactly once. Returns True for the call that settled it."""
    if not db.mark_invoice_settled(invoice_id):
        return False
    db.add_communication(
        invoice_id=invoice_id,
        comm_type="invoice_settled",
        subject="Marked as settled",
        content="Marked as settled. The agent will take no further action on this invoice.",
        direction="internal",
        user_id=user_id,
    )
    return True


def update_client_details(invoice_id: str, updates: dict) -> dict:
    """Save the client's name and email. Other fields are ignored. Returns what was saved.

    Raises InvalidClientDetails, saving nothing, if either value is unusable.
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
    if allowed:
        db.update_invoice(invoice_id, **allowed)
    return allowed
