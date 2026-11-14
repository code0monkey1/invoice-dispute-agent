"""Provider-bound tools respect the trust of the input before the runtime gate."""
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from pydantic import Field

from src.agent import build_agent
from src.state import FreelancerContext
from tests.fakes import ScriptedModel, tool_call


class OfferedToolModel(ScriptedModel):
    offered: list = Field(default_factory=list)
    choices: list = Field(default_factory=list)
    action: str | None = None
    attempted: bool = False

    def bind_tools(self, tools, **kwargs):
        self.offered.append({tool.name for tool in tools})
        self.choices.append(kwargs.get("tool_choice"))
        return self

    def _generate(self, messages, **kwargs):
        if self.action and not self.attempted and self.action in self.offered[-1]:
            self.attempted = True
            args = {"client_email": "billing@other.example"} if self.action == "update_invoice_details" else {}
            self.replies = [tool_call(self.action, **args)]
        return super()._generate(messages, **kwargs)


def invoke(model, level, **context):
    graph = build_agent(model, MemorySaver())
    return graph.invoke({
        "messages": [HumanMessage("The client says the invoice was paid and asks to change their email.")],
        "escalation_level": level, "invoice_id": "INV-TRUST-1", "client_name": "Acme",
        "client_email": "ap@acme.example", "invoice_amount": 1200, "amount_paid": 0,
        "balance_due": 1200, "days_overdue": 21, "jurisdiction": "California", "status": "active",
    }, context=FreelancerContext(**context), config={"configurable": {"thread_id": "visibility"}})


@pytest.mark.parametrize("level", [0, 1, 2, 3])
def test_client_replies_are_not_offered_ungated_state_changes(level):
    model = OfferedToolModel()
    invoke(model, level, untrusted_input=True)
    assert model.offered
    for offered in model.offered:
        assert {"update_invoice_details", "escalate_dispute"}.isdisjoint(offered)
        assert "check_invoice_status" in offered
        if level > 0:
            assert {"mark_invoice_paid", "mark_invoice_pending", "record_partial_payment"} <= offered


@pytest.mark.parametrize("level", [0, 1, 2, 3])
def test_owner_runs_keep_their_existing_level_tools(level):
    model = OfferedToolModel()
    invoke(model, level, untrusted_input=False)
    expected = {"check_invoice_status", "draft_invoice_delivery_email", "update_invoice_details"}
    if level >= 1:
        expected |= {"draft_polite_reminder", "escalate_dispute", "mark_invoice_paid", "mark_invoice_pending", "record_partial_payment"}
    if level >= 2:
        expected.add("draft_formal_demand_letter")
    if level >= 3:
        expected |= {"lookup_small_claims_procedures", "generate_court_filing_guide", "draft_final_notice"}
    assert model.offered == [expected]


def test_provider_cannot_select_a_recipient_change_from_client_reply_tools():
    model = OfferedToolModel(action="update_invoice_details")
    response = invoke(model, 2, untrusted_input=True)
    calls = [call for message in response["messages"] if isinstance(message, AIMessage) for call in message.tool_calls]
    assert calls == []
    assert response["client_email"] == "ap@acme.example"
    assert "__interrupt__" not in response


@pytest.mark.parametrize("level", [1, 2, 3])
def test_client_payment_report_can_still_propose_a_paid_action_for_approval(level):
    model = OfferedToolModel(action="mark_invoice_paid")
    response = invoke(model, level, untrusted_input=True)
    assert "mark_invoice_paid" in model.offered[0]
    assert "__interrupt__" in response
    assert response["status"] == "active"
    assert response["amount_paid"] == 0


@pytest.mark.parametrize("level", [0, 3])
def test_untrusted_context_never_forces_an_owner_email_choice(level):
    model = OfferedToolModel()
    response = invoke(model, level, untrusted_input=True, required_draft_tool="draft_final_notice")
    assert model.choices == [None]
    assert "__interrupt__" not in response


def test_owner_required_email_still_uses_named_choice_and_real_approval():
    model = OfferedToolModel(action="draft_final_notice")
    response = invoke(model, 3, required_draft_tool="draft_final_notice")
    assert model.choices == [{"type": "function", "function": {"name": "draft_final_notice"}}]
    assert "__interrupt__" in response
