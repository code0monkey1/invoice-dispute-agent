"""Marking an invoice as settled stops all further work on it.

Settled reuses the existing "paid" status: chat and escalation already stop for it.
These tests cover the button's endpoint and the paths that could still act after it:
a draft that was waiting for approval, and a client reply arriving later.
"""
import base64
import hashlib
import hmac
import json
import time

import pytest

from tests.test_approve_sends_email import create_invoice, fake_agent, sent, signed_in  # noqa: F401


@pytest.mark.asyncio
async def test_settling_marks_the_invoice_paid_and_logs_it(client, fake_db, fake_agent):
    import api.index as api_index
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)

    r = await client.post(f"/api/invoices/{invoice['id']}/settle", headers=headers)

    assert r.status_code == 200, r.text
    assert r.json()["invoice"]["status"] == "paid"
    assert api_index.get_invoice(invoice["id"])["status"] == "paid"
    assert fake_agent.state["status"] == "paid"
    log = api_index.get_communications(invoice["id"])
    assert log[-1]["type"] == "invoice_settled"


@pytest.mark.asyncio
async def test_settling_twice_is_harmless(client, fake_db, fake_agent):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    await client.post(f"/api/invoices/{invoice['id']}/settle", headers=headers)
    r = await client.post(f"/api/invoices/{invoice['id']}/settle", headers=headers)
    assert r.status_code == 200 and r.json()["invoice"]["status"] == "paid"


@pytest.mark.asyncio
async def test_a_waiting_draft_is_dropped_and_can_no_longer_be_sent(client, fake_db, fake_agent, sent):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    fake_agent.ask_for_approval("draft_polite_reminder")

    await client.post(f"/api/invoices/{invoice['id']}/settle", headers=headers)

    listed = {i["id"]: i for i in (await client.get("/api/invoices", headers=headers)).json()}
    assert listed[invoice["id"]]["awaiting_approval"] is False
    fake_agent.interrupts_cleared = False  # even if a draft somehow survived the sync
    hist = await client.get(f"/api/invoices/{invoice['id']}/history", headers=headers)
    assert hist.json()["interrupt"] is None
    r = await client.post(f"/api/invoices/{invoice['id']}/resume", headers=headers, json={"decision": "approve"})
    assert r.status_code == 400
    assert sent == []


@pytest.mark.asyncio
async def test_another_user_cannot_settle_the_invoice(client, fake_db, fake_agent):
    import api.index as api_index
    invoice = await create_invoice(client, signed_in(fake_db, "user-a"))
    r = await client.post(f"/api/invoices/{invoice['id']}/settle", headers=signed_in(fake_db, "user-b"))
    assert r.status_code == 404
    assert api_index.get_invoice(invoice["id"])["status"] == "active"


SECRET_RAW = b"test-webhook-signing-key-32bytes!"
DOMAIN = "abc123.resend.app"


@pytest.mark.asyncio
async def test_a_reply_after_settling_is_kept_but_the_agent_stays_quiet(client, fake_db, fake_agent, monkeypatch):
    import api.index as api_index
    monkeypatch.setenv("RESEND_INBOUND_DOMAIN", DOMAIN)
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", "whsec_" + base64.b64encode(SECRET_RAW).decode())
    monkeypatch.setattr(api_index, "fetch_received_email", lambda email_id: {"text": "Thanks, all done!", "html": None})
    calls = []
    monkeypatch.setattr(api_index, "invoke_agent_with_retry", lambda *a, **k: calls.append(1))

    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    token = api_index.ensure_reply_token(invoice["id"])
    await client.post(f"/api/invoices/{invoice['id']}/settle", headers=headers)

    body = json.dumps({"type": "email.received", "data": {
        "email_id": "0f8b6c2e-1111-4222-8333-944445555666", "from": "ap@acme.example",
        "to": [f"inv-{token}@{DOMAIN}"], "subject": "Re: invoice"}}).encode()
    ts = str(int(time.time()))
    sig = base64.b64encode(hmac.new(SECRET_RAW, f"msg_s.{ts}.".encode() + body, hashlib.sha256).digest()).decode()
    r = await client.post("/api/email/inbound", content=body,
                          headers={"svix-id": "msg_s", "svix-timestamp": ts, "svix-signature": f"v1,{sig}"})

    assert r.json()["status"] == "stored"
    assert calls == []
    assert any(c.get("direction") == "inbound" for c in api_index.get_communications(invoice["id"]))
