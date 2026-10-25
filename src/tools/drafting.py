import re

from langchain.tools import tool, ToolRuntime

_PLACEHOLDER = re.compile(r"\[([^\[\]\n]{1,40})\]")
_PLACEHOLDER_WORDS = re.compile(
    r"\b(your|client|recipient|name|company|business|phone|number|website|address|"
    r"title|position|contact|email|signature)\b", re.IGNORECASE)


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


def fill_draft_from_context(text: str, state: dict, ctx) -> str:
    return fill_placeholders(
        text,
        client_name=state.get("client_name") or "there",
        freelancer_name=ctx.freelancer_name,
        business_name=ctx.business_name,
        freelancer_email=ctx.freelancer_email,
    )


@tool
def draft_invoice_delivery_email(subject: str, body: str, runtime: ToolRuntime) -> str:
    """Draft the first email that sends an invoice to the client. Include a concise subject and body.

    Write the real client name, invoice details and your signature from the system prompt;
    never leave placeholders like [Client Name]."""
    draft = f"Subject: {subject.strip()}\n\n{body.strip()}"
    return fill_draft_from_context(draft, runtime.state, runtime.context)


@tool
def draft_polite_reminder(runtime: ToolRuntime) -> str:
    """Draft a polite payment reminder email for an overdue invoice. Use at escalation level 1."""
    state = runtime.state
    ctx = runtime.context
    invoice_amount = float(state.get('invoice_amount', 0) or 0)
    amount_paid = float(state.get('amount_paid', 0) or 0)
    balance_due = max(0, float(state.get('balance_due', invoice_amount - amount_paid) or 0))
    draft = (
        f"Subject: Friendly Reminder - Invoice #{state['invoice_id']} Payment\n\n"
        f"Hi {state['client_name']},\n\n"
        f"I hope this message finds you well. I wanted to kindly follow up on "
        f"Invoice #{state['invoice_id']}. The original invoice total was ${invoice_amount:.2f}, "
        f"and the remaining balance is ${balance_due:.2f}, "
        f"which was due {state['days_overdue']} days ago.\n\n"
        f"I understand things can get busy, and I'd appreciate it if you could "
        f"let me know the status of this payment at your earliest convenience.\n\n"
        f"If you've already sent the payment, please disregard this message.\n\n"
        f"Best regards,\n"
        f"{ctx.freelancer_name}\n"
        f"{ctx.business_name}\n"
        f"{ctx.freelancer_email}"
    )
    return draft


@tool
def draft_formal_demand_letter(runtime: ToolRuntime) -> str:
    """Draft a formal demand letter referencing the agreed payment terms. Use at escalation level 2."""
    state = runtime.state
    ctx = runtime.context
    invoice_amount = float(state.get('invoice_amount', 0) or 0)
    amount_paid = float(state.get('amount_paid', 0) or 0)
    balance_due = max(0, float(state.get('balance_due', invoice_amount - amount_paid) or 0))
    draft = (
        f"Subject: FORMAL DEMAND - Overdue Invoice #{state['invoice_id']}\n\n"
        f"Dear {state['client_name']},\n\n"
        f"This letter constitutes a formal demand for payment of Invoice "
        f"#{state['invoice_id']}. The original invoice amount was ${invoice_amount:.2f}; "
        f"the remaining unpaid balance is ${balance_due:.2f}, "
        f"which is now {state['days_overdue']} days past due.\n\n"
        f"Per our agreed payment terms ({ctx.default_payment_terms}), this invoice "
        f"was due for immediate payment.\n\n"
        f"Total amount now due: ${balance_due:.2f}\n\n"
        f"Please remit payment within 7 business days of receipt of this notice "
        f"to avoid further action.\n\n"
        f"This letter serves as formal documentation of this outstanding debt.\n\n"
        f"Sincerely,\n"
        f"{ctx.freelancer_name}\n"
        f"{ctx.business_name}"
    )
    return draft


@tool
def draft_final_notice(runtime: ToolRuntime) -> str:
    """Draft a final notice before legal action. Use at escalation level 3."""
    state = runtime.state
    ctx = runtime.context
    invoice_amount = float(state.get('invoice_amount', 0) or 0)
    amount_paid = float(state.get('amount_paid', 0) or 0)
    balance_due = max(0, float(state.get('balance_due', invoice_amount - amount_paid) or 0))
    draft = (
        f"Subject: FINAL NOTICE BEFORE LEGAL ACTION - Invoice #{state['invoice_id']}\n\n"
        f"Dear {state['client_name']},\n\n"
        f"NOTICE: This is a final demand for payment before legal proceedings "
        f"are initiated in {state['jurisdiction']}.\n\n"
        f"Despite previous communications, Invoice #{state['invoice_id']} remains unpaid.\n\n"
        f"Original amount: ${invoice_amount:.2f}\n"
        f"Amount paid: ${amount_paid:.2f}\n"
        f"TOTAL DUE: ${balance_due:.2f}\n\n"
        f"If full payment is not received within 10 business days of this notice, "
        f"I will file a claim in small claims court in {state['jurisdiction']}. "
        f"You may also be liable for court filing fees and additional costs.\n\n"
        f"This letter serves as evidence of attempted resolution prior to legal action.\n\n"
        f"All prior correspondence regarding this matter has been documented.\n\n"
        f"{ctx.freelancer_name}\n"
        f"{ctx.business_name}\n"
        f"{ctx.freelancer_email}"
    )
    return draft
