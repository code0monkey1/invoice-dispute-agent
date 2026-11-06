"""Opening an invoice must never lose an approval card that is waiting.

LangGraph's update_state() empties a pending interrupt. /history synced the
database into agent state before reading it, and the sync saw a difference
that wasn't one (follow_up_date None in state vs '' from the database), so a
card proposed by a client-reply run vanished the first time the user opened
the chat. Found by the golden-set eval (evals/golden/level_1.yaml).
"""
from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage

from tests.test_approve_sends_email import create_invoice, sent, signed_in  # noqa: F401
from tests.test_real_graph_payments import scripted, tool_call  # noqa: F401


@pytest.mark.asyncio
async def test_a_card_from_a_client_reply_survives_opening_the_chat(client, fake_db, scripted):
    import api.index as api_index
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [tool_call("mark_invoice_pending", follow_up_date="2026-12-01")]
    api_index.handle_client_reply(fake_db.invoices[invoice["id"]], "ap@acme.example", "Re: invoice", "We'll pay on 2026-12-01.")

    for _ in range(2):  # opening it twice changes nothing
        r = await client.get(f"/api/invoices/{invoice['id']}/history", headers=headers)
        assert r.json()["interrupt"]["tool"] == "mark_invoice_pending"

    r = await client.post(f"/api/invoices/{invoice['id']}/resume", headers=headers, json={"decision": "approve"})
    assert r.status_code == 200, r.text
    assert fake_db.invoices[invoice["id"]]["status"] == "pending"
    assert fake_db.invoices[invoice["id"]]["follow_up_date"] == "2026-12-01"


@pytest.mark.asyncio
async def test_reloading_a_drafted_reminder_keeps_it_sendable(client, fake_db, scripted, sent):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [tool_call("draft_polite_reminder"), AIMessage(content="Sent.")]
    await client.post("/api/chat", headers=headers, json={"thread_id": f"invoice-{invoice['id']}", "message": "Draft a polite reminder for this invoice"})

    for _ in range(2):
        r = await client.get(f"/api/invoices/{invoice['id']}/history", headers=headers)
        assert r.json()["interrupt"]["tool"] == "draft_polite_reminder"

    r = await client.post(f"/api/invoices/{invoice['id']}/resume", headers=headers, json={"decision": "approve"})
    assert r.status_code == 200 and len(sent) == 1


def test_sync_does_not_treat_empty_values_as_changes():
    import api.index as api_index

    class Snapshot:
        values = {"follow_up_date": None, "status": "active", "client_name": "Acme"}
        tasks = ()

    with patch.object(api_index, "get_invoice", return_value={"id": "x"}), \
         patch.object(api_index, "invoice_state_from_db", return_value={"follow_up_date": "", "status": "active", "client_name": "Acme"}), \
         patch.object(api_index.agent, "get_state", return_value=Snapshot()), \
         patch.object(api_index.agent, "update_state") as update_state:
        api_index.sync_agent_state_from_invoice("x", {"configurable": {"thread_id": "invoice-x"}})
    update_state.assert_not_called()
