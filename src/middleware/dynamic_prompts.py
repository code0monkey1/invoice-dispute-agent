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


@dynamic_prompt
def escalation_prompt(request: ModelRequest) -> str:
    """Generate system prompt based on escalation level."""
    level = request.state.get("escalation_level", 0)
    ctx = request.runtime.context

    if level <= 0 and request.state.get("invoice_id"):
        level = 1

    prompt_template = _load_escalation_prompt(level)
    return prompt_template.format(
        freelancer_name=ctx.freelancer_name,
        business_name=ctx.business_name,
        default_payment_terms=ctx.default_payment_terms,
        default_late_fee_percent=ctx.default_late_fee_percent,
        invoice_context_summary=ctx.invoice_context_summary or "No other invoice context is available.",
    )
