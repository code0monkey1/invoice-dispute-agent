"""Route inbound provider events to the invoice they belong to."""

import logging
from collections.abc import Callable
from email.utils import parseaddr

from src.ports import CommunicationLog, InvoiceStore

logger = logging.getLogger("invoicechaser")


class InboundReplyUseCases:
    def __init__(
        self,
        *,
        invoices: InvoiceStore,
        communications: CommunicationLog,
        fetch_email: Callable[[str], dict],
        parse_token: Callable[[list[str]], str | None],
        plain_text: Callable[[dict], str],
        inbound_domain: Callable[[], str | None],
        new_token: Callable[[], str],
    ):
        self._invoices = invoices
        self._communications = communications
        self._fetch_email = fetch_email
        self._parse_token = parse_token
        self._plain_text = plain_text
        self._inbound_domain = inbound_domain
        self._new_token = new_token

    def ensure_reply_token(self, invoice_id: str) -> str | None:
        """Return a stable tracking token when inbound email is configured."""
        if not self._inbound_domain():
            return None
        invoice = self._invoices.get_invoice(invoice_id) or {}
        if invoice.get("reply_token"):
            return invoice["reply_token"]
        token = self._new_token()
        try:
            updated = self._invoices.update_invoice(invoice_id, reply_token=token)
        except Exception:
            logger.exception(
                "Could not save a reply token for invoice %s (is the reply_token column missing?)",
                invoice_id,
            )
            return None
        return token if (updated or {}).get("reply_token") == token else None

    def process(self, event: dict, handle_verified: Callable[[dict, str, str, str], None]) -> str:
        if event.get("type") != "email.received":
            return "ignored"
        data = event.get("data") or {}
        recipients = [
            *list(data.get("to") or []),
            *list(data.get("cc") or []),
            *list(data.get("received_for") or []),
        ]
        token = self._parse_token(recipients)
        invoice = self._invoices.get_invoice_by_reply_token(token) if token else None
        if not invoice:
            logger.info("Inbound email with no matching reply token; ignoring")
            return "ignored"

        body = ""
        if data.get("email_id"):
            try:
                body = self._plain_text(self._fetch_email(data["email_id"]))
            except Exception:
                logger.exception("Could not fetch received email %s", data.get("email_id"))

        sender = parseaddr(data.get("from", ""))[1].strip().lower()
        expected = (invoice.get("client_email") or "").strip().lower()
        if not sender or sender != expected:
            self._communications.add_communication(
                invoice_id=invoice["id"],
                comm_type="client_reply_unverified",
                subject=data.get("subject", ""),
                content=body[:2000],
                direction="inbound",
                user_id=invoice.get("user_id"),
            )
            return "stored_unverified"

        handle_verified(invoice, data.get("from", ""), data.get("subject", ""), body)
        return "stored"
