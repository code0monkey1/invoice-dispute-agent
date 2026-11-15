"""Invoice use cases: create, list, files, generated invoices, details, settle.

Stores and the agent session are injected (see src/ports.py), so these run
with in-memory fakes in tests/test_invoice_usecases.py. The rules come from
src/domain/invoice.py; HTTP status codes are the router's business.
"""
import logging
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime

from src.domain.invoice import (
    build_invoice_storage_id,
    clean_client_details,
    compute_balance,
    invoice_state,
    parse_public_invoice_id,
)
from src.ports import AgentSession, CommunicationLog, InvoiceStore

logger = logging.getLogger("invoicechaser")

INITIALIZATION_ERROR = "The dispute was created, but the AI chat state could not be initialized yet."
NO_COMMUNICATIONS = {"communication_count": 0, "outbound_count": 0, "last_communication_direction": None}


class InvoiceExists(ValueError):
    """The caller already has an invoice with this number."""


class InvalidStoragePath(ValueError):
    """A generated invoice points at a file outside the caller's own folder. args[0] is that folder."""


class InvalidDueDate(ValueError):
    """A generated invoice's due date isn't YYYY-MM-DD."""


def safe_filename(filename: str) -> str:
    base = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return cleaned or "invoice"


def present_invoice(invoice: dict | None) -> dict | None:
    """Add the user-facing invoice number to invoice payloads."""
    if not invoice:
        return None

    payload = dict(invoice)
    payload["invoice_id"] = parse_public_invoice_id(payload["id"])
    payload["amount_paid"] = float(payload.get("amount_paid", 0) or 0)
    payload["invoice_amount"] = float(payload.get("invoice_amount", 0) or 0)
    payload["balance_due"] = compute_balance(payload["invoice_amount"], payload["amount_paid"])
    return payload


