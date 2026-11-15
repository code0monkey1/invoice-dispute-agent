"""The app factory on its own: no routes from api/index.py, no real agent."""
import pytest
from httpx import ASGITransport, AsyncClient

from src.db import DatabaseUnavailable, InvoiceAlreadyExists
from web.app import Deps, create_app
from web.identity import Identity


def build():
    deps = Deps(agent=object())
    app = create_app(deps, Identity("test-secret", store=lambda: deps.db))

    @app.get("/numbers")
    def numbers():
        return {"total": float("inf"), "rows": [float("nan"), 1.5]}

    @app.get("/down")
    def down():
        raise DatabaseUnavailable("connection reset")

    @app.get("/duplicate")
    def duplicate():
        raise InvoiceAlreadyExists("INV-1")

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret internals")

    @app.get("/traced")
    def traced(request: __import__("fastapi").Request):
        request.state.trace_ids.extend(["run-1", "run-2"])
        return {}

    return app, deps


async def get(app, path, **kwargs):
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path, **kwargs)


def test_the_app_carries_the_deps_it_was_built_with():
    app, deps = build()
    assert app.state.deps is deps


@pytest.mark.asyncio
async def test_numbers_json_cannot_hold_become_null():
    app, _ = build()
    r = await get(app, "/numbers")
    assert r.json() == {"total": None, "rows": [None, 1.5]}


@pytest.mark.asyncio
async def test_a_database_outage_is_a_503_that_says_to_retry():
    app, _ = build()
    r = await get(app, "/down")
    assert r.status_code == 503 and r.headers["retry-after"] == "5"
    assert "connection reset" not in r.text


@pytest.mark.asyncio
async def test_a_duplicate_invoice_is_a_409():
    app, _ = build()
    r = await get(app, "/duplicate")
    assert r.status_code == 409
    assert r.json() == {"detail": "An invoice with this number already exists."}


@pytest.mark.asyncio
async def test_an_unexpected_error_never_leaks_its_message():
    app, _ = build()
    r = await get(app, "/boom")
    assert r.status_code == 500 and "secret internals" not in r.text


@pytest.mark.asyncio
async def test_trace_ids_come_back_in_a_header_browsers_may_read():
    app, _ = build()
    r = await get(app, "/traced", headers={"Origin": "http://localhost:5173"})
    assert r.headers["x-trace-id"] == "run-1,run-2"
    assert r.headers["access-control-expose-headers"] == "X-Trace-Id"
    assert r.headers["access-control-allow-credentials"] == "true"


def test_live_forwards_to_whatever_the_provider_returns_now():
    from types import SimpleNamespace
    from web.app import Live
    holder = SimpleNamespace(db=SimpleNamespace(name="first"))
    view = Live(lambda: holder.db)
    holder.db = SimpleNamespace(name="second")
    assert view.name == "second"
