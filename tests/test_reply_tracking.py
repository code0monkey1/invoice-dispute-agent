"""Reply tracking through Resend Inbound, and send-only Gmail access.

Approved emails go out from the freelancer's Gmail with a Reply-To of
inv-<token>@<id>.resend.app. Resend posts each reply to /api/email/inbound,
where the token finds the one invoice it belongs to.
"""
import base64
import hashlib
import hmac
import json
import time
import urllib.parse

import pytest

INBOUND_DOMAIN = "abc123.resend.app"
WEBHOOK_SECRET_RAW = b"test-webhook-signing-key-32bytes!"
WEBHOOK_SECRET = "whsec_" + base64.b64encode(WEBHOOK_SECRET_RAW).decode()


@pytest.fixture(autouse=True)
def resend_env(monkeypatch):
    monkeypatch.setenv("RESEND_INBOUND_DOMAIN", INBOUND_DOMAIN)
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setenv("RESEND_API_KEY", "re_test")


def sign(body: bytes, msg_id="msg_1", timestamp=None, secret=WEBHOOK_SECRET_RAW):
    timestamp = str(int(time.time()) if timestamp is None else timestamp)
    signed = f"{msg_id}.{timestamp}.".encode() + body
    sig = base64.b64encode(hmac.new(secret, signed, hashlib.sha256).digest()).decode()
    return {"svix-id": msg_id, "svix-timestamp": timestamp, "svix-signature": f"v1,{sig}"}


# ─── Token and address helpers ───────────────────────────────────────────────

def test_reply_tokens_are_random_and_email_safe():
    from src.services import resend_inbound
    a, b = resend_inbound.new_reply_token(), resend_inbound.new_reply_token()
    assert a != b
    assert len(a) == 20 and a.isalnum() and a == a.lower()


def test_reply_address_uses_the_inbound_domain():
    from src.services import resend_inbound
    assert resend_inbound.reply_address("deadbeef") == f"inv-deadbeef@{INBOUND_DOMAIN}"


def test_reply_address_is_none_when_inbound_is_not_configured(monkeypatch):
    from src.services import resend_inbound
    monkeypatch.delenv("RESEND_INBOUND_DOMAIN")
    assert resend_inbound.reply_address("deadbeef") is None


def test_parse_reply_token_finds_our_address_only():
    from src.services import resend_inbound
    addrs = ["Lena <lena@lenapark.studio>", f"INV-ABCdef0123@{INBOUND_DOMAIN.upper()}"]
    assert resend_inbound.parse_reply_token(addrs) == "abcdef0123"
    assert resend_inbound.parse_reply_token([f"inv-abc@other.resend.app"]) is None
    assert resend_inbound.parse_reply_token([]) is None


# ─── Webhook signatures ──────────────────────────────────────────────────────

def test_verify_webhook_accepts_a_valid_signature():
    from src.services import resend_inbound
    body = b'{"type":"email.received"}'
    resend_inbound.verify_webhook(body, sign(body), WEBHOOK_SECRET)


@pytest.mark.parametrize("tamper", ["body", "secret", "stale"])
def test_verify_webhook_rejects_tampering(tamper):
    from src.services import resend_inbound
    body = b'{"type":"email.received"}'
    headers = sign(body)
    if tamper == "body":
        body = b'{"type":"email.received","x":1}'
    elif tamper == "secret":
        headers = sign(body, secret=b"wrong-secret")
    else:
        headers = sign(body, timestamp=int(time.time()) - 3600)
    with pytest.raises(ValueError):
        resend_inbound.verify_webhook(body, headers, WEBHOOK_SECRET)


# ─── Inbound endpoint ────────────────────────────────────────────────────────

