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
