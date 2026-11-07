"""The system prompt matches the tools the model is given."""
from src.middleware.dynamic_prompts import prompt_for_state
from src.state import FreelancerContext

CTX = FreelancerContext(freelancer_name="Fay", business_name="Fay Studio", freelancer_email="fay@example.com")


def test_an_unsent_invoice_is_told_only_the_delivery_email_is_available():
    """Found by the golden-set eval: level 0 got the level-1 prompt, so the model tried to draft reminders."""
    prompt = prompt_for_state({"escalation_level": 0, "invoice_id": "INV-1"}, CTX)
    assert "hasn't been sent" in prompt and "draft_invoice_delivery_email" in prompt
    # No tool the model doesn't have is named as one of its tools.
    for missing in ("draft_polite_reminder", "escalate_dispute", "draft_final_notice"):
        assert missing not in prompt


def test_setup_without_an_invoice_asks_for_details():
    prompt = prompt_for_state({"escalation_level": 0}, CTX)
    assert "has not yet provided invoice details" in prompt
    assert "hasn't been sent" not in prompt


def test_level_one_and_up_have_no_unsent_note():
    for level in (1, 2, 3):
        assert "hasn't been sent" not in prompt_for_state({"escalation_level": level, "invoice_id": "INV-1"}, CTX)


def test_no_prompt_shows_a_placeholder_to_copy():
    """Found by the golden-set eval: telling the model not to write "[Client Name]" made it write "[Client Name]"."""
    for state in ({"escalation_level": 0}, {"escalation_level": 0, "invoice_id": "I"},
                  *({"escalation_level": n, "invoice_id": "I"} for n in (1, 2, 3))):
        assert "[" not in prompt_for_state(state, CTX).replace("[INCOMING CLIENT REPLY]", "")
