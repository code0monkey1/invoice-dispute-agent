"""The dashboard's "Waiting for you" queue reads awaiting_approval from the invoice list."""
from types import SimpleNamespace

import pytest


async def _create_invoice(client, invoice_id):
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


def _snapshot_with_draft(tool_name):
    interrupt = SimpleNamespace(value={"action_requests": [{"name": tool_name, "args": {}}]})
    return SimpleNamespace(values={"messages": []}, tasks=[SimpleNamespace(interrupts=[interrupt])])


@pytest.mark.asyncio
async def test_invoice_list_flags_invoices_waiting_for_approval(client, fake_db, monkeypatch):
    waiting = await _create_invoice(client, "INV-WAIT-1")
    idle = await _create_invoice(client, "INV-IDLE-1")

    import api.index as api_index

    def fake_get_state(config):
        if config["configurable"]["thread_id"] == f"invoice-{waiting['id']}":
            return _snapshot_with_draft("draft_polite_reminder")
        return SimpleNamespace(values={"messages": []}, tasks=[])

    monkeypatch.setattr(api_index.agent, "get_state", fake_get_state)

    r = await client.get("/api/invoices")
    assert r.status_code == 200, r.text
    by_id = {inv["id"]: inv for inv in r.json()}

    assert by_id[waiting["id"]]["awaiting_approval"] is True
    assert by_id[waiting["id"]]["pending_action"] == "draft_polite_reminder"
    assert by_id[idle["id"]]["awaiting_approval"] is False
    assert by_id[idle["id"]]["pending_action"] is None


@pytest.mark.asyncio
async def test_invoice_list_still_loads_when_agent_state_is_unavailable(client, fake_db, monkeypatch):
    invoice = await _create_invoice(client, "INV-ERR-1")

    import api.index as api_index

    def broken_get_state(config):
        raise RuntimeError("checkpointer down")

    monkeypatch.setattr(api_index.agent, "get_state", broken_get_state)

    r = await client.get("/api/invoices")
    assert r.status_code == 200, r.text
    row = next(inv for inv in r.json() if inv["id"] == invoice["id"])
    assert row["awaiting_approval"] is False
