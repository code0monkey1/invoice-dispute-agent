from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage
from langgraph.types import Command
from src.agent import agent
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
            response = agent.invoke(
                Command(resume={"decisions": [{"type": "approve"}]}),
                config=config
            )
        elif user_input.lower() == "reject":
            reason = input("Rejection reason (optional): ").strip()
            response = agent.invoke(
                Command(resume={"decisions": [{"type": "reject", "message": reason or "Please revise."}]}),
                config=config
            )
        elif user_input.lower() == "edit":
            new_text = input("Enter your edited version: ").strip()
            if new_text:
                response = agent.invoke(
                    Command(resume={"decisions": [{"type": "reject", "message": new_text}]}),
                    config=config
                )
            else:
                print("No edit provided, skipping.")
                continue
        else:
            response = agent.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                context=context,
                config=config,
            )

        # Check for HITL interrupt
        if response.get("__interrupt__"):
            print_interrupt(response)
        else:
            last_msg = response["messages"][-1].content
            if last_msg:
                print(f"\nAgent: {last_msg}\n")


if __name__ == "__main__":
    main()
