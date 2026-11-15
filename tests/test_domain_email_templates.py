"""Email wording has one source: what the client is sent is what the model reads back."""
from types import SimpleNamespace

import pytest

from src.domain.email_templates import DRAFT_TOOLS, render_draft
from tests.test_policy_golden import CONTEXT, FINAL_NOTICE, FORMAL_DEMAND, POLITE_REMINDER, STATE


@pytest.mark.parametrize("tool,expected", [
    ("draft_polite_reminder", POLITE_REMINDER),
    ("draft_formal_demand_letter", FORMAL_DEMAND),
    ("draft_final_notice", FINAL_NOTICE),
])
def test_the_domain_renders_the_text_clients_receive(tool, expected):
    assert render_draft(tool, dict(STATE), CONTEXT) == expected


def test_a_sender_is_anything_with_the_four_fields():
    sender = SimpleNamespace(freelancer_name="Dana Lee", freelancer_email="dana@studio.example",
                             business_name="Lee Studio", default_payment_terms="Net 15")
    assert render_draft("draft_polite_reminder", dict(STATE), sender) == POLITE_REMINDER


def test_an_unknown_tool_has_no_draft():
    assert render_draft("mark_invoice_paid", dict(STATE), CONTEXT) == ""


@pytest.mark.parametrize("tool", DRAFT_TOOLS)
def test_each_draft_tool_returns_the_card_text(tool):
    """The tool result (what the model reads after an approval) matches the approval card."""
    import src.tools.drafting as drafting
    from api.index import generate_draft_preview
    runtime = SimpleNamespace(state=dict(STATE), context=CONTEXT)
    args = {"subject": "Invoice", "body": "Hello"} if tool == "draft_invoice_delivery_email" else {}

    from_tool = getattr(drafting, tool).func(runtime=runtime, **args)

    assert from_tool == generate_draft_preview(tool, dict(STATE), CONTEXT, args)
    assert from_tool  # never an empty draft for a known tool


def test_a_zero_balance_in_state_falls_back_to_the_computed_one():
    """The card's rule, now the tool's too: a blank or zero balance_due means 'work it out'."""
    draft = render_draft("draft_polite_reminder", {**STATE, "balance_due": 0}, CONTEXT)
    assert "the remaining balance is $1,000.00" in draft
