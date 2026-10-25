"""One invoice through the whole product, as a signed-in user.

upload -> draft waiting -> approve (sends from Gmail with Reply-To) ->
client replies (Resend webhook) -> escalate -> new draft waiting.
"""
import base64
import hashlib
import hmac
import json
import time

import pytest
from langchain_core.messages import AIMessage

from tests.test_approve_sends_email import FakeAgent, DRAFT, signed_in

INBOUND_DOMAIN = "abc123.resend.app"
SECRET_RAW = b"test-webhook-signing-key-32bytes!"


def signed(body: bytes):
    ts = str(int(time.time()))
    sig = base64.b64encode(hmac.new(SECRET_RAW, f"msg_e2e.{ts}.".encode() + body, hashlib.sha256).digest()).decode()
    return {"svix-id": "msg_e2e", "svix-timestamp": ts, "svix-signature": f"v1,{sig}"}


@pytest.mark.asyncio
async def test_full_invoice_lifecycle(client, fake_db, monkeypatch):
    import api.index as api_index

    monkeypatch.setenv("RESEND_INBOUND_DOMAIN", INBOUND_DOMAIN)
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", "whsec_" + base64.b64encode(SECRET_RAW).decode())

    agent = FakeAgent()
    monkeypatch.setattr(api_index, "agent", agent)
    sent = []
    monkeypatch.setattr(api_index, "get_user_gmail_tokens", lambda uid: ("access", "refresh"))
    monkeypatch.setattr(api_index, "send_email_via_gmail",
                        lambda uid, to, subject, body, thread_id=None, attachments=None, reply_to=None:
                        sent.append({"to": to, "subject": subject, "reply_to": reply_to}) or {"id": "m1", "threadId": "t1"})
    monkeypatch.setattr(api_index, "fetch_received_email",
                        lambda email_id: {"text": "Sorry, paying on Friday.", "html": None})
    agent_prompts = []

    def fake_invoke(payload, *, context, config):
        agent_prompts.append(payload["messages"][0].content)
        return {**agent.state, "messages": [AIMessage(content="ok")]}

    monkeypatch.setattr(api_index, "invoke_agent_with_retry", fake_invoke)
    headers = signed_in(fake_db)

    # 1. Create the invoice (as if from an uploaded PDF).
    r = await client.post("/api/invoices", headers=headers, json={
        "invoice_id": "INV-E2E-1", "client_name": "Client Co.", "client_email": "sam@clientco.com",
        "invoice_amount": 5000, "amount_paid": 0, "days_overdue": 14, "jurisdiction": "Oregon",
    })
    assert r.status_code == 200, r.text
    invoice = r.json()["invoice"]
    agent.state = api_index.invoice_state_from_db(api_index.get_invoice(invoice["id"]))

    # 2. The agent drafts a reminder; the dashboard shows it waiting for the user.
    agent.ask_for_approval("draft_polite_reminder")
    listed = {i["id"]: i for i in (await client.get("/api/invoices", headers=headers)).json()}
    assert listed[invoice["id"]]["awaiting_approval"] is True

    # 3. Opening the invoice keeps the draft; approving sends it with the tracking Reply-To.
    hist = await client.get(f"/api/invoices/{invoice['id']}/history", headers=headers)
    assert hist.json()["interrupt"]["tool"] == "draft_polite_reminder"
    r = await client.post(f"/api/invoices/{invoice['id']}/resume", headers=headers,
                          json={"decision": "approve", "message": DRAFT})
    assert r.json()["email_status"] == "sent"
    token = api_index.get_invoice(invoice["id"])["reply_token"]
    assert sent[-1]["to"] == "sam@clientco.com"
    assert sent[-1]["reply_to"] == [f"inv-{token}@{INBOUND_DOMAIN}", "owner@example.com"]

    # 4. The client replies; it lands on the invoice and the agent analyses it.
    body = json.dumps({"type": "email.received", "data": {
        "email_id": "0f8b6c2e-1111-4222-8333-944445555666", "from": "Sam <sam@clientco.com>",
        "to": [f"inv-{token}@{INBOUND_DOMAIN}"], "subject": "Re: A reminder"}}).encode()
    r = await client.post("/api/email/inbound", content=body, headers=signed(body))
    assert r.json()["status"] == "stored"
    replies = [c for c in api_index.get_communications(invoice["id"]) if c.get("direction") == "inbound"]
    assert "paying on Friday" in replies[0]["content"]
    assert "<client_reply>" in agent_prompts[-1]

    # 5. The user escalates; the level changes and the agent is asked for a formal draft.
    r = await client.post(f"/api/invoices/{invoice['id']}/escalate", headers=headers)
    assert r.status_code == 200, r.text
    assert api_index.get_invoice(invoice["id"])["escalation_level"] == 2
    assert "Formal" in agent_prompts[-1]

    # 6. A second escalation reaches Legal; a third is refused.
    assert (await client.post(f"/api/invoices/{invoice['id']}/escalate", headers=headers)).status_code == 200
    r = await client.post(f"/api/invoices/{invoice['id']}/escalate", headers=headers)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_another_signed_in_user_cannot_touch_the_invoice(client, fake_db, monkeypatch):
    """Two real accounts: user B can't read, escalate, approve or chat on user A's invoice."""
    owner = signed_in(fake_db, "user-a")
    r = await client.post("/api/invoices", headers=owner, json={
        "invoice_id": "INV-A-1", "client_name": "Client Co.", "client_email": "sam@clientco.com",
        "invoice_amount": 5000, "amount_paid": 0, "days_overdue": 14, "jurisdiction": "Oregon",
    })
    invoice = r.json()["invoice"]

    intruder = signed_in(fake_db, "user-b")
    for method, path, body in [
        ("get", f"/api/invoices/{invoice['id']}/history", None),
        ("post", f"/api/invoices/{invoice['id']}/escalate", None),
        ("post", f"/api/invoices/{invoice['id']}/resume", {"decision": "approve"}),
        ("post", "/api/chat", {"thread_id": f"invoice-{invoice['id']}", "message": "what is the invoice status"}),
        ("patch", f"/api/invoices/{invoice['id']}/details", {"client_email": "attacker@evil.example"}),
    ]:
        kwargs = {"headers": intruder}
        if body is not None:
            kwargs["json"] = body
        r = await getattr(client, method)(path, **kwargs)
        assert r.status_code == 404, (path, r.status_code, r.text)

    listed = (await client.get("/api/invoices", headers=intruder)).json()
    assert invoice["id"] not in [i["id"] for i in listed]
