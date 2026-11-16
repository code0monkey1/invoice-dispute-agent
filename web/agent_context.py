"""What the agent is told about the sender and the user's invoices.

The summary is prompt text: change its wording only on purpose (the live
eval checks the agent's behaviour with it). *store* is read on every call.
"""
import logging

from src.domain.invoice import compute_balance, parse_public_invoice_id
from src.state import FreelancerContext

logger = logging.getLogger("invoicechaser")


class AgentContexts:
    def __init__(self, store):
        self._store = store

    def summary(self, current_invoice_id: str, user_id: str) -> str:
        """Build a compact invoice-only context summary for the agent."""
        if not user_id:
            return ""
        try:
            invoices = self._store.get_invoices_by_user(user_id)
        except Exception:
            logger.exception("Failed to build invoice context for user %s", user_id)
            return ""

        current = next((inv for inv in invoices if inv["id"] == current_invoice_id), None)
        header = []
        if current:
            amount = float(current.get("invoice_amount", 0) or 0)
            balance = compute_balance(amount, float(current.get("amount_paid", 0) or 0))
            header = [
                "Current invoice (use these exact details in any email you draft):",
                f"  Invoice number: {parse_public_invoice_id(current['id'])}",
                f"  Client name: {current.get('client_name') or 'unknown'}",
                f"  Client email: {current.get('client_email') or 'unknown'}",
                f"  Invoice total: ${amount:,.2f}; balance due: ${balance:,.2f}",
                f"  Days overdue: {current.get('days_overdue', 0) or 0}; status: {current.get('status', 'active')}",
                # Level 3 looks up small-claims rules with it, and final notices name it.
                f"  Jurisdiction: {current.get('jurisdiction') or 'not set'}",
                *([f"  Client promised to pay by: {current['follow_up_date']}"] if current.get("follow_up_date") else []),
                "",
                "All invoices for this user:",
            ]

        listed = invoices[:12]
        try:
            communications = self._store.get_communications_for([inv["id"] for inv in listed])
        except Exception:
            logger.exception("Failed to read communications for user %s", user_id)
            communications = {}
        lines = []
        for invoice in listed:
            public_id = parse_public_invoice_id(invoice["id"])
            marker = "current" if invoice["id"] == current_invoice_id else "other"
            amount = float(invoice.get("invoice_amount", 0) or 0)
            paid = float(invoice.get("amount_paid", 0) or 0)
            balance = compute_balance(amount, paid)
            lines.append(
                f"- [{marker}] Invoice #{public_id}: {invoice.get('client_name', '')} "
                f"<{invoice.get('client_email', '')}>, status {invoice.get('status', 'active')}, "
                f"balance ${balance:,.2f}, {invoice.get('days_overdue', 0) or 0} days overdue."
                + (f" Promised to pay by {invoice['follow_up_date']}." if invoice.get("follow_up_date") else "")
            )
            comms = communications.get(invoice["id"], [])
            # Only our own outgoing subjects: inbound ones are written by outsiders.
            recent_subjects = [
                c.get("subject")
                for c in [c for c in comms if c.get("direction") != "inbound"][-3:]
                if c.get("subject")
            ]
            if recent_subjects:
                lines.append(f"  Recent communications: {'; '.join(recent_subjects)}")

        return "\n".join(header + lines)

    def for_invoice(self, invoice_id: str, user: dict | None = None) -> FreelancerContext:
        """Get FreelancerContext for an invoice.

        Priority: invoice-level sender overrides > authenticated user profile > defaults.
        Always carries ``user_id`` so downstream tools can route per-user side-effects
        (e.g. notifications) without re-deriving identity.
        """
        invoice = self._store.get_invoice(invoice_id)
        owner_id = (invoice or {}).get("user_id") or (user or {}).get("id", "")
        invoice_context_summary = self.summary(invoice_id, owner_id)

        if invoice and invoice.get("sender_name"):
            return FreelancerContext(
                freelancer_name=invoice["sender_name"],
                freelancer_email=invoice.get("sender_email") or (user or {}).get("email", "unknown@example.com"),
                business_name=invoice.get("sender_business") or invoice["sender_name"],
                user_id=owner_id,
                invoice_context_summary=invoice_context_summary,
            )
        if user:
            return FreelancerContext(
                freelancer_name=user.get("name") or "Unknown",
                freelancer_email=user.get("email") or "unknown@example.com",
                business_name=user.get("name", "My Business"),
                user_id=owner_id,
                invoice_context_summary=invoice_context_summary,
            )
        return FreelancerContext(user_id=owner_id, invoice_context_summary=invoice_context_summary)
