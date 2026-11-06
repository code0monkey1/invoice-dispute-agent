"""The interactive CLI (python main.py) traces its runs and resumes with the freelancer context."""
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from src.agent import build_agent
from tests.test_real_graph_payments import ScriptedModel, tool_call


def drive(monkeypatch, replies, typed):
    import main
    model = ScriptedModel()
    model.replies = replies
    monkeypatch.setattr(main, "agent", build_agent(model, MemorySaver()))
    answers = iter(typed)
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    main.main()


def test_approving_in_the_cli_resumes_with_context_and_is_traced(monkeypatch, fake_db, capsys):
    drive(
        monkeypatch,
        [tool_call("draft_invoice_delivery_email", subject="Invoice 7", body="Attached."), AIMessage(content="Sent it.")],
        ["Send invoice 7 to Acme", "approve", "quit"],
    )
    assert "Agent: Sent it." in capsys.readouterr().out

    first, second = fake_db.agent_runs
    assert first["kind"] == second["kind"] == "cli"
    assert first["status"] == "interrupted"
    second_steps = [s for s in fake_db.trace_steps if s["run_id"] == second["id"]]
    assert [s["type"] for s in second_steps] == ["human_decision", "tool_call", "model_call"]
    assert second_steps[0]["payload"]["decision"] == "approve"


def test_rejecting_in_the_cli_sends_the_reason_back(monkeypatch, fake_db, capsys):
    drive(
        monkeypatch,
        [tool_call("draft_invoice_delivery_email", subject="Invoice 7", body="Attached."), AIMessage(content="Revised.")],
        ["Send invoice 7 to Acme", "reject", "Too short", "quit"],
    )
    assert "Agent: Revised." in capsys.readouterr().out
    decision = next(s for s in fake_db.trace_steps if s["type"] == "human_decision")
    assert decision["payload"] == {"decision": "reject", "feedback": "Too short"}
