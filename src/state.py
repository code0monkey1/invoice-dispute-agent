from langchain.agents import AgentState
from dataclasses import dataclass


class InvoiceDisputeState(AgentState):
    client_name: str
    client_email: str
    invoice_amount: float
    invoice_id: str
    days_overdue: int
    escalation_level: int        # 1=friendly, 2=formal, 3=legal
    communication_history: list  # [{"type": str, "content": str, "timestamp": str}]
    jurisdiction: str            # e.g., "California", "England and Wales"


@dataclass
class FreelancerContext:
    freelancer_name: str = "Alex Rivera"
    freelancer_email: str = "alex@riveraconsulting.com"
    business_name: str = "Rivera Consulting"
    default_payment_terms: str = "Net 30"
    default_late_fee_percent: float = 1.5  # monthly
