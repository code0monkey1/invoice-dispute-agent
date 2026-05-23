"""Backend tests for the sender profile endpoints (Invoice Generator)."""
import pytest


@pytest.mark.asyncio
async def test_get_sender_profile_empty_for_new_user(client, fake_db):
    r = await client.get("/api/users/me/sender-profile")
    assert r.status_code == 200
    assert r.json() == {}


@pytest.mark.asyncio
async def test_patch_then_get_round_trip(client, fake_db):
    payload = {
        "business_name": "Acme",
        "your_name": "Jane",
        "your_email": "jane@acme.example",
    }
    r = await client.patch("/api/users/me/sender-profile", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["business_name"] == "Acme"
    assert body["your_email"] == "jane@acme.example"

    r2 = await client.get("/api/users/me/sender-profile")
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["business_name"] == "Acme"
    assert body2["your_name"] == "Jane"
    assert body2["your_email"] == "jane@acme.example"


@pytest.mark.asyncio
async def test_patch_rejects_unknown_keys(client, fake_db):
    r = await client.patch("/api/users/me/sender-profile", json={"haxx": "nope"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_patch_rejects_invalid_email(client, fake_db):
    r = await client.patch("/api/users/me/sender-profile", json={"your_email": "not-an-email"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_patch_merges_with_existing(client, fake_db):
    """A PATCH only sets the supplied fields; others persist."""
    await client.patch(
        "/api/users/me/sender-profile",
        json={"business_name": "Acme", "your_name": "Jane"},
    )
    await client.patch("/api/users/me/sender-profile", json={"tax_id": "EU123"})

    r = await client.get("/api/users/me/sender-profile")
    body = r.json()
    assert body["business_name"] == "Acme"
    assert body["your_name"] == "Jane"
    assert body["tax_id"] == "EU123"
