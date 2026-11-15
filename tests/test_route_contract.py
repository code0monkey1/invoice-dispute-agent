"""The HTTP surface, pinned before the restructure.

Routes may move between modules; this list may not change by accident. A
route added or removed on purpose is a one-line edit here.
"""
import pytest
from collections import Counter

SPA_CATCH_ALL = "/{full_path:path}"
FRAMEWORK_PATHS = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}

EXPECTED_ROUTES = {
    ("GET", "/api/health"),
    ("GET", "/api/auth/google/url"),
    ("GET", "/api/auth/gmail/connect-url"),
    ("POST", "/api/auth/google/callback"),
    ("GET", "/api/auth/me"),
    ("GET", "/api/users/me/sender-profile"),
    ("PATCH", "/api/users/me/sender-profile"),
    ("GET", "/api/invoices/{invoice_id}/summary"),
    ("POST", "/api/invoices/{invoice_id}/summary"),
    ("GET", "/api/invoices/{invoice_id}/history"),
    ("PATCH", "/api/invoices/{invoice_id}/details"),
    ("POST", "/api/invoices/parse"),
    ("POST", "/api/invoices/upload"),
    ("POST", "/api/invoices/generated/upload"),
    ("POST", "/api/invoices/generated"),
    ("GET", "/api/invoices"),
    ("POST", "/api/invoices"),
    ("GET", "/api/invoices/{invoice_id}/sender"),
    ("PATCH", "/api/invoices/{invoice_id}/sender"),
    ("POST", "/api/chat"),
    ("POST", "/api/invoices/{invoice_id}/escalate"),
    ("POST", "/api/invoices/{invoice_id}/settle"),
    ("GET", "/api/invoices/{invoice_id}/traces"),
    ("POST", "/api/invoices/{invoice_id}/resume"),
    ("POST", "/api/email/inbound"),
}


def _routes():
    from api.index import app
    return [(method, route.path) for route in app.routes
            for method in sorted(getattr(route, "methods", None) or []) if method not in {"HEAD", "OPTIONS"}]


def test_api_routes_are_exactly_the_pinned_set():
    actual = {r for r in _routes() if r[1] not in FRAMEWORK_PATHS and r[1] != SPA_CATCH_ALL}
    assert actual == EXPECTED_ROUTES


def test_every_pinned_route_is_registered_once():
    counts = Counter(r for r in _routes() if r in EXPECTED_ROUTES)
    assert counts == Counter({route: 1 for route in EXPECTED_ROUTES})


def test_spa_catch_all_cannot_shadow_an_api_route():
    paths = [path for _, path in _routes()]
    if SPA_CATCH_ALL in paths:
        assert paths.index(SPA_CATCH_ALL) == len(paths) - 1


# Every invoice-scoped route answers 404 for an invoice the caller doesn't own,
# so nothing reveals whether someone else's invoice exists.
INVOICE_SCOPED = [
    ("GET", "/api/invoices/INV-NOT-MINE/summary", None),
    ("POST", "/api/invoices/INV-NOT-MINE/summary", {}),
    ("GET", "/api/invoices/INV-NOT-MINE/history", None),
    ("PATCH", "/api/invoices/INV-NOT-MINE/details", {"client_name": "X"}),
    ("GET", "/api/invoices/INV-NOT-MINE/sender", None),
    ("PATCH", "/api/invoices/INV-NOT-MINE/sender", {"business_name": "X"}),
    ("POST", "/api/invoices/INV-NOT-MINE/escalate", None),
    ("POST", "/api/invoices/INV-NOT-MINE/settle", None),
    ("GET", "/api/invoices/INV-NOT-MINE/traces", None),
    ("POST", "/api/invoices/INV-NOT-MINE/resume", {"decision": "approve"}),
    ("POST", "/api/chat", {"thread_id": "invoice-INV-NOT-MINE", "message": "status?"}),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path,body", INVOICE_SCOPED)
async def test_unknown_invoice_is_not_found(client, method, path, body):
    r = await client.request(method, path, json=body)
    assert r.status_code == 404, r.text
