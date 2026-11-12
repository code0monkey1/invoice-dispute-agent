from langchain.tools import tool, ToolRuntime
from langgraph.types import Command
from langchain_core.messages import ToolMessage

from src.services.escalation_policy import LEVEL_NAMES, next_level


@tool
def escalate_dispute(reason: str, runtime: ToolRuntime) -> Command:
    """Propose moving the dispute up one level (1=Friendly, 2=Formal, 3=Legal).

    The freelancer must approve it before anything changes. Give a short reason
    they can judge it by, e.g. how many reminders went unanswered."""
    # Runs only after the freelancer approved; /resume has already saved the
    # new level, so this just moves the rest of the run to it.
    current = int(runtime.state.get("escalation_level") or 1)
    target = next_level(current)
    if target is None:
        return Command(update={
            "messages": [ToolMessage(
                "Already at maximum escalation level (3 - Legal). Cannot escalate further.",
                tool_call_id=runtime.tool_call_id
            )]
        })
    return Command(update={
        "escalation_level": target,
        "messages": [ToolMessage(
            f"The freelancer approved escalating from level {current} ({LEVEL_NAMES[current]}) "
            f"to level {target} ({LEVEL_NAMES[target]}). The {LEVEL_NAMES[target]} email is now available.",
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
    level = int(runtime.state.get("escalation_level") or 0)
    update = {
        "client_name": client_name,
        "client_email": client_email,
        "invoice_amount": invoice_amount,
        "invoice_id": invoice_id,
        "days_overdue": days_overdue,
        "jurisdiction": jurisdiction,
    }
    if level < 1:
        # Setup starts the ladder. Saving details later never resets it.
        update.update(escalation_level=1, communication_history=[])
        level_note = "Starting at escalation level 1 (Friendly)."
    else:
        level_note = f"Escalation level unchanged ({level})."
    update["messages"] = [ToolMessage(
        f"Invoice details saved. Client: {client_name}, Amount: ${invoice_amount:.2f}, "
        f"{days_overdue} days overdue in {jurisdiction}. {level_note}",
        tool_call_id=runtime.tool_call_id
    )]
    return Command(update=update)
