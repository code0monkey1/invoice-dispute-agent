"""Bounded owner-action resolution; never interprets client text as authority."""
from dataclasses import dataclass
import re
import unicodedata

DRAFT_LABELS = {
    'draft_invoice_delivery_email': 'Invoice Delivery',
    'draft_polite_reminder': 'Polite Reminder',
    'draft_formal_demand_letter': 'Formal Demand',
    'draft_final_notice': 'Final Notice',
}


@dataclass(frozen=True)
class EmailRequest:
    tool_name: str | None = None
    only_if_unsent: bool = False
    clarification: str | None = None


def _normalize(text):
    return unicodedata.normalize('NFKC', str(text)).casefold().translate(str.maketrans({'’': "'", '‑':'-', '–':'-', '—':'-'}))


def _owner_text(text):
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    text = re.sub(r'`[^`\n]*`|"[^"\n]*"|“[^”\n]*”|‘[^’\n]*’|(?<!\w)\x27[^\x27\n]+\x27(?!\w)', '', text)
    return '\n'.join(line for line in text.splitlines() if not line.lstrip().startswith('>')).strip()


def _target(text):
    if re.search(r'\bfinal[ -]+notice\b', text):
        return 'draft_final_notice'
    if re.search(r'\bformal[ -]+(?:demand|notice)\b|\bdemand[ -]+letter\b', text):
        return 'draft_formal_demand_letter'
    if re.search(r'\breminder\b', text):
        return 'draft_polite_reminder'
    if re.search(r'\binvoice\b', text):
        return 'draft_invoice_delivery_email'
    return None


def resolve_email_request(message, messages=()):
    """Recognize supported actions, not arbitrary prose containing 'send'."""
    text = _normalize(_owner_text(str(message)))
    request_text = re.sub(
        r"^(?:(?:ok|okay|no)[,\s]+|please\s+|let's\s+|(?:can|could|would|will)\s+you\s+|"
        r"(?:i\s+)?(?:want|need|would like)\s+(?:you\s+)?to\s+|i'd\s+like\s+(?:you\s+)?to\s+|help\s+me\s+)+", '', text)
    if not re.match(r'^(?:draft|write|prepare|send|resend|email|mail|show|use)\b', request_text):
        return None
    email_action = re.match(
        r'^(?:draft|write|prepare|send|resend|email|mail)\s+(?:(?:me|us)\s+)?'
        r'(?:(?:a|an|the|this|my|another|new|first|initial|short|concise|polite|friendly|formal|final|payment)\s+)*'
        r'(?:email|mail|invoice|notice|reminder|demand|letter|it|this)\b', request_text)
    if re.match(r'^(?:draft|write|prepare|send|resend|email|mail)\b', request_text) and not email_action:
        return None
    if request_text.startswith('show') and (
        not re.search(r'\b(?:card|template)\b', request_text)
        or re.search(r'\b(?:how|why|what|explain)\b', request_text)
    ):
        return None
    if request_text.startswith('use') and not re.match(r'^use\s+(?:(?:the|this|chat)\s+)*(?:email|mail)\s+(?:facility|card|template|composer)\b', request_text):
        return None
    if re.search(r'\bsummary\b|\bcourt filing guide\b|\bsmall claims\b', text) and not re.search(r'\b(?:email|mail|reminder|notice|demand)\b', text):
        return None
    drafting = bool(re.search(r'\b(?:draft|write|prepare)\s+(?:(?:a|an|the|another|new|first|polite|friendly|formal|final|payment)\s+)*(?:email|mail|invoice|notice|reminder|demand|letter)\b', text))
    if re.search(r"\b(?:do not|don't|never)\s+(?:draft|write|prepare)\b", text):
        return None
    if not drafting and re.search(r"\b(?:do not|don't|never)\s+(?:send|resend|email|mail)\b", text):
        return None
    action = re.search(r'\b(?:draft|write|prepare|send|resend|email|mail)\b|\bshow\b.*\b(?:card|template)\b|\buse\b.*\bemail\b', text)
    if not action:
        return None
    # A draft command must concern an invoice/email, rather than unrelated text.
    email_words = re.search(r'\b(?:email|mail|invoice|notice|reminder|demand|letter|card|it|this)\b', text)
    if not email_words:
        return None
    conditional = bool(re.search(r"\bif\b[^.;!?]{0,60}\b(?:not|never|hasn't|wasn't)\b[^.;!?]{0,30}\bsent\b|\bunless\b[^.;!?]{0,60}\balready\s+sent\b", text))
    tool = _target(text)
    if tool == 'draft_invoice_delivery_email' and not re.search(r'\binvoice delivery\b|\b(?:send|resend|email|mail|draft|write|prepare)\s+(?:(?:the|this|my|an|a)\s+)?invoice\b', text):
        tool = None  # "for this invoice" does not replace a referenced notice
    if not tool:
        for msg in list(messages)[-8:][::-1]:
            if getattr(msg, 'type', None) != 'ai':
                continue
            calls = [c.get('name') for c in getattr(msg, 'tool_calls', []) if c.get('name') in DRAFT_LABELS]
            if len(set(calls)) == 1:
                tool = calls[0]
                break
            content = getattr(msg, 'content', '')
            if isinstance(content, list):
                content = '\n'.join(b if isinstance(b, str) else str(b.get('text', ''))
                    for b in content if isinstance(b, str) or (isinstance(b, dict) and b.get('type') in ('text','output_text')))
            content = _normalize(content)
            if 'subject:' in content or re.search(r'\bdraft(?:ed)?\b', content):
                tool = _target(content)
                if tool:
                    break
    if not tool:
        return EmailRequest(clarification='Which invoice email would you like me to prepare: an invoice delivery, reminder, formal demand or final notice?')
    return EmailRequest(tool, conditional)


class DraftPreparationError(RuntimeError):
    pass
