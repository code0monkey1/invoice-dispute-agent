from langchain.tools import tool, ToolRuntime
from langgraph.types import Command
from langchain_core.messages import ToolMessage

from src.domain.invoice import escalation_name, next_escalation_level


@tool
def escalate_dispute(runtime: ToolRuntime) -> Command:
    """Escalate the invoice dispute to the next level. Level 1=friendly, 2=formal, 3=legal."""
    current = runtime.state.get("escalation_level", 1)
    new_level = next_escalation_level(current)
    if new_level is None:
        return Command(update={
            "messages": [ToolMessage(
                "Already at maximum escalation level (3 - Legal). Cannot escalate further.",
                tool_call_id=runtime.tool_call_id
            )]
        })
    return Command(update={
        "escalation_level": new_level,
        "messages": [ToolMessage(
            f"Dispute escalated from level {current} ({escalation_name(current)}) "
            f"to level {new_level} ({escalation_name(new_level)}). "
            f"New tools and communication tone are now available.",
            tool_call_id=runtime.tool_call_id
        )]
    })


@tool
def update_invoice_details(
    client_name: str,
    client_email: str,
    invoice_amount: float,
    invoice_id: str,
    days_overdue: int,
    jurisdiction: str,
    runtime: ToolRuntime
) -> Command:
    """Save invoice details to state when the user provides them. Call this once you have all details."""
    return Command(update={
        "client_name": client_name,
        "client_email": client_email,
        "invoice_amount": invoice_amount,
        "invoice_id": invoice_id,
        "days_overdue": days_overdue,
        "jurisdiction": jurisdiction,
        "escalation_level": 1,
        "communication_history": [],
        "messages": [ToolMessage(
            f"Invoice details saved. Client: {client_name}, Amount: ${invoice_amount:.2f}, "
            f"{days_overdue} days overdue in {jurisdiction}. Starting at escalation level 1 (Friendly).",
            tool_call_id=runtime.tool_call_id
        )]
    })
