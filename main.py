from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage
from langgraph.types import Command
from src.agent import agent
from src.observability.tracer import note_run_outcome, trace_run
from src.state import FreelancerContext


def print_interrupt(response):
    """Display HITL interrupt details and prompt for action."""
    interrupt = response["__interrupt__"][0]
    action = interrupt.value["action_requests"][0]
    print(f"\n{'='*60}")
    print(f"  DRAFT PENDING APPROVAL")
    print(f"{'='*60}")
    print(f"  Tool: {action['name']}")
    if action.get("description"):
        print(f"\n{action['description']}")
    print(f"{'='*60}")
    print("  Type 'approve', 'reject', or 'edit' to respond.")
    print()


def run_traced(payload, context, config, decision=None):
    """One traced agent run. Resumes pass the context too: the system prompt is built from it."""
    with trace_run("cli", user_id=context.user_id or None, invoice_id=None) as run:
        context.trace_run_id = run.id
        try:
            if decision is not None:
                run.add("human_decision", None, decision)
            response = agent.invoke(payload, context=context, config=config)
            note_run_outcome(run, response)
            return response
        finally:
            context.trace_run_id = None


def resume(decision_type, context, config, message=None):
    decision = {"type": decision_type}
    traced = {"decision": decision_type}
    if message is not None:
        decision["message"] = message
        traced["feedback"] = message
    return run_traced(Command(resume={"decisions": [decision]}), context, config, decision=traced)


def main():
    context = FreelancerContext()
    config = {"configurable": {"thread_id": "client-001"}}

    print("\n" + "=" * 60)
    print("  INVOICE DISPUTE & PAYMENT CHASER AGENT")
    print("=" * 60)
    print("  Describe your overdue invoice and I'll help you chase it.")
    print("  Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("Goodbye!")
            break

        # Handle HITL resume commands
        if user_input.lower() == "approve":
            response = resume("approve", context, config)
        elif user_input.lower() == "reject":
            reason = input("Rejection reason (optional): ").strip()
            response = resume("reject", context, config, reason or "Please revise.")
        elif user_input.lower() == "edit":
            new_text = input("Enter your edited version: ").strip()
            if not new_text:
                print("No edit provided, skipping.")
                continue
            # Sent as feedback: the agent rewrites the draft from the edited text.
            response = resume("reject", context, config, new_text)
        else:
            response = run_traced({"messages": [HumanMessage(content=user_input)]}, context, config)

        # Check for HITL interrupt
        if response.get("__interrupt__"):
            print_interrupt(response)
        else:
            last_msg = response["messages"][-1].content
            if last_msg:
                print(f"\nAgent: {last_msg}\n")


if __name__ == "__main__":
    main()
