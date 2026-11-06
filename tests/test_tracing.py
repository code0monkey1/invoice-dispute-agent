"""Every agent run the API makes is traced, step by step, through the real graph.

These drive /api/chat, /escalate, /resume and the client-reply handler with a
scripted model, then read the runs and steps the tracer wrote to the (fake)
database.
"""
import json

import pytest
from langchain_core.messages import AIMessage

from src.observability import tracer
from tests.test_approve_sends_email import create_invoice, sent, signed_in  # noqa: F401
from tests.test_real_graph_payments import ScriptedModel, scripted, tool_call  # noqa: F401


async def post_chat(client, headers, invoice, message):
    return await client.post("/api/chat", headers=headers, json={"thread_id": f"invoice-{invoice['id']}", "message": message})


async def resume(client, headers, invoice, decision, **extra):
    return await client.post(f"/api/invoices/{invoice['id']}/resume", headers=headers, json={"decision": decision, **extra})


def runs(fake_db, kind=None):
    return [r for r in fake_db.agent_runs if kind is None or r["kind"] == kind]


def steps(fake_db, run_id):
    return sorted((s for s in fake_db.trace_steps if s["run_id"] == run_id), key=lambda s: s["seq"])


def types(fake_db, run_id):
    return [s["type"] for s in steps(fake_db, run_id)]


async def drafted_reminder(client, fake_db, scripted):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [tool_call("draft_polite_reminder")]
    r = await post_chat(client, headers, invoice, "Please draft a polite reminder for this invoice")
    assert r.status_code == 200, r.text
    return headers, invoice, r


@pytest.mark.asyncio
async def test_a_chat_that_drafts_is_traced_up_to_the_approval_card(client, fake_db, scripted):
    _, invoice, r = await drafted_reminder(client, fake_db, scripted)

    [run] = runs(fake_db, "chat")
    assert r.headers["X-Trace-Id"] == run["id"]
    assert run["status"] == "interrupted"
    assert run["invoice_id"] == invoice["id"] and run["user_id"] == "user-1"
    assert run["prompt_version"] == "v1"
    assert types(fake_db, run["id"]) == ["model_call", "interrupt"]

    model_call, interrupt = steps(fake_db, run["id"])
    assert "draft_polite_reminder" in model_call["payload"]["tools_offered"]
    assert "draft_final_notice" not in model_call["payload"]["tools_offered"]
    assert len(model_call["payload"]["system_prompt_sha256"]) == 64
    assert model_call["payload"]["system_prompt"]  # the rendered prompt, redacted
    assert model_call["payload"]["tool_calls"][0]["name"] == "draft_polite_reminder"
    assert model_call["latency_ms"] is not None
    assert interrupt["name"] == "draft_polite_reminder"


@pytest.mark.asyncio
async def test_approving_records_the_decision_before_the_send_and_the_tool(client, fake_db, scripted, sent):
    headers, invoice, _ = await drafted_reminder(client, fake_db, scripted)
    r = await resume(client, headers, invoice, "approve")
    assert r.status_code == 200, r.text

    [run] = runs(fake_db, "resume")
    assert r.headers["X-Trace-Id"] == run["id"]
    order = types(fake_db, run["id"])
    assert order[:3] == ["human_decision", "email_send", "tool_call"]
    decision, email, tool = steps(fake_db, run["id"])[:3]
    assert decision["payload"]["decision"] == "approve"
    assert decision["name"] == "draft_polite_reminder"
    assert email["payload"]["status"] == "sent"
    assert email["payload"]["gmail_message_id"] == "msg-1"
    assert tool["name"] == "draft_polite_reminder"
    assert run["status"] == "ok"


@pytest.mark.asyncio
async def test_an_edited_approval_is_labelled_as_edited(client, fake_db, scripted, sent):
    headers, invoice, r = await drafted_reminder(client, fake_db, scripted)
    proposed = r.json()["interrupt"]["description"]
    edited = proposed.replace("Hi", "Hello there") + "\n\nP.S. I can also take a bank transfer."
    await resume(client, headers, invoice, "approve", message=edited)

    [run] = runs(fake_db, "resume")
    decision = steps(fake_db, run["id"])[0]
    assert decision["payload"]["decision"] == "approved_with_edits"
    assert 0 < decision["payload"]["similarity"] < 1
    assert decision["payload"]["approved_chars"] > decision["payload"]["proposed_chars"]


@pytest.mark.asyncio
async def test_approving_the_draft_unchanged_is_a_plain_approval(client, fake_db, scripted, sent):
    headers, invoice, r = await drafted_reminder(client, fake_db, scripted)
    proposed = r.json()["interrupt"]["description"]
    await resume(client, headers, invoice, "approve", message="  " + proposed + "\n")

    [run] = runs(fake_db, "resume")
    assert steps(fake_db, run["id"])[0]["payload"]["decision"] == "approve"


@pytest.mark.asyncio
async def test_rejecting_records_the_decision_and_sends_nothing(client, fake_db, scripted, sent):
    headers, invoice, _ = await drafted_reminder(client, fake_db, scripted)
    await resume(client, headers, invoice, "reject", message="Too pushy, soften it")

    [run] = runs(fake_db, "resume")
    order = types(fake_db, run["id"])
    assert order[0] == "human_decision" and "email_send" not in order
    assert steps(fake_db, run["id"])[0]["payload"]["decision"] == "reject"
    assert sent == []


