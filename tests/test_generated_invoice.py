"""Backend tests for the generated-invoice creation and upload endpoints."""
import pytest

VALID_BODY = {
    "invoice_id": "INV-2026-001",
    "client_name": "BigCorp",
    "client_email": "ap@bigcorp.example",
    "invoice_amount_cents": 150000,
    "due_date": "2026-05-15",
    "jurisdiction": "California",
    "file_name": "INV-2026-001.pdf",
    "file_size": 12345,
}


async def _get_user_id(client) -> str:
    """First call mints the ic_guest_session cookie; return the guest_id."""
    await client.get("/api/users/me/sender-profile")
    cookie = next((c for c in client.cookies.jar if c.name == "ic_guest_session"), None)
    assert cookie is not None
    return cookie.value


@pytest.mark.asyncio
async def test_upload_generated_pdf_stores_under_user(client, fake_db):
    """Multipart PDF upload returns a storage_path under generated/<user_id>/."""
    user_id = await _get_user_id(client)
    r = await client.post(
        "/api/invoices/generated/upload",
        files={"file": ("INV-1.pdf", b"%PDF-1.4 fake bytes", "application/pdf")},
        data={"invoice_id": "INV-1"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["storage_path"].startswith(f"generated/{user_id}/")
    assert body["storage_path"].endswith(".pdf")
    assert body["file_size"] == len(b"%PDF-1.4 fake bytes")


@pytest.mark.asyncio
async def test_upload_rejects_non_pdf(client, fake_db):
    await _get_user_id(client)
    r = await client.post(
        "/api/invoices/generated/upload",
        files={"file": ("note.txt", b"hello", "text/plain")},
        data={"invoice_id": "INV-2"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_creates_invoice_row(client, fake_db):
    user_id = await _get_user_id(client)
    payload = {**VALID_BODY, "storage_path": f"generated/{user_id}/abc/INV.pdf"}

    r = await client.post("/api/invoices/generated", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["invoice_id"] == "INV-2026-001"
    assert body["escalation_level"] == 0
    assert body["invoice_file_path"] == payload["storage_path"]
    assert body["invoice_file_mime"] == "application/pdf"


@pytest.mark.asyncio
async def test_rejects_storage_path_for_other_user(client, fake_db):
    await _get_user_id(client)
    payload = {**VALID_BODY, "storage_path": "generated/other-user/INV.pdf"}
    r = await client.post("/api/invoices/generated", json=payload)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_rejects_storage_path_traversal(client, fake_db):
    """`startswith` alone would accept ../ traversal; normpath collapse blocks it."""
    user_id = await _get_user_id(client)
    payload = {
        **VALID_BODY,
        "storage_path": f"generated/{user_id}/../other-user/legit.pdf",
    }
    r = await client.post("/api/invoices/generated", json=payload)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_rejects_duplicate_invoice_id(client, fake_db):
    user_id = await _get_user_id(client)
    payload = {**VALID_BODY, "storage_path": f"generated/{user_id}/abc/INV.pdf"}
    r1 = await client.post("/api/invoices/generated", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/invoices/generated", json=payload)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_rejects_invalid_payload(client, fake_db):
    await _get_user_id(client)
    r = await client.post("/api/invoices/generated", json={"client_name": "X"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_rejects_invalid_due_date(client, fake_db):
    user_id = await _get_user_id(client)
    payload = {
        **VALID_BODY,
        "due_date": "not-a-date",
        "storage_path": f"generated/{user_id}/abc/INV.pdf",
    }
    r = await client.post("/api/invoices/generated", json=payload)
    assert r.status_code == 422
