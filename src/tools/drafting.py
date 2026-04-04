from langchain.tools import tool, ToolRuntime


@tool
def draft_polite_reminder(runtime: ToolRuntime) -> str:
    """Draft a polite payment reminder email for an overdue invoice. Use at escalation level 1."""
    state = runtime.state
    ctx = runtime.context
    draft = (
        f"Subject: Friendly Reminder - Invoice #{state['invoice_id']} Payment\n\n"
        f"Hi {state['client_name']},\n\n"
        f"I hope this message finds you well. I wanted to kindly follow up on "
        f"Invoice #{state['invoice_id']} for ${state['invoice_amount']:.2f}, "
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
    """Draft a formal demand letter referencing contract terms and late fees. Use at escalation level 2."""
    state = runtime.state
    ctx = runtime.context
    late_fee = state['invoice_amount'] * (ctx.default_late_fee_percent / 100)
    total_due = state['invoice_amount'] + late_fee
    draft = (
        f"Subject: FORMAL DEMAND - Overdue Invoice #{state['invoice_id']}\n\n"
        f"Dear {state['client_name']},\n\n"
        f"This letter constitutes a formal demand for payment of Invoice "
        f"#{state['invoice_id']} in the amount of ${state['invoice_amount']:.2f}, "
        f"which is now {state['days_overdue']} days past due.\n\n"
        f"Per our agreed payment terms ({ctx.default_payment_terms}), this invoice "
        f"was due for immediate payment. A late fee of ${late_fee:.2f}/month "
        f"({ctx.default_late_fee_percent}% per month) is now being applied.\n\n"
        f"Total amount now due: ${total_due:.2f}\n\n"
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
    months_overdue = max(1, state['days_overdue'] // 30)
    total_late_fees = state['invoice_amount'] * (ctx.default_late_fee_percent / 100) * months_overdue
    total_due = state['invoice_amount'] + total_late_fees
    draft = (
        f"Subject: FINAL NOTICE BEFORE LEGAL ACTION - Invoice #{state['invoice_id']}\n\n"
        f"Dear {state['client_name']},\n\n"
        f"NOTICE: This is a final demand for payment before legal proceedings "
        f"are initiated in {state['jurisdiction']}.\n\n"
        f"Despite previous communications, Invoice #{state['invoice_id']} remains unpaid.\n\n"
        f"Original amount: ${state['invoice_amount']:.2f}\n"
        f"Accumulated late fees ({months_overdue} month(s) at {ctx.default_late_fee_percent}%): "
        f"${total_late_fees:.2f}\n"
        f"TOTAL DUE: ${total_due:.2f}\n\n"
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
