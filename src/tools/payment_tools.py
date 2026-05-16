from langchain.tools import tool, ToolRuntime
from langgraph.types import Command
from langchain_core.messages import ToolMessage


@tool
def mark_invoice_pending(follow_up_date: str, runtime: ToolRuntime) -> Command:
    """Mark an invoice as pending payment. The client has agreed to pay. Provide a follow-up date (YYYY-MM-DD) to check back."""
    invoice_id = runtime.state.get("invoice_id", "N/A")
    return Command(update={
        "messages": [ToolMessage(
            f"Invoice #{invoice_id} marked as PENDING. Client has agreed to pay. "
            f"Follow-up scheduled for {follow_up_date}.",
            tool_call_id=runtime.tool_call_id
        )]
    })


@tool
def record_partial_payment(amount_paid: float, payment_date: str, runtime: ToolRuntime) -> Command:
    """Record a partial payment received from the client. Provide the amount paid and payment date (YYYY-MM-DD)."""
    invoice_id = runtime.state.get("invoice_id", "N/A")
    current_paid = float(runtime.state.get("amount_paid", 0) or 0)
    invoice_amount = float(runtime.state.get("invoice_amount", 0) or 0)
    new_paid = min(invoice_amount, current_paid + max(0, amount_paid))
    balance_due = max(0, invoice_amount - new_paid)
    status = "paid" if balance_due <= 0 else "active"
    return Command(update={
        "amount_paid": new_paid,
        "balance_due": balance_due,
        "status": status,
        "messages": [ToolMessage(
            f"Recorded ${amount_paid:.2f} payment for invoice #{invoice_id} on {payment_date}. "
            f"Remaining balance: ${balance_due:.2f}.",
            tool_call_id=runtime.tool_call_id
        )]
    })


@tool
def mark_invoice_paid(runtime: ToolRuntime) -> Command:
    """Mark an invoice as paid. Use when payment has been confirmed."""
    invoice_id = runtime.state.get("invoice_id", "N/A")
    invoice_amount = float(runtime.state.get("invoice_amount", 0) or 0)
    return Command(update={
        "amount_paid": invoice_amount,
        "balance_due": 0,
        "status": "paid",
        "messages": [ToolMessage(
            f"Invoice #{invoice_id} has been marked as PAID. Dispute resolved.",
            tool_call_id=runtime.tool_call_id
        )]
    })
