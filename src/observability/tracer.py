"""Per-step tracing for agent runs.

One *run* is one agent.invoke made by the API (a chat message, an escalation,
a resume after a human decision, or a client reply). Each run records its
*steps* in order: model calls, tool calls, refused tools, interrupts, human
decisions and sent emails. Steps are buffered in memory and written in two
requests when the run ends.

    api route ──trace_run()──▶ RunRecorder ◀──record_step()── middleware / api
                                   │ (run ends)
                                   ▼
                     flush(): POST agent_runs, then POST agent_trace_steps (bulk)

Tracing is fail-open: a run that can't be written is logged and counted
(see stats()), never raised, because the request it describes may already
have emailed a client.

Stored text is redacted (emails, phone numbers, account-like numbers) and
capped, so the trace tables don't become a second copy of client data.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from src import db
from src.prompts import PROMPT_VERSION

logger = logging.getLogger("invoicechaser")

MAX_TEXT_CHARS = 8_000
MAX_STEP_JSON_CHARS = 32_000
MAX_ERROR_CHARS = 2_000

# USD per 1M tokens (input, output), Groq list prices (console.groq.com/docs/models, Nov 2026).
# A model missing here gets cost None, never 0, so an unpriced run isn't mistaken for a free one.
MODEL_PRICES: dict[str, tuple[float, float]] = {
    "openai/gpt-oss-120b": (0.15, 0.60),
    "openai/gpt-oss-20b": (0.075, 0.30),
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant": (0.05, 0.08),
}

# Each pattern is matched on its own, and overlapping or touching matches are
# merged, so no ordering leaves part of a value showing: "+1 (415) 555-0199@x.com"
# (a phone and an email that share digits) is masked as one span. Repetition is
# bounded or deterministic, so matching stays linear on untrusted text (client
# replies, web search results).
_EMAIL = re.compile(r"[\w.+-]{1,64}@[\w-]{1,63}(?:\.[\w-]{1,63}){1,8}")
_NUMBER = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b|(?<![\w-])(?:\d[ -]?){12,}\d")
_PHONE = re.compile(r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?!\w)")
_PATTERNS = (("email", _EMAIL), ("number", _NUMBER), ("phone", _PHONE))  # label priority order
_PRIORITY = {label: rank for rank, (label, _) in enumerate(_PATTERNS)}
# Longer than any single email match (64 + 1 + 9 * 64 = 641 chars).
_REDACT_MARGIN = 768


def _sensitive_spans(text: str) -> list[tuple[int, int, str]]:
    spans = sorted(
        (m.start(), m.end(), label) for label, pattern in _PATTERNS for m in pattern.finditer(text)
    )
    merged: list[tuple[int, int, str]] = []
    for start, end, label in spans:
        if merged and start <= merged[-1][1]:
            prev_start, prev_end, prev_label = merged[-1]
            best = prev_label if _PRIORITY[prev_label] <= _PRIORITY[label] else label
            merged[-1] = (prev_start, max(prev_end, end), best)
        else:
            merged.append((start, end, label))
    return merged


def redact(text: str) -> str:
    """Mask contact details and account-like numbers, and cap the length.

    Only a window of the text is scanned, so hostile input can't make this
    slow. When the window cuts the text, nothing from its last _REDACT_MARGIN
    characters is emitted as text: a value can't start before that point and
    run past the window, so no half-cut address or number is ever shown.

        |<------------- MAX_TEXT_CHARS ------------->|<- margin ->|  rest (dropped)
        |   emitted, with matches masked             | matches that start here are dropped
    """
    window = text[: MAX_TEXT_CHARS + _REDACT_MARGIN]
    safe_end = len(window) if len(window) == len(text) else MAX_TEXT_CHARS
    parts: list[str] = []
    position = 0
    for start, end, label in _sensitive_spans(window):
        if start >= safe_end:
            break
        parts.append(window[position:start])
        parts.append(f"[{label}]")
        position = end
    if position < safe_end:
        parts.append(window[position:safe_end])
    out = "".join(parts)
    if len(text) > MAX_TEXT_CHARS:
        out = f"{out[:MAX_TEXT_CHARS]}…[truncated {len(text) - MAX_TEXT_CHARS} chars]"
    return out


def _clean(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_clean(v) for v in value]
    return redact(repr(value))[:500]


def sanitize(payload: Any) -> Any:
    """A JSON-safe, redacted copy of a step payload, capped as a whole."""
    cleaned = _clean(payload)
    encoded = json.dumps(cleaned)
    if len(encoded) > MAX_STEP_JSON_CHARS:
        return {"truncated": True, "chars": len(encoded), "preview": encoded[:MAX_TEXT_CHARS]}
    return cleaned


def cost_usd(model: str | None, input_tokens: int | None, output_tokens: int | None) -> float | None:
    price = MODEL_PRICES.get(model or "")
    if price is None or (input_tokens is None and output_tokens is None):
        return None
    return round(((input_tokens or 0) * price[0] + (output_tokens or 0) * price[1]) / 1_000_000, 8)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class RunRecorder:
    """The steps of one agent run, kept in memory until the run ends."""

    def __init__(self, *, kind: str, user_id: str | None, invoice_id: str | None,
                 model: str | None = None, level_start: int | None = None):
        self.id = str(uuid.uuid4())
        self.kind = kind
        self.user_id = user_id
        self.invoice_id = invoice_id
        self.model = model
        self.level_start = level_start
        self.level_end: int | None = None
        self.status = "ok"  # ok | interrupted | error
        self.error: str | None = None
        self.steps: list[dict] = []
        self.input_tokens = 0
        self.output_tokens = 0
        self._cost: float | None = None
        self.started_at = _iso_now()
        self.ended_at: str | None = None
        self._t0 = time.monotonic()
        self.latency_ms: int | None = None
        # The tool node can run several tool calls at once, on different threads.
        self._lock = threading.Lock()

    def add(self, step_type: str, name: str | None, payload: Any, *, latency_ms: int | None = None,
            input_tokens: int | None = None, output_tokens: int | None = None,
            model: str | None = None) -> dict:
        step_model = model or self.model
        step_cost = cost_usd(step_model, input_tokens, output_tokens)
        with self._lock:
            if model and not self.model:
                self.model = model
            step = {
                "run_id": self.id,
                "seq": len(self.steps) + 1,
                "type": step_type,
                "name": name,
                "payload": sanitize(payload),
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "created_at": _iso_now(),
            }
            self.steps.append(step)
            self.input_tokens += input_tokens or 0
            self.output_tokens += output_tokens or 0
            if step_cost is not None:
                self._cost = (self._cost or 0.0) + step_cost
        return step

    def cost_usd(self) -> float | None:
        if self._cost is None:
            return cost_usd(self.model, self.input_tokens or None, self.output_tokens or None)
        return round(self._cost, 8)

    def fail(self, exc: BaseException) -> None:
        """Mark the run failed. The first error is kept: it is the cause, later ones are consequences."""
        self.status = "error"
        if self.error is None:
            self.error = redact(f"{type(exc).__name__}: {exc}")[:MAX_ERROR_CHARS]

    def finish(self) -> None:
        self.ended_at = _iso_now()
        self.latency_ms = int((time.monotonic() - self._t0) * 1000)

    def run_row(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "invoice_id": self.invoice_id,
            "kind": self.kind,
            "status": self.status,
            "prompt_version": PROMPT_VERSION,
            "model": self.model,
            "level_start": self.level_start,
            "level_end": self.level_end,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens or None,
            "output_tokens": self.output_tokens or None,
            "cost_usd": self.cost_usd(),
            "step_count": len(self.steps),
            "error": self.error,
        }


_active: dict[str, RunRecorder] = {}
_active_lock = threading.Lock()
_counters = {"traces_written": 0, "traces_dropped": 0}


def get_recorder(run_id: str | None) -> RunRecorder | None:
    if not run_id:
        return None
    with _active_lock:
        return _active.get(run_id)


def record_step(runtime: Any, step_type: str, name: str | None, payload: Any, **metrics: Any) -> None:
    """Add a step to the run named by the runtime's context; no open run means nothing to do."""
    context = getattr(runtime, "context", None)
    recorder = get_recorder(getattr(context, "trace_run_id", None))
    if recorder is not None:
        recorder.add(step_type, name, payload, **metrics)


