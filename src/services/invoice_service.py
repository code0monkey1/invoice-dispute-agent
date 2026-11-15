"""Invoice use cases: the one place invoice facts are written.

Routes call these functions; tools never write the database. Creating,
settling and editing invoices are in src/usecases/invoices.py; the approval
and escalation writes below move there with their routes (tasks 5.5, 5.7).

A tool that changes money or status is HITL-gated, so it only proposes the
change in agent state. Once the user approves, the resume route hands the agent's response to
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
from src.domain.invoice import (
    approved_changes,
    escalation_target,
    invoice_state,
    is_escalation_level,
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
