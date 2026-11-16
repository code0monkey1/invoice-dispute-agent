"""Turning agent state into what the API returns: messages, invoice state,
approval cards, draft previews, decision labels and email-send notes.

Pure functions: no database, agent or request. Shared by the chat, escalate,
approval and inbound-reply flows.
"""
import json as json_lib
import logging
import re
from difflib import SequenceMatcher

from src.adapters.agent_session import LangGraphAgentSession
from src.domain.email_templates import render_draft
from src.domain.invoice import compute_balance, invoice_state as invoice_state_from_db
from src.email_drafts import DRAFT_LABELS
from src.state import FreelancerContext
from src.usecases.invoices import safe_filename

logger = logging.getLogger("invoicechaser")


EMAIL_DRAFT_TOOLS = set(DRAFT_LABELS)


EMAIL_STATUS_NOTES = {
    "sent": "Sent from your Gmail.",
    "demo": "You're in the demo, so nothing was sent. Connect Gmail to send emails for real.",
    "gmail_not_connected": "Gmail isn't connected, so nothing was sent. Connect Gmail from your dashboard to send from your own address.",
    "failed": "Gmail couldn't send this email, so nothing was sent. Try approving it again in a moment.",
    "already_sent": "This email was already sent, so it wasn't sent again.",
}


EMAIL_SENT_STATUSES = {"sent", "already_sent"}


EMAIL_LOG_LABELS = {
    **DRAFT_LABELS,
    "record_partial_payment": "Partial Payment",
    "mark_invoice_pending": "Payment Pending",
    "mark_invoice_paid": "Invoice Paid",
}


_FENCE_TAG = re.compile(r"</?\s*client_reply\s*>", re.IGNORECASE)


def serialize_message_content(content) -> str:
    """Normalize LangChain message content into text React can render safely."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text is not None:
                    parts.append(str(text))
                else:
                    parts.append(json_lib.dumps(item, ensure_ascii=False))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    if isinstance(content, dict):
        text = content.get("text") or content.get("content")
        return str(text) if text is not None else json_lib.dumps(content, ensure_ascii=False)
    return str(content)


def serialize_messages(messages):
    """Extract serializable message data from LangChain messages."""
    result = []
    for msg in messages:
        entry = {
            "type": msg.__class__.__name__,
            "content": serialize_message_content(msg.content) if hasattr(msg, "content") else str(msg),
        }
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            entry["tool_calls"] = [
                {"name": tc["name"], "args": tc["args"]}
                for tc in msg.tool_calls
            ]
        if hasattr(msg, "name"):
            entry["name"] = msg.name
        result.append(entry)
    return result


def generate_draft_preview(
    tool_name: str,
    state: dict,
    context: FreelancerContext,
    action_args: dict | None = None,
) -> str:
    """The email the draft tool produces, for the approval card and the send. '' if it can't be built."""
    try:
        return render_draft(tool_name, state, context)
    except Exception:
        return ""


def parse_draft_subject_and_body(draft: str) -> tuple[str, str]:
    """Split a draft into subject line and body text."""
    lines = draft.strip().split("\n")
    subject = "Invoice Payment Notice"
    body = draft

    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        # Body is everything after the subject line (skip blank line after subject)
        remaining = lines[1:]
        while remaining and not remaining[0].strip():
            remaining = remaining[1:]
        body = "\n".join(remaining)

    return subject, body


def attachment_note(invoice, tool):
    if not invoice.get('invoice_file_path'):
        return 'No invoice file is uploaded. This email has no invoice attachment.'
    if tool != 'draft_invoice_delivery_email':
        return 'The uploaded invoice is not attached to this email type.'
    return f"Invoice attachment: {safe_filename(invoice.get('invoice_file_name') or 'invoice.pdf')}."


def action_card(action, state, ctx, invoice=None, *, last_delivery):
    """One preview contract for chat, compact reads and explicit history.

    *last_delivery(invoice_id, label)* looks up the last send of this email, to warn before a resend.
    """
    state = {**state, **(invoice_state_from_db(invoice) if invoice else {})}
    tool = action['name']
    card = {'tool':tool, 'args':action.get('args', {}),
            'description':generate_draft_preview(tool, state, ctx, action.get('args', {})) or action.get('description', '')}
    if invoice and tool in DRAFT_LABELS:
        notes = []
        try:
            last = last_delivery(invoice['id'], DRAFT_LABELS[tool])
            if last:
                notes.append(f"A {DRAFT_LABELS[tool]} was previously sent on {last.get('timestamp') or 'a recorded earlier date'}. Sending another requires your approval.")
        except Exception:
            logger.warning('Previous email delivery could not be checked')
            notes.append('Previous delivery could not be checked. Review the conversation before sending again.')
        notes.append(attachment_note(invoice, tool))
        card['notes'] = notes
    return card