def stats() -> dict:
    with _active_lock:
        return {**_counters, "runs_open": len(_active)}


def flush(recorder: RunRecorder) -> bool:
    """Write a finished run and its steps. Returns False (and logs) if it couldn't."""
    t0 = time.monotonic()
    try:
        db.insert_agent_run(recorder.run_row())
        db.insert_trace_steps(recorder.steps)
    except (RuntimeError, TypeError, ValueError) as exc:
        # RuntimeError covers the DB layer: DatabaseUnavailable, Conflict, and
        # other PostgREST errors (e.g. the trace tables not created yet).
        _count("traces_dropped")
        logger.warning("trace.flush failed run_id=%s kind=%s invoice=%s steps=%d: %s",
                       recorder.id, recorder.kind, recorder.invoice_id, len(recorder.steps), exc)
        return False
    except Exception:
        # Fail-open on purpose: this runs after the request's real work (possibly
        # an email to a client), so an unexpected bug here must not turn a
        # success into a 500. Logged with a traceback and counted, not hidden.
        _count("traces_dropped")
        logger.exception("trace.flush failed run_id=%s kind=%s (unexpected)", recorder.id, recorder.kind)
        return False
    _count("traces_written")
    logger.info("trace.flush ok run_id=%s kind=%s steps=%d ms=%d",
                recorder.id, recorder.kind, len(recorder.steps), int((time.monotonic() - t0) * 1000))
    return True


