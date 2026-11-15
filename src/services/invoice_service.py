"""Invoice use cases: the one place invoice facts are written.

Routes call these functions; tools never write the database. A tool that
changes money or status is HITL-gated, so it only proposes the change in agent
state. Once the user approves, the resume route hands the agent's response to
apply_approved_outcome, which validates it and commits it.

    tool --(state)--> user approves --> resume route --> apply_approved_outcome --> db
                                                                                   |
    agent checkpoint <-- sync_agent_state_from_invoice (api/index.py) <------------+

The rules themselves live in src/domain/invoice.py; this module reads the
invoice, applies them and saves the result.
"""
import logging
from typing import Optional

from src import db
from src.domain.invoice import (  # noqa: F401  (re-exported for existing callers)
    COMMITTABLE_BY_TOOL,
    MAX_CLIENT_NAME_LENGTH,
    MAX_EMAIL_LENGTH,
    MAX_ESCALATION_LEVEL,
    InvalidClientDetails,
    approved_changes,
    clean_client_details,
    compute_balance,
    escalation_target,
    invoice_state,
    is_escalation_level,
    parse_follow_up_date,
)

logger = logging.getLogger("invoicechaser")

invoice_state_from_db = invoice_state

_REJECTED_MESSAGES = {
    "amount_paid": "Ignoring invalid amount_paid %r for invoice %s",
    "follow_up_date": "Ignoring invalid follow_up_date %r for invoice %s",
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
    updates, rejected = approved_changes(invoice, response, approved_tool)
    for field, value in rejected:
        if field == "status":
            logger.warning("Ignoring status %r from %s for invoice %s", value, approved_tool, invoice_id)
        else:
            logger.warning(_REJECTED_MESSAGES[field], value, invoice_id)
    if not updates:
        return invoice_state(invoice)
    updated = db.update_invoice(invoice_id, only_if_unpaid=True, **updates)
    return invoice_state(updated) if updated else None


def set_escalation_level(invoice_id: str, new_level) -> bool:
    """Raise the invoice's escalation level. Never lowers it. Returns True if it changed."""
    if not is_escalation_level(new_level):
        return False
    invoice = db.get_invoice(invoice_id)
    if not invoice:
        return False
    target = escalation_target(int(invoice.get("escalation_level") or 0), new_level)
    if target is None:
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
    allowed = clean_client_details(updates)
    if allowed:
        db.update_invoice(invoice_id, **allowed)
    return allowed
