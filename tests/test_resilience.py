"""Outages must produce clear answers, never a bare "Internal Server Error",
and a retry after a failure must never email the client twice.

Found when the database became unreachable mid-session: every request
returned a plain-text 500 with no explanation.
"""
import socket
import urllib.error
from io import BytesIO
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.db import _supabase_rest_request as real_rest_request  # captured before the fake is patched in
from tests.test_approve_sends_email import DRAFT, approve, create_invoice, fake_agent, sent, signed_in  # noqa: F401


@pytest_asyncio.fixture
async def lenient_client(fake_db):
    """Like `client`, but returns the app's 500 response instead of raising."""
    from api.index import app
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
        yield ac


def database_down():
    from src.db import DatabaseUnavailable
    return patch("src.db._supabase_rest_request", side_effect=DatabaseUnavailable("network is unreachable"))


# ─── Database outage ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("method,path,body", [
    ("get", "/api/invoices", None),
    ("post", "/api/invoices", {"invoice_id": "X", "client_name": "A", "client_email": "a@example.com",
                               "invoice_amount": 1, "amount_paid": 0, "days_overdue": 0, "jurisdiction": "Oregon"}),
    ("get", "/api/invoices/{id}/history", None),
    ("post", "/api/invoices/{id}/resume", {"decision": "approve", "message": DRAFT}),
    ("post", "/api/invoices/{id}/settle", None),
    ("post", "/api/invoices/{id}/escalate", None),
    ("post", "/api/chat", {"thread_id": "invoice-{id}", "message": "draft a reminder for this invoice"}),
    ("patch", "/api/invoices/{id}/details", {"client_email": "b@example.com"}),
    ("get", "/api/auth/me", None),
])
async def test_database_outage_gives_a_clear_503(lenient_client, fake_db, method, path, body):
    headers = signed_in(fake_db)
    invoice = await create_invoice(lenient_client, headers)
    path = path.replace("{id}", invoice["id"])
    if body and "thread_id" in body:
        body = {**body, "thread_id": body["thread_id"].replace("{id}", invoice["id"])}

    with database_down():
        kwargs = {"headers": headers}
        if body is not None:
            kwargs["json"] = body
        r = await getattr(lenient_client, method)(path, **kwargs)

    assert r.status_code == 503, (path, r.status_code, r.text)
    assert r.headers["content-type"].startswith("application/json")
    detail = r.json()["detail"]
    assert "try again" in detail.lower()
    assert "unreachable" not in detail and "Traceback" not in r.text


def test_reads_retry_a_network_blip_but_writes_do_not(monkeypatch):
    from src import db
    monkeypatch.setattr(db.time, "sleep", lambda s: None)
    calls = {"n": 0}

    class Ok:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b'[{"id": 1}]'

    def flaky(request, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.URLError(OSError(51, "Network is unreachable"))
        return Ok()

    with patch("urllib.request.urlopen", side_effect=flaky):
        assert real_rest_request("GET", "invoices") == [{"id": 1}]
    assert calls["n"] == 2

    calls["n"] = 0
    with patch("urllib.request.urlopen", side_effect=flaky), pytest.raises(db.DatabaseUnavailable):
        real_rest_request("POST", "communication_history", payload={"a": 1})
    assert calls["n"] == 1  # a write that may have landed is never repeated


@pytest.mark.parametrize("error", [
    urllib.error.URLError(socket.gaierror(8, "nodename nor servname provided")),
    TimeoutError("timed out"),
    ConnectionResetError("reset"),
    urllib.error.HTTPError("http://x", 503, "Service Unavailable", {}, BytesIO(b"<html>cloudflare</html>")),
])
def test_network_and_server_failures_become_database_unavailable(monkeypatch, error):
    from src import db
    monkeypatch.setattr(db.time, "sleep", lambda s: None)
    with patch("urllib.request.urlopen", side_effect=error), pytest.raises(db.DatabaseUnavailable):
        real_rest_request("GET", "invoices")


# ─── Unexpected errors ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unexpected_errors_are_json_without_internals(lenient_client, fake_db, monkeypatch):
    import api.index as api_index
    monkeypatch.setattr(api_index, "get_invoices_by_user", lambda uid: (_ for _ in ()).throw(ValueError("secret column xyz")))
    r = await lenient_client.get("/api/invoices")
    assert r.status_code == 500
    assert r.headers["content-type"].startswith("application/json")
    assert "secret column" not in r.text and "ValueError" not in r.text
    assert "try again" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_ai_outage_is_explained_without_provider_internals(client, fake_db, monkeypatch):
    import api.index as api_index
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    monkeypatch.setattr(api_index, "invoke_agent_with_retry",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("groq: invalid api key gsk_abc123")))
    r = await client.post("/api/chat", headers=headers,
                          json={"thread_id": f"invoice-{invoice['id']}", "message": "draft a reminder for this invoice"})
    assert r.status_code == 503
    assert "gsk_" not in r.text and "groq" not in r.text.lower()
    assert "try again" in r.json()["detail"].lower()


