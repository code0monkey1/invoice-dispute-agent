"""Commit the invoice changes produced by an approved agent action."""

import logging

from src.domain.invoice import approved_changes, invoice_state
from src.ports import InvoiceStore

logger = logging.getLogger("invoicechaser")

_REJECTED_MESSAGES = {
    "amount_paid": "Ignoring invalid amount_paid %r for invoice %s",
    "follow_up_date": "Ignoring invalid follow_up_date %r for invoice %s",
}


class ApprovalUseCases:
    """Validate and persist only the fields the approved tool may change."""

    def __init__(self, invoices: InvoiceStore):
        self._invoices = invoices

    def apply_outcome(self, invoice_id: str, response: dict, approved_tool: str | None) -> dict | None:
        invoice = self._invoices.get_invoice(invoice_id)
        if not invoice:
            logger.warning("apply_outcome: invoice %s not found", invoice_id)
            return None

        updates, rejected = approved_changes(invoice, response, approved_tool)
        for field, value in rejected:
            if field == "status":
                logger.warning("Ignoring status %r from %s for invoice %s", value, approved_tool, invoice_id)
            else:
                logger.warning(_REJECTED_MESSAGES[field], value, invoice_id)

        if not updates:
            return invoice_state(invoice)
        updated = self._invoices.update_invoice(invoice_id, only_if_unpaid=True, **updates)
        return invoice_state(updated) if updated else None
