"""Use cases built at import must still see collaborators a test swaps on deps later.

Group 2 made fakes reach code wherever it lives by having code read deps at
call time. A use case holding the deps.db of import time would silently use
the real one under a test that swapped it.
"""
import pytest

from tests.fakes import Overrides


@pytest.mark.asyncio
async def test_sender_profile_routes_see_a_database_swapped_after_import(client, monkeypatch):
    import api.index as api_index
    user = {"id": "user-swap", "email": "swap@example.com", "name": "Swap",
            "sender_profile": {"business_name": "Seen Through The Swap"}}
    monkeypatch.setattr(api_index.deps, "db", Overrides(api_index.deps.db, get_user=lambda user_id: user))
    token = api_index.identity.create_jwt("user-swap", "swap@example.com")

    r = await client.get("/api/users/me/sender-profile", headers={"Authorization": f"Bearer {token}"})

    assert r.status_code == 200, r.text
    assert r.json().get("business_name") == "Seen Through The Swap"


def test_gmail_token_reads_see_a_database_swapped_after_import(monkeypatch):
    import api.index as api_index
    tokens = ("fake-access", "fake-refresh")
    monkeypatch.setattr(api_index.deps, "db", Overrides(
        api_index.deps.db, get_user_gmail_tokens=lambda user_id: tokens if user_id == "user-swap" else None,
    ))

    assert api_index.deps.gmail_tokens("user-swap") == tokens
