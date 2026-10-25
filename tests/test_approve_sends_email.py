"""Approving a drafted email must actually send it.

The fake agent reproduces LangGraph's real behaviour (verified against
MemorySaver): update_state() keeps the pending task but empties its
interrupts, while Command(resume=...) still works. The approve endpoint used to
sync state first and then look for the interrupt, so it never found the draft
and never sent anything.
"""
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

DRAFT = "Subject: A reminder about invoice INV-SEND-1\n\nHi Acme,\n\nCould you let me know when I can expect payment?\n\nThanks"


class FakeAgent:
    def __init__(self):
        self.state = {}
        self.pending = None
        self.interrupts_cleared = False
        self.resumed_with = None

    def ask_for_approval(self, tool_name="draft_polite_reminder"):
        self.pending = {"name": tool_name, "args": {}}
        self.interrupts_cleared = False

    def get_state(self, config):
        tasks = []
        if self.pending:
            interrupts = [] if self.interrupts_cleared else [SimpleNamespace(value={"action_requests": [self.pending]})]
            tasks = [SimpleNamespace(interrupts=interrupts)]
        return SimpleNamespace(values=dict(self.state, messages=[]), tasks=tasks)

    def update_state(self, config, values):
        self.state.update(values)
        self.interrupts_cleared = True  # what LangGraph does to a pending interrupt

    def invoke(self, payload, context=None, config=None):
        self.resumed_with = getattr(payload, "resume", payload)
        self.pending = None
        return dict(self.state, messages=[AIMessage(content="Done.")])


@pytest.fixture
def fake_agent(monkeypatch):
    import api.index as api_index
    agent = FakeAgent()
    monkeypatch.setattr(api_index, "agent", agent)
    return agent


@pytest.fixture
def sent(monkeypatch):
    import api.index as api_index
    calls = []

    def fake_send(user_id, to_email, subject, body, thread_id=None, attachments=None, reply_to=None):
        calls.append({"user_id": user_id, "to": to_email, "subject": subject, "body": body})
        return {"id": "msg-1", "threadId": "thread-1"}

    monkeypatch.setattr(api_index, "send_email_via_gmail", fake_send)
    monkeypatch.setattr(api_index, "get_user_gmail_tokens", lambda user_id: ("access", "refresh"))
    return calls


def signed_in(fake_db, user_id="user-1"):
    import api.index as api_index
    fake_db.users[user_id] = {"id": user_id, "email": "owner@example.com", "name": "Owner"}
    return {"Authorization": f"Bearer {api_index.create_jwt(user_id, 'owner@example.com')}"}


async def create_invoice(client, headers=None, invoice_id="INV-SEND-1"):
    r = await client.post("/api/invoices", headers=headers or {}, json={
        "invoice_id": invoice_id,
        "client_name": "Acme Corp",
        "client_email": "ap@acme.example",
        "invoice_amount": 1200,
        "amount_paid": 0,
        "days_overdue": 14,
        "jurisdiction": "California",
    })
    assert r.status_code == 200, r.text
    return r.json()["invoice"]


async def approve(client, invoice, headers=None, draft=DRAFT):
    return await client.post(
        f"/api/invoices/{invoice['id']}/resume",
        headers=headers or {},
        json={"decision": "approve", "message": draft},
    )


@pytest.mark.asyncio
async def test_approving_a_draft_sends_it_from_gmail(client, fake_db, fake_agent, sent):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    fake_agent.ask_for_approval()

    r = await approve(client, invoice, headers)

    assert r.status_code == 200, r.text
    assert sent == [{
        "user_id": "user-1",
        "to": "ap@acme.example",
        "subject": "A reminder about invoice INV-SEND-1",
        "body": "Hi Acme,\n\nCould you let me know when I can expect payment?\n\nThanks",
    }]
    body = r.json()
    assert body["email_sent"] is True
    assert body["email_status"] == "sent"
    assert fake_agent.resumed_with == {"decisions": [{"type": "approve"}]}


@pytest.mark.asyncio
async def test_sent_email_is_logged_and_thread_saved(client, fake_db, fake_agent, sent):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    fake_agent.ask_for_approval()

    await approve(client, invoice, headers)

    import api.index as api_index
    outbound = [c for c in api_index.get_communications(invoice["id"]) if c.get("direction") == "outbound"]
    assert len(outbound) == 1
    assert outbound[0]["subject"] == "A reminder about invoice INV-SEND-1"
    assert api_index.get_invoice(invoice["id"])["gmail_thread_id"] == "thread-1"


@pytest.mark.asyncio
async def test_sends_to_the_client_email_saved_on_the_invoice(client, fake_db, fake_agent, sent):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    import api.index as api_index
    api_index.update_invoice(invoice["id"], client_email="billing@acme.example")
    fake_agent.ask_for_approval()

    await approve(client, invoice, headers)

    assert sent[0]["to"] == "billing@acme.example"


@pytest.mark.asyncio
async def test_demo_mode_explains_that_nothing_was_sent(client, fake_db, fake_agent, sent):
    invoice = await create_invoice(client)  # guest
    fake_agent.ask_for_approval()

    r = await approve(client, invoice)

    assert r.status_code == 200, r.text
    assert sent == []
    body = r.json()
    assert body["email_sent"] is False
    assert body["email_status"] == "demo"
    assert "demo" in body["email_note"].lower()


@pytest.mark.asyncio
async def test_missing_gmail_connection_is_reported(client, fake_db, fake_agent, sent, monkeypatch):
    import api.index as api_index
    monkeypatch.setattr(api_index, "get_user_gmail_tokens", lambda user_id: None)
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    fake_agent.ask_for_approval()

    body = (await approve(client, invoice, headers)).json()

    assert sent == []
    assert body["email_sent"] is False
    assert body["email_status"] == "gmail_not_connected"


@pytest.mark.asyncio
async def test_gmail_failure_is_reported_and_not_logged_as_sent(client, fake_db, fake_agent, monkeypatch):
    import api.index as api_index
    monkeypatch.setattr(api_index, "get_user_gmail_tokens", lambda user_id: ("access", "refresh"))
    monkeypatch.setattr(api_index, "send_email_via_gmail", lambda *a, **k: None)
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    fake_agent.ask_for_approval()

    body = (await approve(client, invoice, headers)).json()

    assert body["email_sent"] is False
    assert body["email_status"] == "failed"
    assert not [c for c in api_index.get_communications(invoice["id"]) if c.get("direction") == "outbound"]


@pytest.mark.asyncio
async def test_rejecting_a_draft_sends_nothing(client, fake_db, fake_agent, sent):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    fake_agent.ask_for_approval()

    r = await client.post(
        f"/api/invoices/{invoice['id']}/resume",
        headers=headers,
        json={"decision": "reject", "message": "Make it shorter"},
    )

    assert r.status_code == 200, r.text
    assert sent == []
    assert "email_sent" not in r.json()


@pytest.mark.asyncio
async def test_opening_the_invoice_before_approving_still_sends(client, fake_db, fake_agent, sent):
    """Opening the chat page syncs state from the DB. When nothing changed,
    that sync must not wipe the waiting draft."""
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    import api.index as api_index
    fake_agent.state = api_index.invoice_state_from_db(api_index.get_invoice(invoice["id"]))
    fake_agent.ask_for_approval()

    history = await client.get(f"/api/invoices/{invoice['id']}/history", headers=headers)
    assert history.status_code == 200, history.text
    assert history.json()["interrupt"]["tool"] == "draft_polite_reminder"

    r = await approve(client, invoice, headers)
    assert r.json()["email_status"] == "sent"
    assert len(sent) == 1
