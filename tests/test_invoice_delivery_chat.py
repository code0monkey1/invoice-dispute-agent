from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage


async def _create_invoice(client, invoice_id="INV-DEL-1", client_name="Acme Corp"):
    response = await client.post(
        "/api/invoices",
        json={
            "invoice_id": invoice_id,
            "client_name": client_name,
            "client_email": "ap@acme.example",
            "invoice_amount": 1200,
            "amount_paid": 0,
            "days_overdue": 0,
            "jurisdiction": "California",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["invoice"]


@pytest.mark.asyncio
async def test_chat_blocks_unrelated_questions(client, fake_db, monkeypatch):
    invoice = await _create_invoice(client)

    import api.index as api_index

    def fail_invoke(*args, **kwargs):
        raise AssertionError("LLM should not be called for unrelated chat")

    monkeypatch.setattr(api_index, "invoke_agent_with_retry", fail_invoke)

    response = await client.post(
        "/api/chat",
        json={"thread_id": f"invoice-{invoice['id']}", "message": "What is the weather tomorrow?"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["messages"][-1]["content"] == "I can only answer questions about your invoices."
    assert body["interrupt"] is None


@pytest.mark.asyncio
async def test_chat_allows_invoice_related_questions(client, fake_db, monkeypatch):
    invoice = await _create_invoice(client, invoice_id="INV-ALLOW-1")

    import api.index as api_index

    called = False

    def fake_invoke(payload, *, context, config):
        nonlocal called
        called = True
        return {
            "messages": [AIMessage(content="Invoice answer")],
            "client_name": "Acme Corp",
            "client_email": "ap@acme.example",
            "invoice_id": "INV-ALLOW-1",
            "invoice_amount": 1200,
            "amount_paid": 0,
            "balance_due": 1200,
            "days_overdue": 0,
            "jurisdiction": "California",
            "escalation_level": 1,
            "status": "active",
            "communication_history": [],
        }

    monkeypatch.setattr(api_index, "invoke_agent_with_retry", fake_invoke)

    response = await client.post(
        "/api/chat",
        json={"thread_id": f"invoice-{invoice['id']}", "message": "What is the balance for INV-ALLOW-1?"},
    )

    assert response.status_code == 200, response.text
    assert called
    assert response.json()["messages"][-1]["content"] == "Invoice answer"


def test_delivery_draft_interrupt_uses_tool_args():
    import api.index as api_index

    response = {
        "__interrupt__": [
            SimpleNamespace(value={
                "action_requests": [{
                    "name": "draft_invoice_delivery_email",
                    "args": {
                        "subject": "Invoice INV-9",
                        "body": "Hi Acme,\n\nPlease see the attached invoice.",
                    },
                }]
            })
        ],
        "client_name": "Acme Corp",
        "client_email": "ap@acme.example",
        "invoice_id": "INV-9",
        "invoice_amount": 500,
        "amount_paid": 0,
        "balance_due": 500,
        "days_overdue": 0,
        "jurisdiction": "California",
        "escalation_level": 1,
        "status": "active",
        "communication_history": [],
    }

    interrupt = api_index.extract_interrupt(response)

    assert interrupt["tool"] == "draft_invoice_delivery_email"
    assert interrupt["description"] == "Subject: Invoice INV-9\n\nHi Acme,\n\nPlease see the attached invoice."


def test_serialize_messages_flattens_structured_content():
    import api.index as api_index

    messages = [
        AIMessage(content=[
            {"type": "text", "text": "This invoice is for design work."},
            {"type": "text", "text": "The client is Northwind Apparel LLC."},
        ])
    ]

    serialized = api_index.serialize_messages(messages)

    assert serialized[0]["content"] == (
        "This invoice is for design work.\n"
        "The client is Northwind Apparel LLC."
    )


@pytest.mark.asyncio
async def test_approved_delivery_email_attaches_invoice_file(client, fake_db, monkeypatch):
    import api.index as api_index
    from src.db import build_invoice_storage_id

    user_id = "user-123"
    storage_id = build_invoice_storage_id(user_id, "INV-ATTACH-1")
    fake_db.users[user_id] = {"id": user_id, "email": "owner@example.com", "name": "Owner"}
    fake_db.invoices[storage_id] = {
        "id": storage_id,
        "user_id": user_id,
        "client_name": "Acme Corp",
        "client_email": "ap@acme.example",
        "invoice_amount": 1200,
        "amount_paid": 0,
        "days_overdue": 0,
        "jurisdiction": "California",
        "escalation_level": 1,
        "status": "active",
        "invoice_file_path": "generated/user-123/abc/invoice.pdf",
        "invoice_file_name": "invoice.pdf",
        "invoice_file_mime": "application/pdf",
        "invoice_file_size": 11,
    }
    fake_db.storage["generated/user-123/abc/invoice.pdf"] = b"pdf-content"

    monkeypatch.setattr(api_index, "get_current_user", lambda authorization: fake_db.users[user_id])
    monkeypatch.setattr(api_index, "_current_caller_id", lambda request, authorization: user_id)
    monkeypatch.setattr(api_index, "get_user_gmail_tokens", lambda uid: ("access", "refresh"))
    monkeypatch.setattr(api_index, "download_invoice_file", lambda bucket, path: fake_db.storage[path])
    monkeypatch.setattr(api_index.agent, "update_state", lambda *args, **kwargs: None)

    state = {
        "messages": [AIMessage(content="Draft ready")],
        "client_name": "Acme Corp",
        "client_email": "ap@acme.example",
        "invoice_id": "INV-ATTACH-1",
        "invoice_amount": 1200,
        "amount_paid": 0,
        "balance_due": 1200,
        "days_overdue": 0,
        "jurisdiction": "California",
        "escalation_level": 1,
        "status": "active",
        "communication_history": [],
    }
    interrupt = SimpleNamespace(value={
        "action_requests": [{
            "name": "draft_invoice_delivery_email",
            "args": {
                "subject": "Invoice INV-ATTACH-1",
                "body": "Hi Acme,\n\nPlease see the attached invoice.",
            },
        }]
    })
    task = SimpleNamespace(interrupts=[interrupt])
    monkeypatch.setattr(api_index.agent, "get_state", lambda config: SimpleNamespace(values=state, tasks=[task]))
    monkeypatch.setattr(api_index.agent, "invoke", lambda *args, **kwargs: state)

    sent = {}

    class FakeGmailService:
        def __init__(self, *args, **kwargs):
            pass

        def send_email(self, to, subject, body, thread_id=None, attachments=None):
            sent.update({
                "to": to,
                "subject": subject,
                "body": body,
                "attachments": attachments,
            })
            return {"id": "msg-1", "threadId": "thread-1"}

    monkeypatch.setattr(api_index, "GmailService", FakeGmailService)

    response = await client.post(
        f"/api/invoices/{storage_id}/resume",
        headers={"Authorization": "Bearer test"},
        json={
            "decision": "approve",
            "message": "Subject: Edited Invoice Subject\n\nEdited invoice body.",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email_sent"] is True
    assert sent["to"] == "ap@acme.example"
    assert sent["subject"] == "Edited Invoice Subject"
    assert sent["body"] == "Edited invoice body."
    assert sent["attachments"][0]["filename"] == "invoice.pdf"
    assert sent["attachments"][0]["content"] == b"pdf-content"
    assert fake_db.communications[0]["direction"] == "outbound"
    assert fake_db.communications[0]["subject"] == "Edited Invoice Subject"
    assert fake_db.communications[0]["content"] == "Edited invoice body."
