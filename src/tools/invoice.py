from langchain.tools import tool, ToolRuntime


@tool
def check_invoice_status(runtime: ToolRuntime) -> str:
    """Check the current status of the invoice including amount and days overdue."""
    state = runtime.state
    level_names = {1: "Friendly", 2: "Formal", 3: "Legal"}
    level = state.get('escalation_level', 1)
    history = state.get('communication_history', [])
    invoice_amount = float(state.get('invoice_amount', 0) or 0)
    amount_paid = float(state.get('amount_paid', 0) or 0)
    balance_due = max(0, float(state.get('balance_due', invoice_amount - amount_paid) or 0))
    return (
        f"Invoice #{state['invoice_id']}\n"
        f"Client: {state['client_name']} ({state['client_email']})\n"
        f"Original amount: ${invoice_amount:.2f}\n"
        f"Amount paid: ${amount_paid:.2f}\n"
        f"Remaining balance: ${balance_due:.2f}\n"
        f"Status: {state.get('status', 'active')}\n"
        f"Days overdue: {state['days_overdue']}\n"
        f"Escalation level: {level} ({level_names.get(level, 'Unknown')})\n"
        f"Jurisdiction: {state['jurisdiction']}\n"
        f"Communications sent: {len(history)}"
    )


@tool
def calculate_late_fees(runtime: ToolRuntime) -> str:
    """Calculate accumulated late fees based on days overdue and the freelancer's rate."""
    state = runtime.state
    ctx = runtime.context
    months_overdue = max(1, state['days_overdue'] // 30)
    monthly_rate = ctx.default_late_fee_percent / 100
    invoice_amount = float(state.get('invoice_amount', 0) or 0)
    amount_paid = float(state.get('amount_paid', 0) or 0)
    balance_due = max(0, float(state.get('balance_due', invoice_amount - amount_paid) or 0))
    late_fee = balance_due * monthly_rate * months_overdue
    total = balance_due + late_fee
    return (
        f"Late fee calculation:\n"
        f"  Original invoice amount: ${invoice_amount:.2f}\n"
        f"  Amount paid: ${amount_paid:.2f}\n"
        f"  Remaining balance: ${balance_due:.2f}\n"
        f"  Rate: {ctx.default_late_fee_percent}% per month\n"
        f"  Months overdue: {months_overdue}\n"
        f"  Late fees: ${late_fee:.2f}\n"
        f"  Total currently owed: ${total:.2f}"
    )
