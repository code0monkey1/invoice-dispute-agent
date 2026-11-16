"""Invoice routes, pinned where the order of checks is visible to the caller.

Written before the routes moved into web/routers/invoices.py (task 5.3): the
check that answers first, and what is stored when a request is refused,
must not change in the move.
"""
import json

import pytest

from tests.test_generated_invoice import VALID_BODY, _get_user_id

UPLOAD_METADATA = {
    "invoice_id": "INV-UP-1", "client_name": "Acme Corp", "client_email": "ap@acme.example",
    "invoice_amount": 1200, "amount_paid": 0, "days_overdue": 30, "jurisdiction": "California",
}


async def upload(client, metadata=UPLOAD_METADATA, content=b"%PDF-1.4 invoice"):
    return await client.post(
        "/api/invoices/upload",
        files={"file": ("invoice.pdf", content, "application/pdf")},
        data={"metadata": json.dumps(metadata)},
    )


@pytest.mark.asyncio
async def test_an_uploaded_invoice_stores_its_file_and_starts_unpaid(client, fake_db):
    r = await upload(client)
    assert r.status_code == 200, r.text
    invoice = r.json()["invoice"]
    assert invoice["invoice_file_name"] == "invoice.pdf" and invoice["invoice_file_mime"] == "application/pdf"
    assert fake_db.storage[invoice["invoice_file_path"]] == b"%PDF-1.4 invoice"
    assert r.json()["state"]["escalation_level"] == 1 and r.json()["state"]["status"] == "active"


@pytest.mark.asyncio
async def test_a_duplicate_upload_is_refused_before_its_file_is_stored(client, fake_db):
    assert (await upload(client)).status_code == 200
    stored_before = dict(fake_db.storage)

    r = await upload(client, content=b"%PDF-1.4 second copy")

    assert r.status_code == 409
    assert r.json()["detail"] == "Invoice 'INV-UP-1' already exists"
    assert fake_db.storage == stored_before


@pytest.mark.asyncio
async def test_a_duplicate_upload_is_409_even_when_the_file_is_too_large(client, fake_db):
    import api.index as api_index
    assert (await upload(client)).status_code == 200
    r = await upload(client, content=b"x" * (api_index.MAX_UPLOAD_BYTES + 1))
    assert r.status_code == 409


async def generated(client, user_id, **changes):
    body = {**VALID_BODY, "storage_path": f"generated/{user_id}/abc/INV-2026-001.pdf", **changes}
    return await client.post("/api/invoices/generated", json=body)


@pytest.mark.asyncio
async def test_a_duplicate_generated_invoice_is_409_before_its_due_date_is_read(client, fake_db):
    user_id = await _get_user_id(client)
    assert (await generated(client, user_id)).status_code == 201
    r = await generated(client, user_id, due_date="not a date")
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_a_due_date_without_leading_zeros_is_accepted(client, fake_db):
    user_id = await _get_user_id(client)
    r = await generated(client, user_id, due_date="2026-1-5")
    assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_settling_returns_the_paid_invoice_and_drops_history(client, fake_db):
    r = await client.post("/api/invoices", json=UPLOAD_METADATA)
    invoice_id = r.json()["invoice"]["id"]
    r = await client.post(f"/api/invoices/{invoice_id}/settle")
    assert r.status_code == 200
    settled = r.json()["invoice"]
    assert settled["status"] == "paid" and settled["communication_history"] == []
    assert settled["invoice_id"] == "INV-UP-1" and settled["balance_due"] == 1200.0
