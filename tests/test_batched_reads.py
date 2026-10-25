"""The dashboard list and the agent's invoice context must not make one
database call per invoice (N+1): that is what made first loads slow."""
import pytest

from tests.test_approve_sends_email import signed_in


async def make_invoices(client, headers, n):
    ids = []
    for i in range(n):
        r = await client.post("/api/invoices", headers=headers, json={
            "invoice_id": f"BATCH-{i}", "client_name": f"Client {i}", "client_email": f"c{i}@example.com",
            "invoice_amount": 100, "amount_paid": 0, "days_overdue": i, "jurisdiction": "Oregon"})
        assert r.status_code == 200, r.text
        ids.append(r.json()["invoice"]["id"])
    return ids


def comm_reads(fake_db):
    return [r for r in fake_db.requests if r[0] == "GET" and r[1] == "communication_history"]


def test_batch_helper_groups_communications_by_invoice(fake_db):
    from src import db
    for inv, ts in [("a", "2"), ("b", "1"), ("a", "1")]:
        db.add_communication(invoice_id=inv, comm_type="note", subject=f"{inv}{ts}", content="", direction="outbound")
        fake_db.communications[-1]["timestamp"] = ts
    fake_db.requests.clear()
    grouped = db.get_communications_for(["a", "b", "c"])
    assert [c["subject"] for c in grouped["a"]] == ["a1", "a2"]
    assert [c["subject"] for c in grouped["b"]] == ["b1"]
    assert grouped["c"] == []
    assert len(comm_reads(fake_db)) == 1
    assert db.get_communications_for([]) == {}


@pytest.mark.asyncio
async def test_invoice_list_reads_communications_once_for_many_invoices(client, fake_db):
    headers = signed_in(fake_db)
    ids = await make_invoices(client, headers, 6)
    fake_db.requests.clear()

    r = await client.get("/api/invoices", headers=headers)

    assert r.status_code == 200 and len(r.json()) == 6
    assert len(comm_reads(fake_db)) == 1
    assert {i["id"] for i in r.json()} == set(ids)
    assert all("communication_history" in i for i in r.json())


@pytest.mark.asyncio
async def test_agent_context_reads_communications_once(client, fake_db):
    import api.index as api_index
    headers = signed_in(fake_db)
    ids = await make_invoices(client, headers, 6)
    fake_db.requests.clear()

    summary = api_index.build_user_invoice_context(ids[0], "user-1")

    assert "Client 0" in summary
    assert len(comm_reads(fake_db)) == 1