def _count(key: str) -> None:
    with _active_lock:
        _counters[key] += 1


def langsmith_config(config: dict, run: RunRecorder, **extra: Any) -> dict:
    """The LangChain config for one agent call, labelled for LangSmith.

    LangChain sends traces to LangSmith by itself when LANGSMITH_TRACING=true.
    These labels make each LangSmith trace findable from ours and back: search
    LangSmith for metadata trace_run_id = an X-Trace-Id, and conversations
    group by thread_id (one per invoice). Harmless when LangSmith is off.
    """
    thread_id = (config.get("configurable") or {}).get("thread_id")
    level = run.level_start
    metadata = {
        **(config.get("metadata") or {}),
        "trace_run_id": run.id,
        "invoice_id": run.invoice_id,
        "kind": run.kind,
        "escalation_level": level,
        "prompt_version": PROMPT_VERSION,
        **({"thread_id": thread_id} if thread_id else {}),
        **extra,
    }
    tags = [*(config.get("tags") or []), run.kind, *([f"level-{level}"] if level is not None else [])]
    return {**config, "run_name": f"invoicechaser.{run.kind}", "tags": tags, "metadata": metadata}


def note_run_outcome(run: RunRecorder, response: dict) -> None:
    """Record where an agent run stopped: its level, and any approval card it is waiting on."""
    run.level_end = response.get("escalation_level")
    for interrupt in response.get("__interrupt__", []) or []:
        for action in (getattr(interrupt, "value", None) or {}).get("action_requests", []):
            run.add("interrupt", action.get("name"), {"args": action.get("args", {})})
            run.status = "interrupted"


@contextmanager
def trace_run(kind: str, *, user_id: str | None, invoice_id: str | None,
              level: int | None = None, model: str | None = None) -> Iterator[RunRecorder]:
    """Record one agent run. Errors inside are recorded on the run and re-raised."""
    recorder = RunRecorder(kind=kind, user_id=user_id, invoice_id=invoice_id, model=model, level_start=level)
    with _active_lock:
        _active[recorder.id] = recorder
    try:
        yield recorder
    except Exception as exc:
        recorder.fail(exc)
        raise
    finally:
        with _active_lock:
            _active.pop(recorder.id, None)
        recorder.finish()
        flush(recorder)
