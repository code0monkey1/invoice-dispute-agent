"""GET /api/invoices/{id}/traces: an invoice's agent runs and their steps, for its owner only."""
import pytest

from tests.test_approve_sends_email import create_invoice, signed_in
from tests.test_real_graph_payments import scripted, tool_call  # noqa: F401

GUEST_COOKIE = "ic_guest_session"


def seed_runs(fake_db, invoice_id, count, user_id="user-1"):
    """Runs one minute apart, oldest first, each with two steps stored out of order."""
    for n in range(count):
        run_id = f"run-{n:02d}"
        fake_db.agent_runs.append({
            "id": run_id, "invoice_id": invoice_id, "user_id": user_id, "kind": "chat", "status": "ok",
            "started_at": f"2026-11-06T10:{n:02d}:00.000+00:00", "latency_ms": 100 + n,
        })
        fake_db.trace_steps.append({"run_id": run_id, "seq": 2, "type": "interrupt", "name": "draft_polite_reminder", "payload": {}})
        fake_db.trace_steps.append({"run_id": run_id, "seq": 1, "type": "model_call", "name": "model", "payload": {}})


@pytest.mark.asyncio
async def test_owner_sees_runs_newest_first_with_ordered_steps(client, fake_db):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    seed_runs(fake_db, invoice["id"], 3)

    r = await client.get(f"/api/invoices/{invoice['id']}/traces", headers=headers)

    assert r.status_code == 200, r.text
    body = r.json()
    assert [run["id"] for run in body["runs"]] == ["run-02", "run-01", "run-00"]
    assert [s["seq"] for s in body["runs"][0]["steps"]] == [1, 2]
    assert body["next_before"] is None
    # Steps for every run come from one query, not one per run.
    step_reads = [req for req in fake_db.requests if req[0] == "GET" and req[1] == "agent_trace_steps"]
    assert len(step_reads) == 1


@pytest.mark.asyncio
async def test_pages_with_a_started_at_cursor(client, fake_db):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    seed_runs(fake_db, invoice["id"], 5)

    first = (await client.get(f"/api/invoices/{invoice['id']}/traces?limit=2", headers=headers)).json()
    assert [run["id"] for run in first["runs"]] == ["run-04", "run-03"]
    assert first["next_before"] == "2026-11-06T10:03:00.000+00:00"

    second = await client.get(f"/api/invoices/{invoice['id']}/traces",
                              params={"limit": 2, "before": first["next_before"]}, headers=headers)
    assert [run["id"] for run in second.json()["runs"]] == ["run-02", "run-01"]


@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["limit=0", "limit=51", "limit=abc", "before=yesterday"])
async def test_bad_paging_is_rejected_loudly(client, fake_db, query):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    r = await client.get(f"/api/invoices/{invoice['id']}/traces?{query}", headers=headers)
    assert r.status_code == 422, (query, r.status_code)


@pytest.mark.asyncio
async def test_no_runs_is_an_empty_list(client, fake_db):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    r = await client.get(f"/api/invoices/{invoice['id']}/traces", headers=headers)
    assert r.json() == {"runs": [], "next_before": None}


@pytest.mark.asyncio
async def test_another_user_cannot_read_the_traces(client, fake_db):
    owner = signed_in(fake_db, "user-1")
    invoice = await create_invoice(client, owner)
    seed_runs(fake_db, invoice["id"], 1)

    intruder = signed_in(fake_db, "user-2")
    r = await client.get(f"/api/invoices/{invoice['id']}/traces", headers=intruder)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_malformed_invoice_id_never_reaches_the_database(client, fake_db):
    headers = signed_in(fake_db)
    r = await client.get("/api/invoices/%27%20OR%201%3D1--/traces", headers=headers)
    assert r.status_code == 404
    assert not [req for req in fake_db.requests if req[1] == "agent_runs"]


@pytest.mark.asyncio
async def test_a_guest_reads_their_own_traces(client, fake_db, scripted):
    invoice = await create_invoice(client)  # guest session via cookie
    scripted.replies = [tool_call("draft_polite_reminder")]
    await client.post("/api/chat", json={"thread_id": f"invoice-{invoice['id']}", "message": "Draft a reminder for this invoice"})

    r = await client.get(f"/api/invoices/{invoice['id']}/traces")
    assert r.status_code == 200
    [run] = r.json()["runs"]
    assert [s["type"] for s in run["steps"]] == ["model_call", "interrupt"]


@pytest.mark.asyncio
async def test_traces_follow_a_guest_who_signs_in(client, fake_db):
    from src.db import migrate_guest_to_user
    invoice = await create_invoice(client)
    guest_id = invoice["id"].split("__inv__")[0]
    seed_runs(fake_db, invoice["id"], 2, user_id=guest_id)

    fake_db.users["user-9"] = {"id": "user-9", "email": "nine@example.com"}
    migrate_guest_to_user(guest_id, "user-9")

    assert {run["user_id"] for run in fake_db.agent_runs} == {"user-9"}


@pytest.mark.asyncio
async def test_database_outage_is_a_503_not_a_crash(client, fake_db):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    fake_db.down_tables = {"agent_runs"}
    r = await client.get(f"/api/invoices/{invoice['id']}/traces", headers=headers)
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_signing_in_still_works_if_the_trace_table_is_unavailable(client, fake_db):
    """Traces are optional: a missing or down trace table must never block moving a guest's invoices."""
    from src.db import migrate_guest_to_user
    invoice = await create_invoice(client)
    guest_id = invoice["id"].split("__inv__")[0]
    fake_db.users["user-9"] = {"id": "user-9", "email": "nine@example.com"}
    fake_db.down_tables = {"agent_runs"}

    migrate_guest_to_user(guest_id, "user-9")

    assert fake_db.invoices[invoice["id"]]["user_id"] == "user-9"