class InvoiceUseCases:
    def __init__(self, invoices: InvoiceStore, communications: CommunicationLog, sessions: AgentSession):
        self._invoices = invoices
        self._communications = communications
        self._sessions = sessions

    def exists(self, user_id: str, public_id: str) -> bool:
        return bool(self._invoices.get_invoice(build_invoice_storage_id(user_id, public_id)))

    def create(self, user_id: str, fields: dict, *, file_metadata: dict | None = None) -> dict:
        """Save the invoice and start its agent conversation at the Friendly level.

        Raises InvoiceExists. If the agent state can't be written, the invoice
        is still kept and the result carries an initialization_error.
        """
        storage_id = build_invoice_storage_id(user_id, fields["invoice_id"])
        if self._invoices.get_invoice(storage_id):
            raise InvoiceExists(fields["invoice_id"])

        balance_due = compute_balance(fields["invoice_amount"], fields["amount_paid"])
        file_metadata = file_metadata or {}
        invoice = present_invoice(self._invoices.create_invoice(
            invoice_id=storage_id,
            user_id=user_id,
            client_name=fields["client_name"],
            client_email=fields["client_email"],
            invoice_amount=fields["invoice_amount"],
            amount_paid=fields["amount_paid"],
            days_overdue=fields["days_overdue"],
            jurisdiction=fields["jurisdiction"],
            status="paid" if balance_due <= 0 else "active",
            invoice_file_path=file_metadata.get("path"),
            invoice_file_name=file_metadata.get("name"),
            invoice_file_mime=file_metadata.get("mime"),
            invoice_file_size=file_metadata.get("size"),
        ))
        initial_state = {
            "client_name": fields["client_name"],
            "client_email": fields["client_email"],
            "invoice_id": fields["invoice_id"],
            "invoice_amount": fields["invoice_amount"],
            "amount_paid": fields["amount_paid"],
            "balance_due": balance_due,
            "days_overdue": fields["days_overdue"],
            "jurisdiction": fields["jurisdiction"],
            "escalation_level": 1,
            "status": "paid" if balance_due <= 0 else "active",
            "communication_history": [],
        }
        result = {"invoice": invoice, "messages": [], "interrupt": None, "state": initial_state}
        try:
            self._sessions.update_state(storage_id, initial_state)
        except Exception:
            logger.exception("Failed to initialize agent state for invoice %s", storage_id)
            return {**result, "initialization_error": INITIALIZATION_ERROR}
        invoice["communication_history"] = []
        return result

    def store_file(self, bucket: str, prefix: str, filename: str, content: bytes, content_type: str | None) -> dict:
        """Store an uploaded file under prefix/<random>/<safe name>. Returns its metadata."""
        name = safe_filename(filename)
        object_path = f"{prefix}/{uuid.uuid4().hex}/{name}"
        path = self._invoices.upload_invoice_file(bucket, object_path, content, content_type)
        return {"path": path, "name": name, "mime": content_type, "size": len(content)}

    def create_generated(self, user_id: str, fields: dict, *, today: date) -> dict:
        """Save an invoice for a PDF the caller already uploaded. The agent starts when chat opens.

        Raises InvalidStoragePath, InvoiceExists or InvalidDueDate, checked in that order.
        """
        import posixpath
        # normpath collapses '..' and '//' BEFORE the prefix check: a raw
        # startswith would accept "generated/{user}/../victim/foo.pdf" and let
        # an attacker register a row pointing at someone else's file.
        prefix = f"generated/{user_id}/"
        normalized = posixpath.normpath(fields["storage_path"])
        if not normalized.startswith(prefix) or ".." in normalized.split("/"):
            raise InvalidStoragePath(prefix)

        storage_id = build_invoice_storage_id(user_id, fields["invoice_id"])
        if self._invoices.get_invoice(storage_id):
            raise InvoiceExists(fields["invoice_id"])

        try:
            due = datetime.strptime(fields["due_date"], "%Y-%m-%d").date()
        except ValueError as exc:
            raise InvalidDueDate(fields["due_date"]) from exc

        invoice = self._invoices.create_invoice(
            invoice_id=storage_id,
            user_id=user_id,
            client_name=fields["client_name"],
            client_email=fields["client_email"],
            invoice_amount=fields["invoice_amount_cents"] / 100,
            amount_paid=0,
            days_overdue=max(0, (today - due).days),  # not due yet is not overdue
            jurisdiction=fields["jurisdiction"],
            status="active",
            invoice_file_path=fields["storage_path"],
            invoice_file_name=fields["file_name"],
            invoice_file_mime="application/pdf",
            invoice_file_size=fields["file_size"],
        )
        return present_invoice(invoice)

    def list_for_user(self, user_id: str) -> list[dict]:
        """The user's invoices with message counts and any draft waiting for approval."""
        invoices = self._invoices.get_invoices_by_user(user_id)
        # Aggregate metadata only; email bodies require an explicit history request.
        overviews = self._communications.get_communication_overviews([row["id"] for row in invoices])
        for row in invoices:
            row["communication_history"] = []
            row.update(overviews.get(row["id"], NO_COMMUNICATIONS))
        presented = [present_invoice(row) for row in invoices]
        open_ids = [row["id"] for row in presented if row.get("status") != "paid"]
        with ThreadPoolExecutor(max_workers=8) as pool:
            actions = dict(zip(open_ids, pool.map(self.pending_approval_action, open_ids)))
        for row in presented:
            action = actions.get(row["id"])
            row["pending_action"] = action
            row["awaiting_approval"] = action is not None
        return presented

    def pending_approval_action(self, invoice_id: str) -> str | None:
        """The tool name of a draft waiting for the user's approval, if any."""
        try:
            pending = self._sessions.pending(invoice_id)
        except Exception:
            logger.exception("Could not read agent state for invoice %s", invoice_id)
            return None
        return pending.action.get("name") if pending is not None else None

    def update_client_details(self, invoice_id: str, updates: dict):
        """Save the client's name and email and tell the agent. Returns the agent's state values.

        Raises InvalidClientDetails, saving nothing, if either value is unusable.
        """
        saved = clean_client_details(updates)
        if saved:
            self._invoices.update_invoice(invoice_id, **saved)
        self._sessions.update_state(invoice_id, saved)
        return self._sessions.get_state(invoice_id).values

    def update_sender(self, invoice_id: str, updates: dict) -> None:
        if updates:
            self._invoices.update_invoice(invoice_id, **updates)

    def settle(self, invoice_id: str, user_id: str | None) -> dict:
        """Mark the invoice paid and log it, exactly once, then tell the agent. Returns the invoice."""
        if self._invoices.mark_invoice_settled(invoice_id):
            self._communications.add_communication(
                invoice_id=invoice_id,
                comm_type="invoice_settled",
                subject="Marked as settled",
                content="Marked as settled. The agent will take no further action on this invoice.",
                direction="internal",
                user_id=user_id,
            )
            self.sync_session(invoice_id)
        updated = self._invoices.get_invoice(invoice_id)
        updated["communication_history"] = []
        return present_invoice(updated)

    def sync_session(self, invoice_id: str) -> dict | None:
        """Copy the saved invoice into the agent's state. Returns that state, or None if the invoice is gone.

        A failed write is logged, not raised: the database stays the source of truth.
        """
        invoice = self._invoices.get_invoice(invoice_id)
        if not invoice:
            return None
        persisted_state = invoice_state(invoice)
        try:
            read = self._sessions.read_before_sync(invoice_id, persisted_state)
            if read.sync_error is not None:
                raise read.sync_error
        except Exception:
            logger.exception("Failed to sync agent state for invoice %s", invoice_id)
        return persisted_state
