import logging
from typing import Callable

from langchain.agents.middleware import after_model, wrap_model_call, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, ToolMessage
from pydantic import ValidationError

from src.observability.tracer import record_step
from src.email_drafts import DRAFT_LABELS, DraftPreparationError
from src.tools.drafting import (
    draft_invoice_delivery_email,
    draft_polite_reminder,
    draft_formal_demand_letter,
    draft_final_notice,
)
from src.tools.invoice import check_invoice_status
from src.tools.legal import lookup_small_claims_procedures, generate_court_filing_guide
from src.tools.escalation import escalate_dispute, update_invoice_details
from src.tools.payment_tools import mark_invoice_pending, mark_invoice_paid, record_partial_payment

logger = logging.getLogger("invoicechaser")

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
]

LEVEL_3_TOOLS = LEVEL_2_TOOLS + [
    lookup_small_claims_procedures,
    generate_court_filing_guide,
    draft_final_notice,
]


def tools_for_level(escalation_level: int | None) -> list:
    """The tools unlocked at an escalation level. One rule for what is offered and what may run."""
    level = escalation_level or 0
    if level <= 0:
        return LEVEL_0_TOOLS
    if level == 1:
        return LEVEL_1_TOOLS
    if level == 2:
        return LEVEL_2_TOOLS
    return LEVEL_3_TOOLS


@wrap_model_call
def dynamic_tool_middleware(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Dynamically provide tools based on the current escalation level in state."""
    tools = tools_for_level(request.state.get("escalation_level", 0))
    ctx = request.runtime.context
    if getattr(ctx, 'suppress_email_drafts', False):
        tools = [tool for tool in tools if tool.name not in DRAFT_LABELS]
    required = getattr(ctx, 'required_draft_tool', None) if not getattr(ctx, 'untrusted_input', False) else None
    overrides = {'tools': tools}
    if required:
        if required not in DRAFT_LABELS or required not in {t.name for t in tools}:
            raise DraftPreparationError('Draft is unavailable at this level')
        overrides['tool_choice'] = {'type':'function', 'function':{'name':required}}
    response = handler(request.override(**overrides))
    if required:
        replies = response.result if isinstance(response, ModelResponse) else [response]
        calls = [call for reply in replies if isinstance(reply, AIMessage) for call in reply.tool_calls]
        if len(calls) != 1 or calls[0].get('name') != required:
            raise DraftPreparationError('Provider did not prepare the required draft')
        selected = next(t for t in tools if t.name == required)
        try:
            selected.tool_call_schema.model_validate(calls[0].get('args'), strict=True)
            if required == 'draft_invoice_delivery_email' and any(
                not calls[0]['args'][key].strip() for key in ('subject', 'body')
            ):
                raise ValueError('Empty delivery draft')
        except (ValidationError, ValueError, TypeError, KeyError):
            raise DraftPreparationError('Provider returned an invalid draft action') from None
    return response


# Offering a tool list is only advice to the model: the graph registers every
# tool, so a call to an above-level tool (a hallucination, or a client reply
# that talks the model into it) would otherwise run, and an above-level draft
# would reach the approval card. This hook is listed after HITL so it runs
# first (after_model hooks run last-to-first) and can send the model back
# before HITL or the tool node sees the call.
#
#   model ──▶ enforce_tool_gate.after_model ──(all allowed)──▶ HITL ──▶ tools
#                      │
#                      └─(any refused)──▶ ToolMessage per call ──▶ model (retry)
@after_model(can_jump_to=["model"])
def enforce_tool_gate(state, runtime) -> dict | None:
    messages = state.get("messages") or []
    if not messages or not isinstance(messages[-1], AIMessage) or not messages[-1].tool_calls:
        return None
    level = state.get("escalation_level", 0) or 0
    untrusted = bool(getattr(runtime.context, "untrusted_input", False))
    suppress_drafts = bool(getattr(runtime.context, 'suppress_email_drafts', False))
    calls = messages[-1].tool_calls
    reasons = {c["id"]: _refusal(c["name"], level, untrusted, suppress_drafts) for c in calls}
    if not any(reasons.values()):
        return None

    replies = []
    for call in calls:
        reason = reasons[call["id"]]
        if reason is None:
            content = "Not run: the same turn asked for a tool that isn't available. Retry without it."
        else:
            content = REFUSAL_MESSAGES[reason].format(tool=call["name"], level=level)
            logger.warning("tool gate refused %s at level %s (%s)", call["name"], level, reason)
            record_step(runtime, "gate_blocked", call["name"],
                        {"level": level, "reason": reason, "args": call.get("args", {})})
        replies.append(ToolMessage(content=content, name=call["name"], tool_call_id=call["id"], status="error"))
    return {"messages": replies, "jump_to": "model"}


# Tools that change the invoice or the agent's state without an approval step.
# A run started by a client's reply is untrusted text, so it can't use them:
# found by the golden-set eval, where injected replies made the live model
# escalate and rewrite the client's email address.
UNAPPROVED_STATE_TOOLS = {"update_invoice_details", "escalate_dispute"}

REFUSAL_MESSAGES = {
    'email_preparation': 'Tool {tool} cannot run: this turn requests information or completes an existing approval. Answer the owner without preparing another email.',
    "level": "Tool {tool} is not available at escalation level {level}.",
    "untrusted_input": (
        "Tool {tool} can't run on a client's reply: it changes the invoice without the freelancer's approval. "
        "Tell the freelancer what the client asked for instead."
    ),
}


def _refusal(name: str, level: int, untrusted: bool, suppress_drafts: bool = False) -> str | None:
    if name not in {t.name for t in tools_for_level(level)}:
        return "level"
    if untrusted and name in UNAPPROVED_STATE_TOOLS:
        return "untrusted_input"
    if suppress_drafts and name in DRAFT_LABELS:
        return 'email_preparation'
    return None
