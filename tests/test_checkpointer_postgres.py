"""Conversations survive a restart when stored in a real Postgres.

Opt-in: set TEST_DATABASE_URL to a throwaway local database, e.g.
    TEST_DATABASE_URL="postgresql://postgres@localhost:55432/postgres?sslmode=disable" pytest tests/test_checkpointer_postgres.py

A "restart" builds a brand-new pool, saver and agent, which is what a fresh
Vercel instance does. Nothing in memory carries over; only the database does.
"""
import asyncio
import os
from urllib.parse import urlparse

import pytest
from langchain_core.messages import AIMessage

from tests.fakes import ScriptedModel, tool_call
from tests.test_approve_sends_email import create_invoice, sent, signed_in  # noqa: F401

TEST_URL = os.getenv("TEST_DATABASE_URL", "").strip()

pytestmark = pytest.mark.skipif(not TEST_URL, reason="set TEST_DATABASE_URL to run against a real Postgres")


class Instance:
    """One server instance: its own pool, saver and agent graph."""

    def __init__(self, model):
        from langgraph.checkpoint.postgres import PostgresSaver
        from src.agent import build_agent
        from src.checkpointer import build_pool
        self.pool = build_pool(TEST_URL)
        self.agent = build_agent(model, PostgresSaver(self.pool))

    def close(self):
        self.pool.close()


@pytest.fixture
def server(monkeypatch):
    """Start an instance on a clean database; `server.restart()` swaps in a fresh one."""
    import api.index as api_index
    from src.checkpointer import build_pool

    # This test empties the checkpoint tables: never let it near a real database.
    host = urlparse(TEST_URL).hostname
    assert host in ("localhost", "127.0.0.1", "::1"), f"TEST_DATABASE_URL must be a local throwaway database, not {host}"

    from src import checkpoint_setup
    monkeypatch.setenv("DATABASE_URL", TEST_URL)
    assert checkpoint_setup.main() == 0
    pool = build_pool(TEST_URL)
    with pool.connection() as conn:
        conn.execute("TRUNCATE checkpoints, checkpoint_blobs, checkpoint_writes")
    pool.close()

    class Server:
        model = ScriptedModel()
        current = None

        def restart(self):
            if self.current:
                self.current.close()
            self.current = Instance(self.model)
            monkeypatch.setattr(api_index, "agent", self.current.agent)

    s = Server()
    s.restart()
    yield s
    s.current.close()


async def chat(client, headers, invoice, message):
    r = await client.post("/api/chat", headers=headers, json={"thread_id": f"invoice-{invoice['id']}", "message": message})
    assert r.status_code == 200, r.text
    return r.json()


async def history(client, headers, invoice):
    r = await client.get(f"/api/invoices/{invoice['id']}/history", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def texts(body):
    return [m["content"] for m in body["messages"]]


@pytest.mark.asyncio
async def test_history_survives_a_restart_and_the_conversation_continues(client, fake_db, server):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    server.model.replies = [AIMessage(content="Hello, I can help chase this invoice.")]
    await chat(client, headers, invoice, "What's the status of this invoice?")
    before = await history(client, headers, invoice)
    assert "What's the status of this invoice?" in texts(before)

    server.restart()

    after = await history(client, headers, invoice)
    assert after["messages"] == before["messages"]

    server.model.replies = [AIMessage(content="Still unpaid.")]
    await chat(client, headers, invoice, "Any update?")
    continued = texts(await history(client, headers, invoice))
    assert continued[: len(texts(before))] == texts(before)
    assert "Any update?" in continued and "Still unpaid." in continued


@pytest.mark.asyncio
async def test_a_pending_draft_survives_a_restart_and_is_sent_once(client, fake_db, server, sent):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    server.model.replies = [tool_call("draft_polite_reminder"), AIMessage(content="Sent.")]
    body = await chat(client, headers, invoice, "Draft a polite reminder for this invoice")
    assert body["interrupt"]["tool"] == "draft_polite_reminder"

    server.restart()

    assert (await history(client, headers, invoice))["interrupt"]["tool"] == "draft_polite_reminder"
    r = await client.post(f"/api/invoices/{invoice['id']}/resume", headers=headers, json={"decision": "approve"})
    assert r.status_code == 200, r.text
    assert len(sent) == 1
    assert (await history(client, headers, invoice))["interrupt"] is None


@pytest.mark.asyncio
async def test_concurrent_invoices_keep_their_own_conversations(client, fake_db, server):
    headers = signed_in(fake_db)
    a = await create_invoice(client, headers, invoice_id="INV-A")
    b = await create_invoice(client, headers, invoice_id="INV-B")

    # Each round, both invoices are chatted with at the same time (one message each).
    for n in range(3):
        await asyncio.gather(*(chat(client, headers, inv, f"message {n} for {inv['invoice_id']}") for inv in (a, b)))
    server.restart()

    for mine, other in ((a, b), (b, a)):
        said = [t for t in texts(await history(client, headers, mine)) if t.startswith("message ")]
        assert len(said) == 3
        assert all(t.endswith(mine["invoice_id"]) for t in said), said
        assert not any(other["invoice_id"] in t for t in said)


def test_a_set_up_database_is_reported_as_the_live_store(server):
    from src.checkpointer import make_checkpointer
    saver, status = make_checkpointer(TEST_URL)
    assert status == {"store": "postgres", "reason": None}
    saver.conn.close()


def test_setup_locks_the_tables_away_from_the_public_api(server):
    from src.checkpointer import TABLES, build_pool
    pool = build_pool(TEST_URL)
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public' AND tablename = ANY(%s)",
            (list(TABLES),)).fetchall()
        assert {r["tablename"] for r in rows} == set(TABLES)
        assert all(r["rowsecurity"] for r in rows)
        for role in ("anon", "authenticated"):
            if conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone():
                for t in TABLES:
                    assert not conn.execute("SELECT has_table_privilege(%s, %s, 'SELECT') AS ok",
                                            (role, f"public.{t}")).fetchone()["ok"]
    pool.close()
