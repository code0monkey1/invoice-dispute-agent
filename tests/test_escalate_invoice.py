"""Escalating is the user's call, so the button must change the level itself
rather than hoping the model calls its escalate tool."""
import pytest
from langchain_core.messages import AIMessage


async def _create_invoice(client, invoice_id="INV-ESC-1"):
    r = await client.post("/api/invoices", json={
        "invoice_id": invoice_id,
        "client_name": "Acme Corp",
        "client_email": "ap@acme.example",
        "invoice_amount": 1200,
        "amount_paid": 0,
        "days_overdue": 30,
        "jurisdiction": "California",
    })
    assert r.status_code == 200, r.text
    return r.json()["invoice"]


def _fake_agent(monkeypatch, *, fail=False):
    import api.index as api_index
    calls = []

    def fake_invoke(payload, *, context, config):
        calls.append(payload["messages"][0].content)
        if fail:
            raise RuntimeError("AI service error")
        return {"messages": [AIMessage(content="Here is a formal draft.")], "escalation_level": 2}

    monkeypatch.setattr(api_index, "invoke_agent_with_retry", fake_invoke)
    return calls


@pytest.mark.asyncio
async def test_escalate_raises_the_level_and_asks_for_a_draft(client, fake_db, monkeypatch):
    invoice = await _create_invoice(client)
    calls = _fake_agent(monkeypatch)

    r = await client.post(f"/api/invoices/{invoice['id']}/escalate")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["state"]["escalation_level"] == 2
    import api.index as api_index
    assert api_index.get_invoice(invoice["id"])["escalation_level"] == 2
    assert len(calls) == 1 and "Formal" in calls[0]


@pytest.mark.asyncio
async def test_escalation_sticks_even_if_the_agent_cannot_draft(client, fake_db, monkeypatch):
    invoice = await _create_invoice(client, "INV-ESC-2")
    _fake_agent(monkeypatch, fail=True)

    r = await client.post(f"/api/invoices/{invoice['id']}/escalate")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["state"]["escalation_level"] == 2
    assert "couldn't draft" in body["messages"][-1]["content"]


@pytest.mark.asyncio
async def test_cannot_escalate_past_legal(client, fake_db, monkeypatch):
    invoice = await _create_invoice(client, "INV-ESC-3")
    _fake_agent(monkeypatch)
    import api.index as api_index
    api_index.update_invoice(invoice["id"], escalation_level=3)

    r = await client.post(f"/api/invoices/{invoice['id']}/escalate")
    assert r.status_code == 400
    assert "highest level" in r.json()["detail"]


@pytest.mark.asyncio
async def test_cannot_escalate_someone_elses_invoice(client, fake_db, monkeypatch):
    _fake_agent(monkeypatch)
    r = await client.post("/api/invoices/someone-else__inv__SU5WLTk/escalate")
    assert r.status_code == 404