async def create_invoice(client, invoice_id):
    r = await client.post("/api/invoices", json={
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


def received_event(to):
    return json.dumps({
        "type": "email.received",
        "data": {
            "email_id": "em_1",
            "from": "Sam <ap@acme.example>",
            "to": to,
            "cc": [],
            "subject": "Re: A reminder about invoice INV-1",
        },
    }).encode()


@pytest.fixture
def inbound_fakes(monkeypatch):
    import api.index as api_index
    agent_calls = []
    monkeypatch.setattr(api_index, "fetch_received_email", lambda email_id: {
        "text": "Sorry, this slipped through. Paying on Friday.", "html": None,
    })
    monkeypatch.setattr(api_index, "invoke_agent_with_retry",
                        lambda payload, *, context, config: agent_calls.append(config) or {"messages": []})
    return agent_calls


@pytest.mark.asyncio
async def test_inbound_reply_is_stored_on_the_matching_invoice(client, fake_db, inbound_fakes):
    import api.index as api_index
    invoice = await create_invoice(client, "INV-IN-1")
    other = await create_invoice(client, "INV-IN-2")
    token = api_index.ensure_reply_token(invoice["id"])
    api_index.ensure_reply_token(other["id"])

    body = received_event([f"inv-{token}@{INBOUND_DOMAIN}"])
    r = await client.post("/api/email/inbound", content=body, headers=sign(body))

    assert r.status_code == 200, r.text
    assert r.json()["status"] == "stored"
    replies = [c for c in api_index.get_communications(invoice["id"]) if c.get("direction") == "inbound"]
    assert len(replies) == 1
    assert "Paying on Friday" in replies[0]["content"]
    # Separation: the other invoice is untouched.
    assert not [c for c in api_index.get_communications(other["id"]) if c.get("direction") == "inbound"]
    # The agent was asked to analyse the reply on this invoice's thread.
    assert inbound_fakes == [{"configurable": {"thread_id": f"invoice-{invoice['id']}"}}]


@pytest.mark.asyncio
async def test_inbound_rejects_a_bad_signature(client, fake_db, inbound_fakes):
    body = received_event([f"inv-abc@{INBOUND_DOMAIN}"])
    headers = sign(body, secret=b"wrong-secret")
    r = await client.post("/api/email/inbound", content=body, headers=headers)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_inbound_ignores_unknown_tokens(client, fake_db, inbound_fakes):
    body = received_event([f"inv-0000000000ffffffffff@{INBOUND_DOMAIN}"])
    r = await client.post("/api/email/inbound", content=body, headers=sign(body))
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"
    assert inbound_fakes == []


# ─── Reply-To on approved emails ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_approved_email_carries_the_tracking_reply_to(client, fake_db, monkeypatch):
    from tests.test_approve_sends_email import FakeAgent, DRAFT, signed_in
    import api.index as api_index

    agent = FakeAgent()
    monkeypatch.setattr(api_index, "agent", agent)
    sent = []
    monkeypatch.setattr(api_index, "get_user_gmail_tokens", lambda user_id: ("access", "refresh"))
    monkeypatch.setattr(api_index, "send_email_via_gmail",
                        lambda user_id, to, subject, body, thread_id=None, attachments=None, reply_to=None:
                        sent.append(reply_to) or {"id": "m1", "threadId": "t1"})

    headers = signed_in(fake_db)
    r = await client.post("/api/invoices", headers=headers, json={
        "invoice_id": "INV-RT-1", "client_name": "Acme Corp", "client_email": "ap@acme.example",
        "invoice_amount": 1200, "amount_paid": 0, "days_overdue": 14, "jurisdiction": "California",
    })
    invoice = r.json()["invoice"]
    agent.ask_for_approval()

    await client.post(f"/api/invoices/{invoice['id']}/resume", headers=headers,
                      json={"decision": "approve", "message": DRAFT})

    token = api_index.get_invoice(invoice["id"])["reply_token"]
    assert sent == [[f"inv-{token}@{INBOUND_DOMAIN}", "owner@example.com"]]


# ─── Google permissions ──────────────────────────────────────────────────────

def scopes_of(url: str) -> set[str]:
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    return set(query["scope"][0].split())


@pytest.mark.asyncio
async def test_sign_in_asks_for_basic_permissions_only(client):
    r = await client.get("/api/auth/google/url")
    scopes = scopes_of(r.json()["url"])
    assert scopes == {
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    }


@pytest.mark.asyncio
async def test_connect_gmail_asks_for_send_only(client, fake_db):
    from tests.test_approve_sends_email import signed_in
    r = await client.get("/api/auth/gmail/connect-url", headers=signed_in(fake_db))
    assert r.status_code == 200, r.text
    scopes = scopes_of(r.json()["url"])
    assert "https://www.googleapis.com/auth/gmail.send" in scopes
    assert not any("gmail.readonly" in s or "gmail.modify" in s for s in scopes)


@pytest.mark.asyncio
async def test_connect_gmail_requires_sign_in(client):
    r = await client.get("/api/auth/gmail/connect-url")
    assert r.status_code == 401


def test_signing_in_again_keeps_an_existing_gmail_connection(fake_db):
    from src import db
    db.upsert_user("u-keep", "u@example.com", "U", "", access_token="acc", refresh_token="ref")
    db.upsert_user("u-keep", "u@example.com", "U", "", access_token=None, refresh_token=None)
    assert db.get_user_gmail_tokens("u-keep") == ("acc", "ref")
