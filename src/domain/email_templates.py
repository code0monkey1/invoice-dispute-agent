"""The emails the agent drafts, in one place.

The approval card and draft tools share wording. Their historical amount
formatting and balance interpretation remain distinct. Card wording is pinned
in tests/test_policy_golden.py.

*sender* is anything with freelancer_name, freelancer_email, business_name and
default_payment_terms (src.state.FreelancerContext in the app).
"""
import re
from typing import Protocol

from src.domain.invoice import compute_balance

DRAFT_TOOLS = (
    "draft_invoice_delivery_email",
    "draft_polite_reminder",
    "draft_formal_demand_letter",
    "draft_final_notice",
)

_PLACEHOLDER = re.compile(r"\[([^\[\]\n]{1,40})\]")
_PLACEHOLDER_WORDS = re.compile(
    r"\b(your|client|recipient|name|company|business|phone|number|website|address|"
    r"title|position|contact|email|signature)\b", re.IGNORECASE)


class Sender(Protocol):
    freelancer_name: str
    freelancer_email: str
    business_name: str
    default_payment_terms: str


def fill_placeholders(text: str, *, client_name: str, freelancer_name: str,
                      business_name: str, freelancer_email: str) -> str:
    """Replace template placeholders like [Client Name] in an LLM-written email.

    Known ones get the stored value; any other placeholder is removed so it is
    never sent to a client. Lines left empty by a removal are dropped.
    """
    business = "" if business_name.strip().lower() == freelancer_name.strip().lower() else business_name
    known = {
        "client": client_name, "client name": client_name, "recipient name": client_name,
        "name": freelancer_name, "your name": freelancer_name, "sender name": freelancer_name,
        "your full name": freelancer_name,
        "company name": business, "your company name": business, "your company": business,
        "business name": business, "your business name": business, "your business": business,
        "your email": freelancer_email, "your email address": freelancer_email,
        "email": freelancer_email, "contact information": freelancer_email,
        "your contact information": freelancer_email, "your contact info": freelancer_email,
    }

    def replace(match: re.Match) -> str:
        key = " ".join(match.group(1).lower().split())
        if key in known:
            return known[key]
        return "" if _PLACEHOLDER_WORDS.search(key) else match.group(0)

    lines = []
    for line in text.split("\n"):
        filled = _PLACEHOLDER.sub(replace, line)
        if filled.strip() or not _PLACEHOLDER.search(line):
            lines.append(filled.rstrip() if filled != line else line)
    return "\n".join(lines).strip()


def fill_draft_from_context(text: str, state: dict, sender: Sender) -> str:
    return fill_placeholders(
        text,
        client_name=state.get("client_name") or "there",
        freelancer_name=sender.freelancer_name,
        business_name=sender.business_name,
        freelancer_email=sender.freelancer_email,
    )


def invoice_delivery_draft(state: dict, sender: Sender) -> str:
    """Use stored facts for the base draft; the approval card remains editable."""
    total = float(state.get('invoice_amount', 0) or 0)
    paid = float(state.get('amount_paid', 0) or 0)
    balance = max(0, total - paid)
    draft = (
        f"Subject: Invoice #{state.get('invoice_id', 'N/A')} from {sender.business_name}\n\n"
        f"Hi {state.get('client_name') or 'there'},\n\n"
        f"Here are the details for Invoice #{state.get('invoice_id', 'N/A')}. "
        f"The invoice total is ${total:,.2f}, the amount already paid is ${paid:,.2f}, "
        f"and the remaining balance due is ${balance:,.2f}.\n\n"
        "Please review these details and let me know if you have any questions.\n\n"
        f"Best regards,\n{sender.freelancer_name}\n{sender.business_name}\n{sender.freelancer_email}"
    )
    return fill_draft_from_context(draft, state, sender)


