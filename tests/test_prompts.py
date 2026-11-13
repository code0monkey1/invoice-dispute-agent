"""The system prompt matches the tools the model is given."""
import pytest

from src.middleware.dynamic_prompts import prompt_for_state
from src.state import FreelancerContext

CTX = FreelancerContext(freelancer_name="Fay", business_name="Fay Studio", freelancer_email="fay@example.com")


def test_a_saved_invoice_gets_the_friendly_prompt_and_setup_asks_for_details():
    assert "ESCALATION LEVEL 1" in prompt_for_state({"escalation_level": 0, "invoice_id": "INV-1"}, CTX)
    assert "has not yet provided invoice details" in prompt_for_state({"escalation_level": 0}, CTX)


def test_no_prompt_shows_a_placeholder_to_copy():
    """Found by the golden-set eval: telling the model not to write "[Client Name]" made it write "[Client Name]"."""
    for state in ({"escalation_level": 0}, {"escalation_level": 0, "invoice_id": "I"},
                  *({"escalation_level": n, "invoice_id": "I"} for n in (1, 2, 3))):
        assert "[" not in prompt_for_state(state, CTX).replace("[INCOMING CLIENT REPLY]", "")


# Each level's prompt names only that level's escalation email, so the model
# doesn't keep reaching for one the gate will refuse.
def _prompt_text(level):
    from pathlib import Path
    return (Path(__file__).resolve().parent.parent / "src/prompts/v1" / f"escalation_level_{level}.txt").read_text()


@pytest.mark.parametrize("level,own,others", [
    (1, "draft_polite_reminder", ["draft_formal_demand_letter", "draft_final_notice"]),
    (2, "draft_formal_demand_letter", ["draft_final_notice"]),
    (3, "draft_final_notice", ["escalate_dispute"]),
])
def test_each_level_prompt_offers_only_its_own_escalation_email(level, own, others):
    tools_line = next(line for line in _prompt_text(level).splitlines() if line.startswith("Your tools:"))
    assert own in tools_line
    for name in others:
        assert name not in tools_line


@pytest.mark.parametrize("level", [1, 2])
def test_escalation_is_described_as_a_proposal(level):
    assert "approves or rejects" in _prompt_text(level)


def test_legal_says_it_is_the_top():
    assert "highest level" in _prompt_text(3)


@pytest.mark.parametrize("level", [1, 2, 3])
def test_tools_line_does_not_advertise_editing_invoice_details(level):
    # Naming it nudged the model to edit the invoice when a client reply asked
    # for a new address (the gate refuses it, but it shouldn't be attempted).
    tools_line = next(line for line in _prompt_text(level).splitlines() if line.startswith("Your tools:"))
    assert "update_invoice_details" not in tools_line
