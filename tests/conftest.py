"""Pytest fixtures for backend tests.

We patch the Supabase REST layer (`src.db._supabase_rest_request`) so tests
never touch the real database. Each test gets a clean in-memory store of
users, invoices, and storage uploads, isolated via the `fake_db` fixture.

The httpx AsyncClient/ASGITransport hits the FastAPI app directly — no
network sockets — and preserves cookies across requests so the `ic_guest_session`
cookie minted on the first request flows into subsequent ones.
"""
import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

# Required env vars must exist before importing the app.
os.environ.setdefault("GROQ_API_KEY", "test")
os.environ.setdefault("TAVILY_API_KEY", "test")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test")
os.environ.setdefault("GOOGLE_REDIRECT_URI", "http://localhost:5173/auth/google/callback")
# 32-byte base64-url-safe key for Fernet (the encryption layer).
os.environ.setdefault("SECRET_KEY", "Mn1uJrEa0v7P9z8X2Q3R4S5T6U7W8Y9Z0a1B2C3D4E4=")
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_KEY", "test")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


from tests.fakes import FakeDB  # noqa: E402  (shared with the eval harness)


@pytest.fixture
def fake_db():
    """Fresh per-test FakeDB plus patches against the real DB layer."""
    db = FakeDB()

    def fake_request(method, table, query=None, payload=None, prefer=None, **_):
        return db.handle(method, [table], query=query, payload=payload, prefer=prefer)

    def fake_upload(bucket, object_path, content, content_type):
        db.storage[object_path] = content
        return object_path

    def fake_download(bucket, object_path):
        return db.storage[object_path]

    # Import lazily so env vars are set first.
    import src.db as db_module
    with patch.object(db_module, "_supabase_rest_request", side_effect=fake_request), \
         patch.object(db_module, "upload_invoice_file", side_effect=fake_upload), \
         patch.object(db_module, "download_invoice_file", side_effect=fake_download):
        yield db


@pytest_asyncio.fixture
async def client(fake_db):
    """Async HTTPX client hitting the FastAPI app in-process, with fake DB."""
    from api.index import RATE_LIMITS, app
    RATE_LIMITS.clear()  # per-test isolation: the limiter is process-global
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
