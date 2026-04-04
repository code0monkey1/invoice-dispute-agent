from langchain.tools import tool, ToolRuntime
from langgraph.types import Command
from langchain.messages import ToolMessage


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
def mark_invoice_paid(runtime: ToolRuntime) -> Command:
    """Mark an invoice as paid. Use when payment has been confirmed."""
    invoice_id = runtime.state.get("invoice_id", "N/A")
    return Command(update={
        "messages": [ToolMessage(
            f"Invoice #{invoice_id} has been marked as PAID. Dispute resolved.",
            tool_call_id=runtime.tool_call_id
        )]
    })
