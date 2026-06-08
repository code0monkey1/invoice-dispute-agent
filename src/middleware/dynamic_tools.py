from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

from src.tools.drafting import (
    draft_invoice_delivery_email,
    draft_polite_reminder,
    draft_formal_demand_letter,
    draft_final_notice,
)
from src.tools.invoice import check_invoice_status, calculate_late_fees
from src.tools.legal import lookup_small_claims_procedures, generate_court_filing_guide
from src.tools.escalation import escalate_dispute, update_invoice_details
from src.tools.payment_tools import mark_invoice_pending, mark_invoice_paid, record_partial_payment

PAYMENT_TOOLS = [mark_invoice_pending, mark_invoice_paid, record_partial_payment]

# Tools available at each escalation level (progressive unlocking)
LEVEL_0_TOOLS = [
    update_invoice_details,
    check_invoice_status,
    draft_invoice_delivery_email,
]

LEVEL_1_TOOLS = [
    check_invoice_status,
    draft_invoice_delivery_email,
    draft_polite_reminder,
    escalate_dispute,
    update_invoice_details,
] + PAYMENT_TOOLS

LEVEL_2_TOOLS = LEVEL_1_TOOLS + [
    draft_formal_demand_letter,
    calculate_late_fees,
]

LEVEL_3_TOOLS = LEVEL_2_TOOLS + [
    lookup_small_claims_procedures,
    generate_court_filing_guide,
    draft_final_notice,
]


@wrap_model_call
def dynamic_tool_middleware(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Dynamically provide tools based on the current escalation level in state."""
    escalation_level = request.state.get("escalation_level", 0)

    if escalation_level <= 0:
        tools = LEVEL_0_TOOLS
    elif escalation_level == 1:
        tools = LEVEL_1_TOOLS
    elif escalation_level == 2:
        tools = LEVEL_2_TOOLS
    else:
        tools = LEVEL_3_TOOLS

    request = request.override(tools=tools)
    return handler(request)
