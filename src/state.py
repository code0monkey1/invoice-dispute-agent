from langchain.agents import AgentState
from dataclasses import dataclass


class InvoiceDisputeState(AgentState):
    client_name: str
    client_email: str
    invoice_amount: float
    amount_paid: float
    balance_due: float
    invoice_id: str
    days_overdue: int
    escalation_level: int        # 1=friendly, 2=formal, 3=legal
    communication_history: list  # [{"type": str, "content": str, "timestamp": str}]
    jurisdiction: str            # e.g., "California", "England and Wales"
    status: str                  # active, pending, paid
    gmail_thread_id: str         # Gmail thread ID for tracking replies
    gmail_message_ids: list      # List of sent message IDs


@dataclass
class FreelancerContext:
    """Per-request context describing who the email is being sent on behalf of.

    Populated from the authenticated user's profile or per-invoice sender overrides.
    Defaults are intentionally placeholder values for unauthenticated/uninitialized
    contexts — never used in production multi-tenant flows.
    """
    freelancer_name: str = "Your Name"
    freelancer_email: str = "your-email@example.com"
    business_name: str = "Your Business"
    default_payment_terms: str = "Net 30"
    default_late_fee_percent: float = 1.5  # monthly
    user_id: str = ""
    invoice_context_summary: str = ""