@pytest.mark.asyncio
async def test_a_refused_tool_is_traced_as_gate_blocked(client, fake_db, scripted):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [tool_call("draft_final_notice"), AIMessage(content="That isn't available yet.")]
    await post_chat(client, headers, invoice, "Send the final notice for this invoice now")

    [run] = runs(fake_db, "chat")
    order = types(fake_db, run["id"])
    assert "gate_blocked" in order and "interrupt" not in order
    blocked = next(s for s in steps(fake_db, run["id"]) if s["type"] == "gate_blocked")
    assert blocked["name"] == "draft_final_notice"


@pytest.mark.asyncio
async def test_tool_results_are_traced(client, fake_db, scripted):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [tool_call("check_invoice_status"), AIMessage(content="It's 14 days overdue.")]
    await post_chat(client, headers, invoice, "What is the status of this invoice?")

    [run] = runs(fake_db, "chat")
    assert types(fake_db, run["id"]) == ["model_call", "tool_call", "model_call"]
    tool = steps(fake_db, run["id"])[1]
    assert tool["name"] == "check_invoice_status"
    assert tool["payload"]["status"] == "success"
    assert tool["payload"]["result"]
    assert run["status"] == "ok"


@pytest.mark.asyncio
async def test_tokens_and_cost_are_recorded_when_the_model_reports_usage(client, fake_db, monkeypatch):
    import api.index as api_index
    from langgraph.checkpoint.memory import MemorySaver
    from src.agent import build_agent

    class PricedModel(ScriptedModel):
        model_name: str = "openai/gpt-oss-120b"

    model = PricedModel()
    model.replies = [AIMessage(content="It's overdue.", usage_metadata={"input_tokens": 1000, "output_tokens": 50, "total_tokens": 1050})]
    monkeypatch.setattr(api_index, "agent", build_agent(model, MemorySaver()))
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    await post_chat(client, headers, invoice, "How overdue is this invoice?")

    [run] = runs(fake_db, "chat")
    assert run["model"] == "openai/gpt-oss-120b"
    assert run["input_tokens"] == 1000 and run["output_tokens"] == 50
    assert run["cost_usd"] == pytest.approx((1000 * 0.15 + 50 * 0.60) / 1_000_000)


@pytest.mark.asyncio
async def test_client_contact_details_never_reach_the_trace_tables(client, fake_db, scripted, sent):
    headers, invoice, _ = await drafted_reminder(client, fake_db, scripted)
    await resume(client, headers, invoice, "approve")
    stored = json.dumps(fake_db.trace_steps) + json.dumps(fake_db.agent_runs)
    assert "ap@acme.example" not in stored
    assert "owner@example.com" not in stored


@pytest.mark.asyncio
async def test_escalating_is_traced_with_its_starting_level(client, fake_db, scripted):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [tool_call("draft_formal_demand_letter")]
    r = await client.post(f"/api/invoices/{invoice['id']}/escalate", headers=headers)
    assert r.status_code == 200, r.text

    [run] = runs(fake_db, "escalate")
    assert r.headers["X-Trace-Id"] == run["id"]
    assert run["level_start"] == 2 and run["status"] == "interrupted"


@pytest.mark.asyncio
async def test_a_client_reply_is_traced(client, fake_db, scripted):
    import api.index as api_index
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [AIMessage(content="The client says they'll pay Friday.")]
    api_index.handle_client_reply(fake_db.invoices[invoice["id"]], "ap@acme.example", "Re: invoice", "We'll pay Friday.")

    [run] = runs(fake_db, "inbound_reply")
    assert run["invoice_id"] == invoice["id"]
    assert types(fake_db, run["id"]) == ["model_call"]


@pytest.mark.asyncio
async def test_a_failed_model_call_is_traced_as_an_error_and_still_identified(client, fake_db, monkeypatch):
    import api.index as api_index
    from langgraph.checkpoint.memory import MemorySaver
    from src.agent import build_agent

    class BrokenModel(ScriptedModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            raise ConnectionError("groq is down")

    monkeypatch.setattr(api_index, "agent", build_agent(BrokenModel(), MemorySaver()))
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    r = await post_chat(client, headers, invoice, "What is the status of this invoice?")

    assert r.status_code == 503
    [run] = runs(fake_db, "chat")
    assert r.headers["X-Trace-Id"] == run["id"]
    assert run["status"] == "error" and "groq is down" in run["error"]
    assert types(fake_db, run["id"]) == ["model_call"]
    assert "groq is down" in steps(fake_db, run["id"])[0]["payload"]["error"]


@pytest.mark.asyncio
async def test_an_off_topic_message_runs_no_agent_and_writes_no_trace(client, fake_db, scripted):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    r = await post_chat(client, headers, invoice, "Write me a poem about the sea")
    assert r.status_code == 200
    assert runs(fake_db) == []
    assert "X-Trace-Id" not in r.headers


@pytest.mark.asyncio
async def test_trace_storage_outage_never_blocks_an_approved_email(client, fake_db, scripted, sent):
    headers, invoice, _ = await drafted_reminder(client, fake_db, scripted)
    fake_db.down_tables = {"agent_runs", "agent_trace_steps"}
    dropped = tracer.stats()["traces_dropped"]

    r = await resume(client, headers, invoice, "approve")

    assert r.status_code == 200, r.text
    assert len(sent) == 1
    assert tracer.stats()["traces_dropped"] == dropped + 1
    health = (await client.get("/api/health")).json()
    assert health["traces"]["traces_dropped"] >= dropped + 1
