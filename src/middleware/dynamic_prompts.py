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
    return _load_escalation_prompt(level).format(
        freelancer_name=ctx.freelancer_name,
        freelancer_email=ctx.freelancer_email,
        business_name=ctx.business_name,
        default_payment_terms=ctx.default_payment_terms,
        invoice_context_summary=ctx.invoice_context_summary or "No other invoice context is available.",
    )


@dynamic_prompt
def escalation_prompt(request: ModelRequest) -> str:
    """Generate system prompt based on escalation level."""
    level = request.state.get("escalation_level", 0)
    if level <= 0 and request.state.get("invoice_id"):
        level = 1
    return render_escalation_prompt(level, request.runtime.context)
