"""web.identity on its own, plus the ordering it must keep inside routes."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from web.identity import GUEST_COOKIE_NAME, Caller, Identity


class Store:
    """Records every lookup, to prove when they happen."""

    def __init__(self, users=None, invoices=None):
        self.users = users or {}
        self.invoices = invoices or {}
        self.calls = []

    def get_user(self, user_id):
        self.calls.append(("get_user", user_id))
        return self.users.get(user_id)

    def get_invoice(self, invoice_id):
        self.calls.append(("get_invoice", invoice_id))
        return self.invoices.get(invoice_id)

    def ensure_guest_user(self, guest_id):
        self.calls.append(("ensure_guest_user", guest_id))


class Response:
    def __init__(self):
        self.cookies = {}

    def set_cookie(self, key, value, **options):
        self.cookies[key] = (value, options)


def request(cookies=None, host="10.0.0.1", scheme="http"):
    return SimpleNamespace(cookies=cookies or {}, client=SimpleNamespace(host=host),
                           url=SimpleNamespace(scheme=scheme), headers={})


def caller(store, identity=None, authorization=None, cookies=None, response=None):
    identity = identity or Identity("test-secret", store=lambda: store)
    return Caller(identity, request(cookies), response or Response(), authorization)


def test_a_caller_reads_nothing_until_asked():
    store = Store()
    caller(store, authorization="Bearer whatever")
    assert store.calls == []


def test_a_valid_token_names_the_user():
    store = Store(users={"u1": {"id": "u1"}})
    identity = Identity("test-secret", store=lambda: store)
    token = identity.create_jwt("u1", "u1@example.com")
    assert caller(store, identity, f"Bearer {token}").user() == {"id": "u1"}


@pytest.mark.parametrize("authorization", [None, "", "Basic abc", "Bearer not-a-jwt"])
def test_no_usable_token_is_no_user(authorization):
    assert caller(Store(), authorization=authorization).user() is None


def test_a_token_signed_with_another_secret_is_refused():
    store = Store(users={"u1": {"id": "u1"}})
    forged = Identity("other-secret", store=lambda: store).create_jwt("u1", "u1@example.com")
    assert caller(store, authorization=f"Bearer {forged}").user() is None


def test_a_new_guest_gets_a_signed_http_only_cookie():
    store, response = Store(), Response()
    user, guest_id = caller(store, response=response).resolve()
    value, options = response.cookies[GUEST_COOKIE_NAME]
    assert user is None and guest_id.startswith("guest-")
    assert value.startswith(guest_id + ".") and options["httponly"] and options["samesite"] == "lax"
    assert ("ensure_guest_user", guest_id) in store.calls


def test_a_returning_guest_keeps_their_id_without_a_new_cookie():
    store, identity = Store(), Identity("test-secret", store=lambda: Store())
    cookie = identity.sign_guest_id("guest-" + "c" * 32)
    response = Response()
    user, guest_id = Caller(identity, request({GUEST_COOKIE_NAME: cookie}), response, None).resolve()
    assert guest_id == "guest-" + "c" * 32 and response.cookies == {}


def test_an_ownership_check_never_mints_a_guest():
    store = Store(invoices={"inv": {"id": "inv", "user_id": "someone"}})
    response = Response()
    with pytest.raises(HTTPException) as err:
        caller(store, response=response).authorize("inv")
    assert err.value.status_code == 404 and response.cookies == {}
    assert not any(name == "ensure_guest_user" for name, _ in store.calls)


def test_an_id_outside_the_format_never_reaches_the_database():
    store = Store()
    with pytest.raises(HTTPException):
        caller(store).authorize("1' OR '1'='1")
    assert store.calls == []


def test_rate_limits_count_per_user_or_per_address():
    store = Store(users={"u1": {"id": "u1"}})
    identity = Identity("test-secret", store=lambda: store)
    token = identity.create_jwt("u1", "u1@example.com")
    assert caller(store, identity, f"Bearer {token}").rate_key() == "user:u1"
    assert caller(store).rate_key() == "ip:10.0.0.1"


@pytest.mark.asyncio
async def test_rate_limiting_still_comes_before_the_ownership_check(client):
    """Routes resolve the caller lazily, so a limited client is told 429, not 404."""
    from api.index import CHAT_LIMIT_PER_MINUTE, RATE_LIMITS
    RATE_LIMITS["chat:ip:127.0.0.1"] = [__import__("time").time()] * CHAT_LIMIT_PER_MINUTE
    r = await client.post("/api/invoices/INV-NOT-MINE/escalate")
    assert r.status_code == 429
