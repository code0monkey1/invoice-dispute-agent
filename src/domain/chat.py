"""Policy for deciding whether text belongs in an invoice conversation."""
import re
from collections.abc import Callable, Iterable, Mapping

from src.domain.invoice import parse_public_invoice_id

INVOICE_CHAT_KEYWORDS = {
    "invoice", "invoices", "payment", "paid", "pay", "payer", "balance", "due",
    "overdue", "client", "customer", "email", "mail", "draft", "send", "sent",
    "reminder", "deliver", "delivery", "attach", "attachment", "pdf", "amount",
    "status", "dispute", "chase", "follow", "follow-up", "escalate", "late",
    "fee", "fees", "legal", "demand", "notice", "owe", "owed", "owing",
    "tone", "firm", "firmer", "soft", "softer", "polite", "friendly", "formal",
    "rewrite", "reword", "edit", "shorter", "longer", "message", "letter",
    "reply", "respond", "response", "remind", "nudge", "approve", "reject",
    "escalation", "level", "court", "claims", "sue", "lawsuit", "lawyer",
    "interest", "contract", "terms", "deadline", "extension", "installment",
    "instalments", "refund", "money", "transfer", "wire", "cheque", "check",
}
SHORT_REPLY_MAX_WORDS = 3


def is_invoice_chat_message(
    message: str,
    current_invoice: Mapping,
    other_invoices: Iterable[Mapping] | Callable[[], Iterable[Mapping]] = (),
) -> bool:
    """Return whether *message* plausibly concerns the supplied invoices.

    *other_invoices* may be a loader: it is called only when the message is
    neither a short reply nor contains an invoice word, so most messages
    need no lookup.
    """
    normalized = message.lower()
    words = re.findall(r"[a-z0-9_-]+", normalized)
    if len(words) <= SHORT_REPLY_MAX_WORDS or set(words) & INVOICE_CHAT_KEYWORDS:
        return True

    others = other_invoices() if callable(other_invoices) else other_invoices
    candidates = []
    for invoice in (current_invoice, *others):
        candidates.extend((
            parse_public_invoice_id(str(invoice["id"])),
            invoice.get("client_name", ""),
            invoice.get("client_email", ""),
        ))
    return any(
        len(value) >= 3 and value in normalized
        for candidate in candidates
        if (value := str(candidate or "").strip().lower())
    )