def render_draft(tool_name: str, state: dict, sender: Sender, *, tool_result: bool = False) -> str:
    """The email *tool_name* drafts for this invoice state, or '' for a tool that drafts none.

    Raises if the state can't be formatted (an amount that isn't a number).
    """
    legacy_tool = tool_result and tool_name in DRAFT_TOOLS[1:]
    money_format = ".2f" if legacy_tool else ",.2f"
    client_name = state["client_name"] if legacy_tool else state.get("client_name", "Client")
    invoice_id = state["invoice_id"] if legacy_tool else state.get("invoice_id", "N/A")
    invoice_amount = float(state.get("invoice_amount", 0) or 0)
    amount_paid = float(state.get("amount_paid", 0) or 0)
    balance_due = compute_balance(invoice_amount, amount_paid)
    if legacy_tool:
        balance_due = max(0, float(state.get("balance_due", invoice_amount - amount_paid) or 0))
    elif "balance_due" in state:
        balance_due = float(state.get("balance_due", balance_due) or balance_due)
    days_overdue = state["days_overdue"] if legacy_tool and tool_name != "draft_final_notice" else state.get("days_overdue", 0)
    jurisdiction = state["jurisdiction"] if legacy_tool and tool_name == "draft_final_notice" else state.get("jurisdiction", "")

    if tool_name == "draft_invoice_delivery_email":
        return invoice_delivery_draft(state, sender)
    if tool_name == "draft_polite_reminder":
        return (
            f"Subject: Friendly Reminder - Invoice #{invoice_id} Payment\n\n"
            f"Hi {client_name},\n\n"
            f"I hope this message finds you well. I wanted to kindly follow up on "
            f"Invoice #{invoice_id}. The original invoice total was ${invoice_amount:{money_format}}, "
            f"and the remaining balance is ${balance_due:{money_format}}, "
            f"which was due {days_overdue} days ago.\n\n"
            f"I understand things can get busy, and I'd appreciate it if you could "
            f"let me know the status of this payment at your earliest convenience.\n\n"
            f"If you've already sent the payment, please disregard this message.\n\n"
            f"Best regards,\n"
            f"{sender.freelancer_name}\n"
            f"{sender.business_name}\n"
            f"{sender.freelancer_email}"
        )
    if tool_name == "draft_formal_demand_letter":
        return (
            f"Subject: FORMAL DEMAND - Overdue Invoice #{invoice_id}\n\n"
            f"Dear {client_name},\n\n"
            f"This letter constitutes a formal demand for payment of Invoice "
            f"#{invoice_id}. The original invoice amount was ${invoice_amount:{money_format}}; "
            f"the remaining unpaid balance is ${balance_due:{money_format}}, "
            f"which is now {days_overdue} days past due.\n\n"
            f"Per our agreed payment terms ({sender.default_payment_terms}), this invoice "
            f"was due for immediate payment.\n\n"
            f"Total amount now due: ${balance_due:{money_format}}\n\n"
            f"Please remit payment within 7 business days of receipt of this notice "
            f"to avoid further action.\n\n"
            f"This letter serves as formal documentation of this outstanding debt.\n\n"
            f"Sincerely,\n"
            f"{sender.freelancer_name}\n"
            f"{sender.business_name}"
        )
    if tool_name == "draft_final_notice":
        return (
            f"Subject: FINAL NOTICE BEFORE LEGAL ACTION - Invoice #{invoice_id}\n\n"
            f"Dear {client_name},\n\n"
            f"NOTICE: This is a final demand for payment before legal proceedings "
            f"are initiated in {jurisdiction}.\n\n"
            f"Despite previous communications, Invoice #{invoice_id} remains unpaid.\n\n"
            f"Original amount: ${invoice_amount:{money_format}}\n"
            f"Amount paid: ${amount_paid:{money_format}}\n"
            f"TOTAL DUE: ${balance_due:{money_format}}\n\n"
            f"If full payment is not received within 10 business days of this notice, "
            f"I will file a claim in small claims court in {jurisdiction}. "
            f"You may also be liable for court filing fees and additional costs.\n\n"
            f"This letter serves as evidence of attempted resolution prior to legal action.\n\n"
            f"All prior correspondence regarding this matter has been documented.\n\n"
            f"{sender.freelancer_name}\n"
            f"{sender.business_name}\n"
            f"{sender.freelancer_email}"
        )
    return ""
