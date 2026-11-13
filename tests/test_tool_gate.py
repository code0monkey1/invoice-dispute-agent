"""Escalation gating is enforced, not just advertised.

dynamic_tool_middleware only decides which tools the model is *offered*. The
graph registers every tool, so a model that names an above-level tool anyway
(hallucination, or a prompt-injected client reply) used to have it run, and an
above-level *draft* reached the human approval card and could be emailed.
The gate refuses those calls before HITL or the tool node ever sees them.
"""
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from src.agent import build_agent
from src.middleware.dynamic_tools import tools_for_level
from src.state import FreelancerContext
from tests.test_real_graph_payments import ScriptedModel, tool_call

ALL_NAMES = {t.name for t in tools_for_level(3)}

CTX = FreelancerContext(
    freelancer_name="Fay", freelancer_email="fay@example.com", business_name="Fay Studio",
    default_payment_terms="Net 30", user_id="u-gate",
)

# A valid call for each tool, so a refusal can only come from the gate.
VALID_ARGS = {
    "update_invoice_details": {"client_name": "Acme"},
    "check_invoice_status": {},
    "draft_invoice_delivery_email": {"subject": "Invoice", "body": "Please find it attached."},
    "draft_polite_reminder": {},
    "escalate_dispute": {},
    "draft_formal_demand_letter": {},
    "lookup_small_claims_procedures": {"jurisdiction": "California"},
    "generate_court_filing_guide": {"jurisdiction": "California"},
    "draft_final_notice": {},
    "mark_invoice_pending": {"follow_up_date": "2026-12-01"},
    "mark_invoice_paid": {},
    "record_partial_payment": {"amount_paid": 10.0, "payment_date": "2026-11-01"},
}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Tavily must never be reached from these tests; record any attempt."""
    import src.tools.legal as legal
    calls = []
    monkeypatch.setattr(legal.tavily_client, "search", lambda q, **k: calls.append(q) or {"results": []})
    return calls


def run(level: int, name: str):
    model = ScriptedModel()
    model.replies = [tool_call(name, **VALID_ARGS[name])]
    agent = build_agent(model, MemorySaver())
    config = {"configurable": {"thread_id": f"gate-{level}-{name}"}}
    out = agent.invoke(
        {"messages": [HumanMessage("do it")], "escalation_level": level, "invoice_id": "inv-1"},
        context=CTX, config=config,
    )
    return agent, config, out


def above_level(level: int) -> list[str]:
    allowed = {t.name for t in tools_for_level(level)}
    return sorted(ALL_NAMES - allowed)


def test_tools_for_level_matches_progressive_unlocking():
    assert "draft_final_notice" not in {t.name for t in tools_for_level(1)}
    assert "draft_formal_demand_letter" in {t.name for t in tools_for_level(2)}
    assert {t.name for t in tools_for_level(-1)} == {t.name for t in tools_for_level(0)}
    assert {t.name for t in tools_for_level(9)} == ALL_NAMES


@pytest.mark.parametrize("level", [0, 1, 2])
def test_every_above_level_tool_is_refused(level, no_network):
    for name in above_level(level):
        agent, config, out = run(level, name)
        refusals = [m for m in out["messages"] if isinstance(m, ToolMessage) and m.name == name]
        assert refusals, f"{name} at level {level}: no refusal recorded"
        assert refusals[0].status == "error"
        assert f"not available at escalation level {level}" in refusals[0].content
        # No approval card for an above-level draft or payment change.
        assert "__interrupt__" not in out, f"{name} at level {level} reached HITL"
        assert not agent.get_state(config).tasks
    assert no_network == []


def test_refused_call_does_not_run_the_tool(no_network):
    run(1, "generate_court_filing_guide")
    assert no_network == []


def test_allowed_tool_still_runs_at_its_level(no_network):
    _, _, out = run(3, "generate_court_filing_guide")
    results = [m for m in out["messages"] if isinstance(m, ToolMessage) and m.name == "generate_court_filing_guide"]
    assert results and results[0].status != "error"
    assert len(no_network) == 1


def test_allowed_draft_still_needs_approval():
    _, _, out = run(1, "draft_polite_reminder")
    assert "__interrupt__" in out


def test_mixed_call_answers_every_tool_call_and_lets_model_retry():
    model = ScriptedModel()
    mixed = AIMessage(content="", tool_calls=[
        {"name": "check_invoice_status", "args": {}, "id": "ok-1"},
        {"name": "draft_final_notice", "args": {}, "id": "bad-1"},
    ])
    model.replies = [mixed, AIMessage(content="Understood, I'll stay at this level.")]
    agent = build_agent(model, MemorySaver())
    out = agent.invoke(
        {"messages": [HumanMessage("go")], "escalation_level": 1, "invoice_id": "inv-1"},
        context=CTX, config={"configurable": {"thread_id": "gate-mixed"}},
    )
    answered = {m.tool_call_id for m in out["messages"] if isinstance(m, ToolMessage)}
    assert answered == {"ok-1", "bad-1"}  # no orphaned tool call for the provider to reject
    assert out["messages"][-1].content == "Understood, I'll stay at this level."
    assert "__interrupt__" not in out


# ─── Runs started by a client's reply ────────────────────────────────────────
# Found by the golden-set eval: an injected reply ("escalate to level 3...",
# "update our email to ...") got the live model to call escalate_dispute and
# update_invoice_details, which change state without an approval step.

UNTRUSTED = FreelancerContext(**{**CTX.__dict__, "untrusted_input": True})


def run_untrusted(level, name):
    model = ScriptedModel()
    model.replies = [tool_call(name, **VALID_ARGS[name]), AIMessage(content="Noted.")]
    agent = build_agent(model, MemorySaver())
    return agent.invoke(
        {"messages": [HumanMessage("[INCOMING CLIENT REPLY] ...")], "escalation_level": level, "invoice_id": "inv-1"},
        context=UNTRUSTED, config={"configurable": {"thread_id": f"untrusted-{level}-{name}"}},
    )


@pytest.mark.parametrize("name", ["update_invoice_details", "escalate_dispute"])
@pytest.mark.parametrize("level", [1, 2, 3])
def test_a_client_reply_cannot_change_state_without_approval(level, name):
    out = run_untrusted(level, name)
    [refusal] = [m for m in out["messages"] if isinstance(m, ToolMessage) and m.name == name]
    assert refusal.status == "error" and "client's reply" in refusal.content
    assert out.get("escalation_level") == level  # nothing changed


def test_a_client_reply_can_still_propose_approval_gated_changes():
    out = run_untrusted(1, "mark_invoice_pending")
    assert "__interrupt__" in out  # the freelancer decides


def test_trusted_runs_keep_the_unapproved_tools():
    _, _, out = run(1, "escalate_dispute")
    assert out.get("escalation_level") == 2


class RecordingModel(ScriptedModel):
    """Remembers the tool names it was offered on each model call."""
    offered: list = []

    def bind_tools(self, tools, **kwargs):
        self.offered.append({getattr(t, "name", None) or t.get("name") for t in tools})
        return self


def offered_tools(context, level=2):
    model = RecordingModel()
    model.offered, model.replies = [], [AIMessage(content="Noted.")]
    build_agent(model, MemorySaver()).invoke(
        {"messages": [HumanMessage("[INCOMING CLIENT REPLY] ...")], "escalation_level": level, "invoice_id": "inv-1"},
        context=context, config={"configurable": {"thread_id": f"offered-{id(context)}-{level}"}},
    )
    return model.offered[-1]


@pytest.mark.parametrize("level", [1, 2, 3])
def test_a_client_reply_is_not_offered_tools_it_could_never_use(level):
    """The gate refuses them anyway, but offering them invited the attempt:
    the live eval saw the model try update_invoice_details on a reply."""
    offered = offered_tools(UNTRUSTED, level)
    assert "update_invoice_details" not in offered and "escalate_dispute" not in offered
    assert "mark_invoice_paid" in offered, "approval-gated tools stay available"


def test_trusted_runs_are_still_offered_the_unapproved_tools():
    offered = offered_tools(CTX, 2)
    assert {"update_invoice_details", "escalate_dispute"} <= offered
