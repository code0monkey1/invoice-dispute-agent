"""Creating an invoice rejects values that can't be a real invoice.

Found by pen-testing production: a negative amount was accepted (and saved as
already settled), inf/NaN amounts returned 500, and two creates racing on the
same invoice number returned 500 instead of 409.
"""
import json
import os

import pytest

from tests.test_approve_sends_email import fake_agent, signed_in  # noqa: F401

_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")


def body(**overrides):
    data = {
        "invoice_id": "INV-VAL-1", "client_name": "Acme Corp", "client_email": "ap@acme.example",
        "invoice_amount": 1200, "amount_paid": 0, "days_overdue": 14, "jurisdiction": "California",
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize("overrides", [
    {"invoice_amount": -50},
    {"invoice_amount": 0},
    {"amount_paid": -1},
    {"days_overdue": -3},
    {"invoice_id": "   "},
    {"client_name": ""},
])
@pytest.mark.asyncio
async def test_impossible_values_are_rejected(client, fake_db, fake_agent, overrides):
    headers = signed_in(fake_db)
    r = await client.post("/api/invoices", headers=headers, json=body(**overrides))
    assert r.status_code == 422, r.text
    assert fake_db.invoices == {}


@pytest.mark.parametrize("literal", ["1e309", "NaN", "Infinity", "-Infinity"])
@pytest.mark.asyncio
async def test_non_finite_amounts_are_422_not_500(client, fake_db, fake_agent, literal):
    headers = signed_in(fake_db)
    raw = json.dumps(body()).replace('"invoice_amount": 1200', f'"invoice_amount": {literal}')
    r = await client.post("/api/invoices", headers={**headers, "Content-Type": "application/json"}, content=raw)
    assert r.status_code == 422, r.text
    assert fake_db.invoices == {}


@pytest.mark.asyncio
async def test_a_normal_invoice_is_still_created(client, fake_db, fake_agent):
    headers = signed_in(fake_db)
    r = await client.post("/api/invoices", headers=headers, json=body(amount_paid=200))
    assert r.status_code == 200, r.text
    assert r.json()["invoice"]["status"] == "active"


@pytest.mark.asyncio
async def test_invoice_numbers_are_trimmed_so_spaces_cannot_duplicate(client, fake_db, fake_agent):
    headers = signed_in(fake_db)
    first = await client.post("/api/invoices", headers=headers, json=body(invoice_id="INV-SPACE"))
    assert first.status_code == 200, first.text
    assert first.json()["invoice"]["invoice_id"] == "INV-SPACE"

    second = await client.post("/api/invoices", headers=headers, json=body(invoice_id="  INV-SPACE  "))
    assert second.status_code == 409, second.text
    assert len(fake_db.invoices) == 1


@pytest.mark.asyncio
async def test_same_number_for_two_users_is_two_invoices(client, fake_db, fake_agent):
    one = signed_in(fake_db, "user-1")
    two = signed_in(fake_db, "user-2")
    assert (await client.post("/api/invoices", headers=one, json=body(invoice_id="INV-001"))).status_code == 200
    assert (await client.post("/api/invoices", headers=two, json=body(invoice_id="INV-001"))).status_code == 200
    assert len(fake_db.invoices) == 2
    owners = sorted(r["user_id"] for r in fake_db.invoices.values())
    assert owners == ["user-1", "user-2"]


@pytest.mark.asyncio
async def test_a_racing_duplicate_gets_409_not_500(client, fake_db, fake_agent, monkeypatch):
    """Both requests pass the "already exists?" read; the primary key stops the second insert."""
    import api.index as api_index
    headers = signed_in(fake_db)
    assert (await client.post("/api/invoices", headers=headers, json=body(invoice_id="INV-RACE"))).status_code == 200

    real_get_invoice = api_index.get_invoice
    monkeypatch.setattr(api_index, "get_invoice", lambda invoice_id: None)  # the read raced the other insert
    r = await client.post("/api/invoices", headers=headers, json=body(invoice_id="INV-RACE"))
    monkeypatch.setattr(api_index, "get_invoice", real_get_invoice)

    assert r.status_code == 409, r.text
    assert len(fake_db.invoices) == 1


@pytest.mark.asyncio
async def test_generated_invoice_rejects_non_positive_amounts(client, fake_db, fake_agent):
    headers = signed_in(fake_db)
    r = await client.post("/api/invoices/generated", headers=headers, json={
        "invoice_id": "GEN-1", "client_name": "Acme", "client_email": "ap@acme.example",
        "invoice_amount_cents": -100, "due_date": "2026-10-01", "jurisdiction": "CA",
        "storage_path": "generated/user-1/x.pdf", "file_name": "x.pdf", "file_size": 10,
    })
    assert r.status_code == 422, r.text


@pytest.mark.skipif(not os.path.isdir(_DIST), reason="frontend/dist not built")
@pytest.mark.parametrize("path", ["/api/nope", "/api/invoices/..%2F..%2Fetc%2Fpasswd/history"])
@pytest.mark.asyncio
async def test_unknown_api_paths_are_json_404_not_the_app_shell(client, path):
    r = await client.get(path)
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")
