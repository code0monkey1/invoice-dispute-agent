"""LangSmith tracing (optional): every agent call is labelled so LangSmith and our own traces cross-reference.

LangChain sends traces to LangSmith by itself when LANGSMITH_TRACING=true; the
app only adds a run name, tags and metadata. Tests never send anything.
"""
import os

import pytest

from tests.test_approve_sends_email import create_invoice, sent, signed_in  # noqa: F401
from tests.test_real_graph_payments import scripted, tool_call  # noqa: F401


def test_tests_never_send_traces_to_langsmith():
    assert os.environ.get("LANGSMITH_TRACING") == "false"


class Spy:
    """Wraps the real agent and records the config of every invoke."""

    def __init__(self, agent):
        self.agent, self.configs = agent, []

    def invoke(self, payload, context=None, config=None):
        self.configs.append(config)
        return self.agent.invoke(payload, context=context, config=config)

    def __getattr__(self, name):
        return getattr(self.agent, name)


@pytest.fixture
def spy(monkeypatch, scripted):
    import api.index as api_index
    wrapped = Spy(api_index.agent)
    monkeypatch.setattr(api_index, "agent", wrapped)
    return wrapped


@pytest.mark.asyncio
async def test_a_chat_is_labelled_with_our_trace_id_invoice_and_level(client, fake_db, scripted, spy):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [tool_call("draft_polite_reminder")]
    r = await client.post("/api/chat", headers=headers, json={"thread_id": f"invoice-{invoice['id']}", "message": "Draft a polite reminder for this invoice"})

    [config] = spy.configs
    assert config["configurable"]["thread_id"] == f"invoice-{invoice['id']}"  # unchanged
    assert config["run_name"] == "invoicechaser.chat"
    meta = config["metadata"]
    assert meta["trace_run_id"] == r.headers["X-Trace-Id"]
    assert meta["invoice_id"] == invoice["id"] and meta["kind"] == "chat"
    assert meta["thread_id"] == f"invoice-{invoice['id']}"  # LangSmith groups a conversation by this
    assert meta["prompt_version"] == "v1"
    assert {"chat", "level-1"} <= set(config["tags"])


@pytest.mark.asyncio
async def test_a_decision_is_labelled_too(client, fake_db, scripted, spy, sent):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [tool_call("draft_polite_reminder")]
    await client.post("/api/chat", headers=headers, json={"thread_id": f"invoice-{invoice['id']}", "message": "Draft a polite reminder for this invoice"})
    r = await client.post(f"/api/invoices/{invoice['id']}/resume", headers=headers, json={"decision": "approve"})

    config = spy.configs[-1]
    assert config["run_name"] == "invoicechaser.resume"
    assert config["metadata"]["trace_run_id"] == r.headers["X-Trace-Id"]
    assert config["metadata"]["decision"] == "approve"


def test_the_eval_harness_keeps_langsmith_off_unless_asked(monkeypatch):
    import importlib
    import evals.harness as harness
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.delenv("EVAL_LANGSMITH_TRACING", raising=False)
    importlib.reload(harness)
    assert os.environ["LANGSMITH_TRACING"] == "false"
    monkeypatch.setenv("EVAL_LANGSMITH_TRACING", "true")
    importlib.reload(harness)
    assert os.environ["LANGSMITH_TRACING"] == "true"


@pytest.mark.parametrize("env, expected", [
    ({"LANGSMITH_TRACING": "false"}, {"enabled": False}),
    ({"LANGSMITH_TRACING": "true", "LANGSMITH_API_KEY": "k", "LANGSMITH_AGENT_ID": "invoice-chaser",
      "LANGSMITH_AGENT_ENVIRONMENT": "production"},
     {"enabled": True, "destination": "agent invoice-chaser (production)"}),
    ({"LANGSMITH_TRACING": "true", "LANGSMITH_API_KEY": "k", "LANGSMITH_PROJECT": "invoice chaser"},
     {"enabled": True, "destination": "project invoice chaser"}),
])
def test_health_says_where_langsmith_traces_go(monkeypatch, env, expected):
    from src.observability.tracer import langsmith_status
    for name in ("LANGSMITH_TRACING", "LANGSMITH_API_KEY", "LANGSMITH_PROJECT", "LANGSMITH_AGENT_ID", "LANGSMITH_AGENT_ENVIRONMENT"):
        monkeypatch.delenv(name, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    assert langsmith_status() == expected


@pytest.mark.parametrize("env, problem", [
    ({"LANGSMITH_AGENT_ID": "invoice-chaser"}, "LANGSMITH_AGENT_ENVIRONMENT"),
    ({}, "LANGSMITH_API_KEY"),
])
def test_health_names_a_langsmith_misconfiguration(monkeypatch, env, problem):
    """A bad setup only loses traces (LangChain swallows tracer errors), so it must be visible somewhere."""
    from src.observability.tracer import langsmith_status
    for name in ("LANGSMITH_API_KEY", "LANGSMITH_PROJECT", "LANGSMITH_AGENT_ID", "LANGSMITH_AGENT_ENVIRONMENT"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    if "LANGSMITH_AGENT_ID" in env or not env:
        monkeypatch.setenv("LANGSMITH_API_KEY", "k") if env else None
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    status = langsmith_status()
    assert status["enabled"] is True and problem in status["error"]


@pytest.mark.asyncio
async def test_health_reports_langsmith(client):
    body = (await client.get("/api/health")).json()
    assert body["langsmith"] == {"enabled": False}
