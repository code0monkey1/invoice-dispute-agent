"""The tracer's own rules: what a run records, what it hides, and that it never breaks a request."""
import json

import pytest

from src.observability import tracer
from src.observability.tracer import RunRecorder, cost_usd, redact, sanitize, trace_run


def test_redact_masks_emails_phones_and_long_numbers():
    text = "Mail ana.lee+ar@client.co or call +1 (415) 555-0199; IBAN DE89370400440532013000."
    out = redact(text)
    assert "ana.lee" not in out and "client.co" not in out
    assert "555-0199" not in out
    assert "370400440532013000" not in out
    assert "[email]" in out and "[phone]" in out and "[number]" in out


def test_redact_keeps_money_dates_and_invoice_numbers_readable():
    text = "Invoice INV-2026-0042 for $1,250.00 was due on 2026-11-15."
    assert redact(text) == text


def test_redact_truncates_long_text_and_says_how_much():
    out = redact("a" * 9000)
    assert len(out) < 8100
    assert out.endswith("…[truncated 1000 chars]")


def test_sanitize_walks_nested_payloads_and_survives_unserializable_values():
    class Weird:
        def __repr__(self):
            return "<Weird bob@x.io>"

    out = sanitize({"to": "bob@x.io", "items": ["call 415-555-0199", 3, None], "obj": Weird()})
    json.dumps(out)  # must be JSON-safe
    assert out["to"] == "[email]"
    assert out["items"][0] == "call [phone]"
    assert out["items"][1:] == [3, None]
    assert "bob@x.io" not in out["obj"]


def test_sanitize_caps_a_whole_step_payload():
    out = sanitize({f"k{i}": "x" * 7000 for i in range(10)})
    assert out["truncated"] is True
    assert len(json.dumps(out)) <= 33_000


def test_cost_is_known_for_priced_models_and_null_for_unknown_ones():
    assert cost_usd("openai/gpt-oss-120b", 1_000_000, 0) > 0
    assert cost_usd("some/unpriced-model", 10, 10) is None
    assert cost_usd("openai/gpt-oss-120b", None, None) is None


def test_recorder_numbers_steps_and_sums_tokens():
    rec = RunRecorder(kind="chat", user_id="u1", invoice_id="inv1", model="openai/gpt-oss-120b")
    rec.add("model_call", "model", {"a": 1}, latency_ms=12, input_tokens=100, output_tokens=20)
    rec.add("tool_call", "check_invoice_status", {"b": 2}, latency_ms=3)
    rec.add("model_call", "model", {}, input_tokens=50, output_tokens=5)
    assert [s["seq"] for s in rec.steps] == [1, 2, 3]
    assert rec.input_tokens == 150 and rec.output_tokens == 25
    assert rec.cost_usd() is not None


def test_trace_run_writes_one_run_and_its_steps(fake_db):
    with trace_run("chat", user_id="u1", invoice_id="inv1", level=1) as rec:
        rec.add("model_call", "model", {"text": "hi"})
        rec.status = "interrupted"
    assert len(fake_db.agent_runs) == 1
    run = fake_db.agent_runs[0]
    assert run["id"] == rec.id and run["kind"] == "chat" and run["status"] == "interrupted"
    assert run["invoice_id"] == "inv1" and run["user_id"] == "u1"
    assert run["level_start"] == 1 and run["latency_ms"] >= 0
    assert [s["run_id"] for s in fake_db.trace_steps] == [rec.id]
    # Bulk insert: one request for the run, one for all its steps.
    writes = [r for r in fake_db.requests if r[0] == "POST" and r[1].startswith("agent_")]
    assert len(writes) == 2


def test_trace_run_records_errors_and_reraises(fake_db):
    with pytest.raises(ValueError):
        with trace_run("chat", user_id="u1", invoice_id="inv1"):
            raise ValueError("model blew up")
    assert fake_db.agent_runs[0]["status"] == "error"
    assert "model blew up" in fake_db.agent_runs[0]["error"]


def test_flush_failure_is_fail_open_and_counted(fake_db, caplog):
    fake_db.down_tables = {"agent_runs"}
    before = tracer.stats()["traces_dropped"]
    with trace_run("resume", user_id="u1", invoice_id="inv1") as rec:
        rec.add("email_send", "draft_polite_reminder", {"status": "sent"})
    assert tracer.stats()["traces_dropped"] == before + 1
    assert rec.id in caplog.text and "trace.flush failed" in caplog.text


def test_recorder_is_found_by_run_id_only_while_the_run_is_open(fake_db):
    with trace_run("chat", user_id="u1", invoice_id="inv1") as rec:
        assert tracer.get_recorder(rec.id) is rec
    assert tracer.get_recorder(rec.id) is None
    assert tracer.get_recorder(None) is None


def test_record_step_without_an_open_run_is_a_noop():
    class Ctx:
        trace_run_id = None

    class Runtime:
        context = Ctx()

    tracer.record_step(Runtime(), "tool_call", "x", {})  # must not raise
