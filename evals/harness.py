"""Run one golden case through the real API and agent graph, offline.

    run_case(case, model)
      1. fresh fake DB + fresh checkpointer, agent built with `model`
      2. sign in, create the invoice, set its escalation level
      3. the turn: POST /api/chat, or the client-reply handler
      4. if an approval card appears, approve it (POST /resume), like a user
      5. return what the user saw, the outbox, and every traced run

Nothing leaves the machine except the model calls: Gmail sends go to an
in-memory outbox, a real Gmail client can't even be built (EvalHarnessError),
and the legal research tools get canned search results.
"""
from __future__ import annotations

import os
from contextlib import ExitStack
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

# The API reads these at import time. Real values (from .env) win; these only
# fill gaps so the harness runs on a laptop or in CI with just GROQ_API_KEY.
for _key, _value in {
    "SUPABASE_URL": "http://supabase.invalid",
    "SUPABASE_KEY": "eval-harness",
    "GROQ_API_KEY": "unset",
    "TAVILY_API_KEY": "unset",
    "SECRET_KEY": "eval-harness-secret-key-not-for-production",
}.items():
    os.environ.setdefault(_key, _value)

# Eval runs stay out of LangSmith unless asked for (EVAL_LANGSMITH_TRACING=true),
# so the project there only holds real traffic.
os.environ["LANGSMITH_TRACING"] = os.getenv("EVAL_LANGSMITH_TRACING") or "false"

from httpx import ASGITransport, AsyncClient  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402
from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

from evals.cases import Case  # noqa: E402
from tests.fakes import FakeDB  # noqa: E402

EVAL_USER = "eval-user"
CANNED_SEARCH = {"results": [{"title": "Small claims court basics", "content": "File a claim with the county court.", "url": "https://example.org"}]}


class EvalHarnessError(RuntimeError):
    """The harness was about to reach a real external service."""


@dataclass
class CaseRun:
    case_id: str
    interrupt: dict | None = None
    draft_text: str | None = None
    reply_text: str | None = None
    approved: bool = False
    # None means no measurement was supplied (e.g. a hand-written/error fixture).
    pre_approval_outbox_count: int | None = None
    outbox: list[dict] = field(default_factory=list)
    runs: list[dict] = field(default_factory=list)
    trace_ids: list[str] = field(default_factory=list)
    error: str | None = None


def _refuse_gmail(*args: Any, **kwargs: Any) -> None:
    raise EvalHarnessError("the eval harness must never build a real Gmail client")