# ─── Never send twice ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_retrying_approve_after_a_failure_does_not_email_twice(client, fake_db, fake_agent, sent):
    """The email goes out, then the AI step fails. The user presses approve again."""
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    fake_agent.ask_for_approval()

    real_invoke = fake_agent.invoke
    fake_agent.invoke = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("AI down"))
    first = await approve(client, invoice, headers)
    assert len(sent) == 1
    # The user is told the email went out, even though the rest didn't finish.
    assert first.status_code == 200, first.text
    assert first.json()["email_sent"] is True

    fake_agent.invoke = real_invoke
    fake_agent.ask_for_approval()  # the draft is still waiting server-side
    second = await approve(client, invoice, headers)

    assert len(sent) == 1, "the client must not get the same email twice"
    assert second.status_code == 200
    assert second.json()["email_status"] == "already_sent"
    assert second.json()["email_sent"] is True
    import api.index as api_index
    outbound = [c for c in api_index.get_communications(invoice["id"]) if c.get("direction") == "outbound"]
    assert len(outbound) == 1


@pytest.mark.asyncio
async def test_a_different_draft_is_still_sent(client, fake_db, fake_agent, sent):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    fake_agent.ask_for_approval()
    await approve(client, invoice, headers)
    fake_agent.ask_for_approval()
    await approve(client, invoice, headers, draft=DRAFT.replace("Could you", "Please could you"))
    assert len(sent) == 2


# ─── Sweep: every route, with the database down or a dependency crashing ─────

def _api_routes():
    from api.index import app
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path.startswith("/api/") or path == "/api/health":
            continue
        for method in sorted(getattr(route, "methods", []) - {"HEAD", "OPTIONS"}):
            yield method, path


LEAKS = ("Traceback", "URLError", "unreachable", "RuntimeError", "supabase", "gsk_", 'File "')


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["database_down", "dependency_crash"])
async def test_no_route_returns_a_bare_500_or_leaks_internals(lenient_client, fake_db, monkeypatch, failure):
    """Pen test: break the backend underneath every API route."""
    import api.index as api_index
    headers = signed_in(fake_db)
    invoice = await create_invoice(lenient_client, headers)
    bad = []

    for method, path in _api_routes():
        url = (path.replace("{invoice_id}", invoice["id"]).replace("{full_path:path}", "x")
                   .replace("{token}", "t"))
        with patch("src.db._supabase_rest_request",
                   side_effect=__import__("src.db", fromlist=["x"]).DatabaseUnavailable("network is unreachable")
                   if failure == "database_down" else RuntimeError("supabase secret detail")):
            with patch.object(api_index, "invoke_agent_with_retry", side_effect=RuntimeError("gsk_live_key leaked")):
                kwargs = {"headers": headers}
                if method in ("POST", "PATCH", "PUT"):
                    kwargs["json"] = {}
                r = await lenient_client.request(method, url, **kwargs)

        is_json = r.headers.get("content-type", "").startswith("application/json")
        if r.status_code >= 500 and not is_json:
            bad.append((method, url, r.status_code, "non-JSON error"))
        if any(leak in r.text for leak in LEAKS):
            bad.append((method, url, r.status_code, "leaks internals: " + r.text[:120]))
        if failure == "database_down" and r.status_code == 500:
            bad.append((method, url, r.status_code, "outage reported as 500, not 503"))

    assert not bad, "\n".join(map(str, bad))


@pytest.mark.parametrize("timeout_error", [TimeoutError("timed out"), urllib.error.URLError(socket.timeout("timed out"))])
def test_a_read_that_timed_out_is_not_retried(monkeypatch, timeout_error):
    """Three 20-second timeouts would blow the 60-second function limit."""
    from src import db
    monkeypatch.setattr(db.time, "sleep", lambda s: None)
    calls = {"n": 0}

    def slow(request, timeout):
        calls["n"] += 1
        raise timeout_error

    with patch("urllib.request.urlopen", side_effect=slow), pytest.raises(db.DatabaseUnavailable):
        real_rest_request("GET", "invoices")
    assert calls["n"] == 1
