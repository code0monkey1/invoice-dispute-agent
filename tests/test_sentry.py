"""Exercise our capture/privacy boundary with the real SDK and no network."""
import json
import logging

import pytest
import sentry_sdk
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sentry_sdk.transport import Transport

from src.errors import DatabaseUnavailable
from web.app import Deps, create_app


class MemoryTransport(Transport):
    def __init__(self):
        super().__init__()
        self.events = []
        self.telemetry = []

    def capture_envelope(self, envelope):
        for item in envelope.items:
            self.telemetry.append((item.headers.get("type"), item.payload.json))
            if item.headers.get("type") == "event":
                self.events.append(item.payload.json)


@pytest.fixture
def telemetry():
    from src.observability.sentry import initialize_sentry
    previous = sentry_sdk.get_client()
    transport = MemoryTransport()
    initialize_sentry({
        "SENTRY_DSN": "https://public@example.invalid/1",
        "SENTRY_ENVIRONMENT": "test",
        "SENTRY_RELEASE": "invoicechaser@test",
    }, transport=transport)
    yield transport
    sentry_sdk.get_client().close()
    sentry_sdk.get_global_scope().set_client(previous)


@pytest.fixture
def captured(telemetry):
    return telemetry.events


@pytest.mark.asyncio
@pytest.mark.parametrize("kind,status", [("unexpected", 500), ("database", 503), ("http", 503)])
async def test_backend_failures_reach_sentry_without_request_secrets(captured, kind, status):
    app = create_app(Deps(agent=None), object())

    @app.post("/failure")
    def failure():
        if kind == "database":
            raise DatabaseUnavailable("database down")
        if kind == "http":
            raise HTTPException(503, "provider unavailable")
        raise RuntimeError("Sentry test error")

    async with AsyncClient(transport=ASGITransport(app, raise_app_exceptions=False), base_url="http://test") as client:
        response = await client.post("/failure?code=oauth-secret", json={"invoice_amount": 999, "message": "private-body"},
                                     headers={"Authorization": "Bearer token-secret", "Cookie": "session=cookie-secret"})
    assert response.status_code == status
    assert captured
    serialized = json.dumps(captured)
    for secret in ["oauth-secret", "token-secret", "cookie-secret", "private-body", "invoice_amount"]:
        assert secret not in serialized
    assert captured[0]["environment"] == "test"
    assert captured[0]["release"] == "invoicechaser@test"


@pytest.mark.asyncio
async def test_expected_client_errors_are_not_issues(captured):
    app = create_app(Deps(agent=None), object())

    @app.get("/expected")
    def expected():
        raise HTTPException(422, "invalid input")

    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        assert (await client.get("/expected")).status_code == 422
    assert captured == []


def test_caught_error_logs_are_reported_without_log_arguments(captured):
    logging.getLogger("invoicechaser").error("Email delivery failed for %s", "private@example.com")
    assert len(captured) == 1
    assert "Email delivery failed" in json.dumps(captured)
    assert "private@example.com" not in json.dumps(captured)


def test_scrubber_removes_custom_context_and_stack_locals():
    from src.observability.sentry import scrub_event
    event = scrub_event({
        "request": {"url": "https://test/api/invoices/INV-private?code=secret", "headers": {"Authorization": "secret"}, "data": "secret"},
        "user": {"email": "secret@example.com"}, "extra": {"prompt": "secret"},
        "breadcrumbs": {"values": [{"message": "secret"}]},
        "exception": {"values": [{"type": "RuntimeError", "value": "email secret@example.com", "stacktrace": {"frames": [{"filename": "app.py", "vars": {"token": "secret"}}]}}]},
    }, {})
    assert event["request"] == {"url": "https://test/api/invoices/:id"}
    assert "secret" not in json.dumps(event)
    assert event["exception"]["values"][0]["stacktrace"]["frames"][0]["filename"] == "app.py"


def test_provider_exception_payloads_are_not_sent(captured):
    try:
        raise RuntimeError('Supabase request failed: {"details":"(private-user-id, INV-PRIVATE, Client Name, 999.00)"}')
    except RuntimeError:
        logging.getLogger("invoicechaser").exception("Database adapter failed")
    payload = json.dumps(captured)
    assert "RuntimeError" in payload
    for private in ["private-user-id", "INV-PRIVATE", "Client Name", "999.00"]:
        assert private not in payload


@pytest.mark.parametrize("operation", ["read", "refresh"])
def test_summary_fallbacks_still_report_the_caught_failure(captured, operation):
    from types import SimpleNamespace
    from src.services import conversation_summary

    def unavailable(*args):
        raise RuntimeError("private provider response")

    result = getattr(conversation_summary, operation)("invoice", object(), SimpleNamespace(get_invoice_summary=unavailable))
    assert result["summary"] is None
    assert len(captured) == 1
    assert captured[0]["exception"]["values"][0]["type"] == "RuntimeError"
    assert "private provider response" not in json.dumps(captured)


@pytest.mark.asyncio
async def test_app_drains_telemetry_after_error_handler(captured):
    drained = []
    deps = Deps(agent=None)
    # This is the serverless lifecycle boundary: the logger captures before drain.
    deps.flush_telemetry = lambda: drained.append(len(captured))
    app = create_app(deps, object())

    @app.get("/error")
    def error():
        raise RuntimeError("error")

    async with AsyncClient(transport=ASGITransport(app, raise_app_exceptions=False), base_url="http://test") as client:
        assert (await client.get("/error")).status_code == 500
    assert drained == [1]


def test_no_dsn_means_no_initialization():
    from src.observability.sentry import initialize_sentry
    assert initialize_sentry({}) is None
    assert not sentry_sdk.get_client().is_active()


@pytest.mark.asyncio
async def test_trace_and_logs_are_sent_without_business_payloads(telemetry):
    app = create_app(Deps(agent=None), object())

    @app.get("/api/invoices/{invoice_id}")
    def invoice(invoice_id: str):
        logging.getLogger("invoicechaser").warning("Provider failed for %s", invoice_id)
        return {}

    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        assert (await client.get("/api/invoices/private-invoice?code=private-code")).status_code == 200
    sentry_sdk.flush()
    types = {kind for kind, _ in telemetry.telemetry}
    assert "transaction" in types
    assert "log" in types
    payload = json.dumps(telemetry.telemetry)
    assert "private-invoice" not in payload
    assert "private-code" not in payload
    assert "Provider failed for %s" in payload
