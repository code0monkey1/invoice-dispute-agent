"""Chat policy: whether text belongs in an invoice conversation, and what to do
with an owner's request for an email before the agent runs."""
import re
from dataclasses import dataclass
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


# --- Preparing an email the owner asked for in chat ------------------------------

PENDING_REPLY = "Please approve or reject the existing review card before preparing another action."


@dataclass(frozen=True)
class EmailPreflight:
    """What to do with an owner's email request before the agent runs.

    outcome None means: let the agent draft *tool* now. Any other outcome is
    answered with *reply* and no agent run.
    """
    outcome: str | None
    reply: str | None
    tool: str | None
    reuse_pending: bool = False


def _missing_details(invoice: Mapping, tool: str) -> list[str]:
    missing = [label for key, label in (("client_name", "client name"), ("client_email", "client email"))
               if not str(invoice.get(key) or "").strip()]
    if not invoice.get("invoice_amount"):
        missing.append("invoice amount")
    if tool == "draft_final_notice" and not invoice.get("jurisdiction"):
        missing.append("jurisdiction")
    return missing


def email_preflight(
    *,
    intent,
    waiting: Mapping | None,
    invoice: Mapping,
    allowed_tools: set[str],
    labels: Mapping[str, str],
    last_delivery: Callable[[str], Mapping | None],
) -> EmailPreflight | None:
    """Decide an owner's email request (*intent*, from src.email_drafts) before any model call.

    None: this isn't an email turn, or the invoice is settled; the usual chat
    path answers. *waiting* is an approval already shown; *allowed_tools* are
    the tools at the invoice's level; *last_delivery(label)* looks up the last
    send of that email and is called only for "if not already sent".
    """
    if not intent and not waiting:
        return None
    if invoice.get("status") == "paid":
        return None  # the settled-invoice reply stays authoritative
    if waiting:
        return EmailPreflight("pending_reused", PENDING_REPLY, waiting.get("name") or getattr(intent, "tool_name", None),
                              reuse_pending=True)
    if intent.clarification:
        return EmailPreflight("clarification", intent.clarification, intent.tool_name)

    tool = intent.tool_name
    if tool not in allowed_tools:
        reply = ("Final notices are available at Legal level." if tool == "draft_final_notice"
                 else "That email is not available at the current escalation level.")
        return EmailPreflight("unavailable_level", reply, tool)
    missing = _missing_details(invoice, tool)
    if missing:
        return EmailPreflight("missing_details", "Please provide the " + ", ".join(missing) + " before I prepare this email.", tool)
    if intent.only_if_unsent:
        last = last_delivery(labels[tool])
        if last:
            return EmailPreflight("already_delivered", (
                f"The {labels[tool]} was already sent on {last.get('timestamp') or 'a recorded earlier date'}. "
                "I have not prepared or sent a duplicate. Ask me to prepare another draft if you want to resend it."), tool)
    return EmailPreflight(None, None, tool)
