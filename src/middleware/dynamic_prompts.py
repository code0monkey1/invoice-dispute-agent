from langchain.agents.middleware import dynamic_prompt, ModelRequest

from src.prompts import load_prompt


def _load_escalation_prompt(level: int) -> str:
    if level <= 0:
        prompt_name = "escalation_level_0"
    elif level == 1:
        prompt_name = "escalation_level_1"
    elif level == 2:
        prompt_name = "escalation_level_2"
    else:
        prompt_name = "escalation_level_3"
    return load_prompt(prompt_name)


def render_escalation_prompt(level: int, ctx) -> str:
    return _render(_load_escalation_prompt(level), ctx)


def _render(template: str, ctx) -> str:
    return template.format(
        freelancer_name=ctx.freelancer_name,
        freelancer_email=ctx.freelancer_email,
        business_name=ctx.business_name,
        default_payment_terms=ctx.default_payment_terms,
        invoice_context_summary=ctx.invoice_context_summary or "No other invoice context is available.",
    )


def prompt_for_state(state, ctx) -> str:
    """The system prompt for the agent's state.

    A saved invoice always works at level 1 or above (invoice_state_from_db
    reads a stored 0 as 1), so level 0 with an invoice id only happens before
    the first sync; it gets the level-1 prompt.
    """
    level = state.get("escalation_level", 0) or 0
    if level <= 0 and state.get("invoice_id"):
        level = 1
    return render_escalation_prompt(level, ctx)


@dynamic_prompt
def escalation_prompt(request: ModelRequest) -> str:
    """Generate system prompt based on escalation level."""
    return prompt_for_state(request.state, request.runtime.context)
