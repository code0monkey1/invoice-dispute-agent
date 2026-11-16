"""Shared email wording preserves the distinct card and tool formatting contracts."""
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
def test_each_draft_tool_preserves_its_original_text(tool):
    """Tools historically omit thousands separators; delivery already matches the card."""
    import src.tools.drafting as drafting
    from api.index import generate_draft_preview
    runtime = SimpleNamespace(state=dict(STATE), context=CONTEXT)
    args = {"subject": "Invoice", "body": "Hello"} if tool == "draft_invoice_delivery_email" else {}

    from_tool = getattr(drafting, tool).func(runtime=runtime, **args)

    expected = generate_draft_preview(tool, dict(STATE), CONTEXT, args)
    if tool != "draft_invoice_delivery_email":
        expected = expected.replace("$1,200.00", "$1200.00").replace("$1,000.00", "$1000.00")
    assert from_tool == expected
    assert from_tool  # never an empty draft for a known tool


def test_a_zero_balance_in_state_falls_back_to_the_computed_one():
    """The card's original rule: a blank or zero balance_due means 'work it out'."""
    draft = render_draft("draft_polite_reminder", {**STATE, "balance_due": 0}, CONTEXT)
    assert "the remaining balance is $1,000.00" in draft


@pytest.mark.parametrize("tool", DRAFT_TOOLS[1:])
@pytest.mark.parametrize("balance", [0, None, -20])
def test_tool_results_preserve_explicit_zero_and_clamp_negative_balances(tool, balance):
    import src.tools.drafting as drafting
    runtime = SimpleNamespace(state={**STATE, "balance_due": balance}, context=CONTEXT)
    draft = getattr(drafting, tool).func(runtime=runtime)
    assert "$0.00" in draft
    assert "$1,000.00" not in draft
    assert "$-20.00" not in draft


@pytest.mark.parametrize("tool", DRAFT_TOOLS[1:])
def test_tools_still_require_the_invoice_identifier(tool):
    import src.tools.drafting as drafting
    state = dict(STATE)
    del state["invoice_id"]
    with pytest.raises(KeyError, match="invoice_id"):
        getattr(drafting, tool).func(runtime=SimpleNamespace(state=state, context=CONTEXT))