def pending_action(snapshot):
    pending = LangGraphAgentSession.pending_from_snapshot(snapshot)
    return pending.action if pending is not None else None


def extract_interrupt(response, ctx: FreelancerContext | None = None, invoice=None, *, last_delivery):
    """Extract HITL interrupt info from agent response, including a preview of the draft."""
    interrupts = response.get("__interrupt__", [])
    if not interrupts:
        return None
    interrupt = interrupts[0]
    action = interrupt.value["action_requests"][0]
    return action_card(action, response, ctx or FreelancerContext(), invoice, last_delivery=last_delivery)


def extract_state(response):
    """Extract relevant state fields from response."""
    invoice_amount = float(response.get("invoice_amount", 0) or 0)
    amount_paid = float(response.get("amount_paid", 0) or 0)
    balance_due = float(response.get("balance_due", compute_balance(invoice_amount, amount_paid)) or 0)
    return {
        "escalation_level": response.get("escalation_level", 0),
        "client_name": response.get("client_name", ""),
        "client_email": response.get("client_email", ""),
        "invoice_amount": invoice_amount,
        "amount_paid": amount_paid,
        "balance_due": balance_due,
        "invoice_id": response.get("invoice_id", ""),
        "days_overdue": response.get("days_overdue", 0),
        "jurisdiction": response.get("jurisdiction", ""),
        "status": response.get("status", "active"),
        "follow_up_date": response.get("follow_up_date", "") or "",
        "communication_history": response.get("communication_history", []),
    }


def _normalized(text: str | None) -> str:
    return " ".join((text or "").split())


def describe_decision(decision: str, message: str | None, pending_action: dict | None,
                      pending_state: dict, context: FreelancerContext) -> dict:
    """What the human decided. An approval whose text differs from the draft is an edit.

    The app sends an edited draft as an approval with the new text, so the
    difference is found by comparing it with the draft the user was shown.
    """
    tool_name = (pending_action or {}).get("name")
    payload: dict = {"decision": decision, "had_pending_action": bool(pending_action)}
    if decision == "reject" and message:
        payload["feedback"] = message
    if decision == "approve" and message and tool_name in EMAIL_DRAFT_TOOLS:
        proposed = generate_draft_preview(tool_name, pending_state, context, pending_action.get("args", {}))
        if not isinstance(proposed, str) or not proposed:
            # Can't rebuild the draft to compare with: record a plain approval
            # rather than fail the request that is about to send the email.
            payload["compared_with_draft"] = False
            return payload
        if _normalized(proposed) != _normalized(message):
            payload.update(
                decision="approved_with_edits",
                similarity=round(SequenceMatcher(None, proposed, message).ratio(), 3),
                proposed_chars=len(proposed),
                approved_chars=len(message),
            )
    return payload


def trim_action_response(result: dict, before: int, include_history: bool) -> dict:
    if not include_history:
        result = {**result, "messages": result.get("messages", [])[before:]}
        result['state'] = {**result.get('state', {}), 'communication_history': []}
    return result


def with_email_status(result: dict, tool_name: str | None, status: str | None, email_result, extra_note: str = "") -> dict:
    """Add the send outcome to a resume response (email draft approvals only)."""
    if tool_name in EMAIL_DRAFT_TOOLS:
        status = status or "failed"
        result["email_sent"] = status in EMAIL_SENT_STATUSES
        result["email_status"] = status
        result["email_note"] = f"{EMAIL_STATUS_NOTES[status]} {extra_note}".strip()
        if email_result:
            result["email_id"] = email_result.get("id") if isinstance(email_result, dict) else str(email_result)
    return result


def _unfence(text: str) -> str:
    """Strip fence tags so untrusted text can't close the <client_reply> block."""
    text = text or ""
    while True:  # nested pieces like "</client_</client_reply>reply>" rebuild a tag
        cleaned = _FENCE_TAG.sub("", text)
        if cleaned == text:
            return text
        text = cleaned
