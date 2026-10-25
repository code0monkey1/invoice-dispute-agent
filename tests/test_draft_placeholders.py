"""The invoice delivery email is written by the LLM, so it must be given the stored
invoice details, and any template placeholders it still writes must never reach the client."""
import pytest

from src.state import FreelancerContext
from src.tools.drafting import fill_placeholders

LLM_DRAFT = """Hi [Client Name],

Please find attached Invoice #inv-07881 for the amount of $2,980.00.

Best regards,
[Your Name]
[Your Company Name]
[Your Contact Information]"""

SENDER = dict(client_name="Uncle Sam", freelancer_name="Chiranjeev Thomas",
              business_name="Thomas Studio", freelancer_email="chiranjeev@example.com")


def test_known_placeholders_are_filled_with_stored_details():
    out = fill_placeholders(LLM_DRAFT, **SENDER)
    assert out.startswith("Hi Uncle Sam,")
    assert "Chiranjeev Thomas\nThomas Studio\nchiranjeev@example.com" in out
    assert "[" not in out


def test_unknown_placeholders_are_removed_not_sent():
    out = fill_placeholders("Thanks,\nChiranjeev\n[Your Phone Number]\n[Website]", **SENDER)
    assert out == "Thanks,\nChiranjeev"


def test_business_line_is_dropped_when_it_just_repeats_the_name():
    out = fill_placeholders("Best,\n[Your Name]\n[Your Company Name]",
                            **{**SENDER, "business_name": "Chiranjeev Thomas"})
    assert out == "Best,\nChiranjeev Thomas"


def test_normal_brackets_in_text_are_left_alone():
    text = "Hi Sam,\n\nThe amount [incl. tax] is $10."
    assert fill_placeholders(text, **SENDER) == text


def test_draft_preview_never_shows_placeholders():
    import api.index as api_index
    state = {"client_name": "Uncle Sam", "invoice_id": "inv-07881", "invoice_amount": 2980}
    ctx = FreelancerContext(freelancer_name="Chiranjeev Thomas", freelancer_email="chiranjeev@example.com",
                            business_name="Chiranjeev Thomas")
    draft = api_index.generate_draft_preview(
        "draft_invoice_delivery_email", state, ctx,
        {"subject": "Invoice #inv-07881", "body": LLM_DRAFT})
    assert "Hi Uncle Sam," in draft and "[" not in draft
    assert "chiranjeev@example.com" in draft


@pytest.mark.asyncio
async def test_agent_prompt_names_the_current_invoice_and_sender(client, fake_db):
    import api.index as api_index
    from src.middleware.dynamic_prompts import render_escalation_prompt
    for n, name in enumerate(["Other Co", "Uncle Sam"]):
        r = await client.post("/api/invoices", json={
            "invoice_id": f"inv-0788{n}", "client_name": name, "client_email": f"c{n}@example.com",
            "invoice_amount": 2980, "amount_paid": 0, "days_overdue": 0, "jurisdiction": "Oregon"})
        invoice = r.json()["invoice"]

    ctx = api_index.get_context_for_invoice(invoice["id"], {"id": "x", "name": "Chiranjeev Thomas",
                                                            "email": "chiranjeev@example.com"})
    prompt = render_escalation_prompt(1, ctx)
    current = ctx.invoice_context_summary.split("\n\n")[0]
    assert "Current invoice" in current and "Uncle Sam" in current and "Other Co" not in current
    assert "chiranjeev@example.com" in prompt
    assert "placeholder" in prompt.lower()
