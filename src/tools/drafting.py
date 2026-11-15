"""The draft tools. Their wording lives in src/domain/email_templates.py, so the
text the model reads back is the text the approval card shows and the client gets."""
from langchain.tools import tool, ToolRuntime

from src.domain.email_templates import (  # noqa: F401  (fill_* re-exported for existing callers)
    fill_draft_from_context,
    fill_placeholders,
    invoice_delivery_draft,
    render_draft,
)


@tool
def draft_invoice_delivery_email(subject: str, body: str, runtime: ToolRuntime) -> str:
    """Prepare an invoice-delivery draft for the owner's review card. This does not send email.

    Call this tool before requesting approval; delivery requires the owner's later card approval.
    Include a concise subject and body.

    Write the real client name, invoice details and your signature from the system prompt;
    use actual values and omit missing details rather than leaving template placeholders."""
    return invoice_delivery_draft(runtime.state, runtime.context)


@tool
def draft_polite_reminder(runtime: ToolRuntime) -> str:
    """Draft a polite payment reminder email for an overdue invoice. Use at escalation level 1."""
    return render_draft("draft_polite_reminder", runtime.state, runtime.context)


@tool
def draft_formal_demand_letter(runtime: ToolRuntime) -> str:
    """Draft a formal demand letter referencing the agreed payment terms. Use at escalation level 2."""
    return render_draft("draft_formal_demand_letter", runtime.state, runtime.context)


@tool
def draft_final_notice(runtime: ToolRuntime) -> str:
    """Draft a final notice before legal action. Use at escalation level 3."""
    return render_draft("draft_final_notice", runtime.state, runtime.context)