class EvalHarness:
    def __init__(self) -> None:
        self._stack = ExitStack()
        self.db = FakeDB()
        self.outbox: list[dict] = []

    async def __aenter__(self) -> "EvalHarness":
        import api.index as api_index
        import src.db as db_module
        import src.services.gmail_service as gmail_module
        import src.tools.legal as legal

        def fake_request(method, table, query=None, payload=None, prefer=None, **_):
            return self.db.handle(method, [table], query=query, payload=payload, prefer=prefer)

        def fake_send(user_id, to_email, subject, body, thread_id=None, attachments=None, reply_to=None):
            self.outbox.append({"to": to_email, "subject": subject, "body": body})
            return {"id": f"eval-msg-{len(self.outbox)}", "threadId": "eval-thread"}

        stack = self._stack
        stack.enter_context(patch.object(db_module, "_supabase_rest_request", side_effect=fake_request))
        stack.enter_context(patch.object(gmail_module.GmailService, "__init__", _refuse_gmail))
        stack.enter_context(patch.object(api_index.deps, "send_email", fake_send))
        stack.enter_context(patch.object(api_index.deps, "gmail_tokens", lambda user_id: ("access", "refresh")))
        stack.enter_context(patch.object(legal.tavily_client, "search", lambda *a, **k: CANNED_SEARCH))
        self._api = api_index
        self._agent_patch = None
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self._stack.close()

    def _signed_in(self) -> dict:
        self.db.users[EVAL_USER] = {"id": EVAL_USER, "email": "owner@example.com", "name": "Owner"}
        return {"Authorization": f"Bearer {self._api.identity.create_jwt(EVAL_USER, 'owner@example.com')}"}

    async def run_case(self, case: Case, model: Any) -> CaseRun:
        from src.agent import build_agent

        self.db = FakeDB()
        self.outbox.clear()
        self._api.RATE_LIMITS.clear()
        result = CaseRun(case_id=case.id)
        with patch.object(self._api.deps, "agent", build_agent(model, MemorySaver())):
            transport = ASGITransport(app=self._api.app)
            async with AsyncClient(transport=transport, base_url="http://eval") as client:
                try:
                    await self._drive(client, case, result)
                except EvalHarnessError:
                    raise
                except Exception as exc:  # a failed case is reported, not fatal to the whole run
                    result.error = f"{type(exc).__name__}: {exc}"
        if result.pre_approval_outbox_count is None:
            # A failed chat can still have sent something before returning its
            # error. No approval was attempted, so retain that actual count too.
            result.pre_approval_outbox_count = len(self.outbox)
        result.outbox = list(self.outbox)
        result.runs = self._traced_runs()
        return result

    async def _drive(self, client: AsyncClient, case: Case, result: CaseRun) -> None:
        headers = self._signed_in()
        r = await client.post("/api/invoices", headers=headers, json=case.invoice)
        if r.status_code != 200:
            raise RuntimeError(f"creating the invoice failed: {r.status_code} {r.text[:200]}")
        invoice_id = r.json()["invoice"]["id"]
        self.db.invoices[invoice_id]["escalation_level"] = case.level
        self._seed_prior_state(case, invoice_id)

        if "chat" in case.turn:
            r = await client.post("/api/chat", headers=headers,
                                  json={"thread_id": f"invoice-{invoice_id}", "message": case.turn["chat"]})
            if r.status_code != 200:
                raise RuntimeError(f"chat failed: {r.status_code} {r.text[:200]}")
            body = r.json()
            result.trace_ids += r.headers.get("X-Trace-Id", "").split(",") if r.headers.get("X-Trace-Id") else []
        else:
            self._api.handle_client_reply(
                self.db.invoices[invoice_id], case.invoice["client_email"],
                case.turn.get("subject", "Re: Invoice"), case.turn["client_reply"],
            )
            r = await client.get(f"/api/invoices/{invoice_id}/history", headers=headers)
            body = r.json()

        result.pre_approval_outbox_count = len(self.outbox)
        result.interrupt = body.get("interrupt")
        result.reply_text = _last_ai_text(body.get("messages") or [])
        if result.interrupt:
            result.draft_text = result.interrupt.get("description")
            r = await client.post(f"/api/invoices/{invoice_id}/resume", headers=headers, json={"decision": "approve"})
            if r.status_code != 200:
                raise RuntimeError(f"approving failed: {r.status_code} {r.text[:200]}")
            result.approved = True

    def _seed_prior_state(self, case: Case, invoice_id: str) -> None:
        if case.history:
            messages = [(HumanMessage if entry["role"] == "user" else AIMessage)(content=entry["content"])
                        for entry in case.history]
            self._api.deps.agent.update_state({"configurable": {"thread_id": f"invoice-{invoice_id}"}},
                                         {"messages": messages})
        for entry in case.prior_deliveries:
            self.db.communications.append({
                "id": len(self.db.communications) + 1, "invoice_id": invoice_id, "user_id": EVAL_USER,
                "direction": "outbound", "type": self._api.EMAIL_LOG_LABELS[entry["tool"]],
                "subject": entry["subject"], "content": entry["content"], "timestamp": entry["timestamp"],
            })

    def _traced_runs(self) -> list[dict]:
        runs = sorted((dict(r) for r in self.db.agent_runs), key=lambda r: r.get("started_at") or "")
        for run in runs:
            run["steps"] = sorted((s for s in self.db.trace_steps if s["run_id"] == run["id"]), key=lambda s: s["seq"])
        return runs


def _last_ai_text(messages: list[dict]) -> str | None:
    for message in reversed(messages):
        if message.get("type") == "AIMessage" and message.get("content"):
            return str(message["content"])
    return None
