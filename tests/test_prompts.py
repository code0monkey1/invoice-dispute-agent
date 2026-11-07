"""The system prompt matches the tools the model is given."""
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
