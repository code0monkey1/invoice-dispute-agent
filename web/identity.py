"""Who is calling: a signed-in user (JWT) or an anonymous guest (signed cookie).

Identity holds the rules and the signing secret. Caller is one request's view
of them, handed to routes by FastAPI:

    def route(caller: Caller = Depends(get_caller)): ...

Caller does nothing until asked, so every database read and cookie write
happens where the route asks for it, exactly as when routes called the
helpers by hand.
"""
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timezone
from typing import Any, Callable

import jwt
from fastapi import Header, HTTPException, Request, Response

DEFAULT_SECRET_KEY = "dev-secret-key-change-in-production"
GUEST_COOKIE_NAME = "ic_guest_session"
GUEST_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
GUEST_ID_PATTERN = re.compile(r"guest-[0-9a-f]{32}")
INVOICE_ID_PATTERN = re.compile(r"[A-Za-z0-9_.@ -]{1,300}")
TOKEN_LIFETIME_SECONDS = 86400 * 7


def assert_secret_configured(secret: str, env) -> None:
    """Refuse to run in production with the public default key.

    SECRET_KEY signs login tokens and guest sessions; with the default,
    anyone could forge them for any account.
    """
    if env.get("VERCEL") and (not secret or secret == DEFAULT_SECRET_KEY):
        raise RuntimeError("SECRET_KEY must be set to a private value in production.")


def is_secure_request(request: Request) -> bool:
    """Return True when the request is over HTTPS (incl. behind a TLS proxy)."""
    if request.url.scheme == "https":
        return True
    forwarded = request.headers.get("x-forwarded-proto", "")
    return "https" in forwarded.lower()


class Identity:
    """Login tokens, guest cookies and invoice ownership.

    *store* returns the database collaborator (users, guests, invoices). It is
    called on every use, so a test that swaps the database sees its fake here too.
    """

    def __init__(self, secret_key: str, store: Callable[[], Any]):
        self._secret = secret_key
        self._store = store

    def create_jwt(self, user_id: str, email: str) -> str:
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": datetime.now(timezone.utc).timestamp() + TOKEN_LIFETIME_SECONDS,
        }
        return jwt.encode(payload, self._secret, algorithm="HS256")

    def current_user(self, authorization: str | None) -> dict | None:
        if not authorization or not authorization.startswith("Bearer "):
            return None
        token = authorization.removeprefix("Bearer ")
        try:
            payload = jwt.decode(token, self._secret, algorithms=["HS256"])
            return self._store().get_user(payload["user_id"])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None

    def sign_guest_id(self, guest_id: str) -> str:
        """Cookie value for a guest: the ID plus an HMAC, so it can't be forged.

        Guest IDs appear inside invoice IDs (URLs, API responses), so the bare
        ID must never be enough to act as that guest.
        """
        sig = hmac.new(self._secret.encode(), guest_id.encode(), hashlib.sha256).hexdigest()[:32]
        return f"{guest_id}.{sig}"

    def guest_id_from_cookie(self, value: str | None) -> str | None:
        """Return the guest ID from a signed cookie, or None if missing, unsigned or tampered."""
        if not value or "." not in value:
            return None
        guest_id, _, _sig = value.rpartition(".")
        if not GUEST_ID_PATTERN.fullmatch(guest_id):
            return None
        return guest_id if hmac.compare_digest(value, self.sign_guest_id(guest_id)) else None

    def guest_id(self, request: Request, response: Response) -> str:
        """Return the per-session guest_id from the cookie, minting one if absent.

        Each anonymous visitor gets a unique ``guest-<hex>`` ID stored in an
        HTTP-only cookie. Guest IDs are isolated: visitor A never sees visitor B's
        invoices. On Google sign-in, the cookie's guest data is migrated to the
        real user and the cookie is cleared.
        """
        existing = self.guest_id_from_cookie(request.cookies.get(GUEST_COOKIE_NAME))
        if existing:
            return existing

        guest_id = f"guest-{secrets.token_hex(16)}"
        self._store().ensure_guest_user(guest_id)
        response.set_cookie(
            key=GUEST_COOKIE_NAME,
            value=self.sign_guest_id(guest_id),
            max_age=GUEST_COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=is_secure_request(request),
            path="/",
        )
        return guest_id

    def owned_invoice(self, invoice_id: str, caller_id: Callable[[], str | None]) -> dict:
        """Return the invoice row only if the caller owns it; otherwise raise 404.

        404 (not 403) so we don't leak the existence of invoices belonging to others.
        IDs outside our own format never reach the database: SQL-looking text made
        Supabase's firewall return an error page, which surfaced as a 500.
        """
        if not INVOICE_ID_PATTERN.fullmatch(invoice_id or ""):
            raise HTTPException(status_code=404, detail="Invoice not found")
        owner = caller_id()
        invoice = self._store().get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if invoice.get("user_id") != owner:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice


class Caller:
    """One request's caller. Each method does its lookups when called, never before."""

    def __init__(self, identity: Identity, request: Request, response: Response, authorization: str | None):
        self.identity = identity
        self.request = request
        self.response = response
        self.authorization = authorization

    def user(self) -> dict | None:
        return self.identity.current_user(self.authorization)

    def resolve(self) -> tuple[dict | None, str]:
        """Return ``(user_or_none, user_id)``, falling back to a per-session guest_id."""
        user = self.user()
        if user:
            return user, user["id"]
        return None, self.identity.guest_id(self.request, self.response)

    def caller_id(self) -> str | None:
        """The caller's user_id (signed in or guest) WITHOUT minting a new guest cookie.

        Used for read-only ownership checks where we shouldn't be creating identities.
        """
        user = self.user()
        if user:
            return user["id"]
        return self.guest_cookie_id()

    def guest_cookie_id(self) -> str | None:
        return self.identity.guest_id_from_cookie(self.request.cookies.get(GUEST_COOKIE_NAME))

    def authorize(self, invoice_id: str) -> dict:
        return self.identity.owned_invoice(invoice_id, self.caller_id)

    def rate_key(self) -> str:
        """Rate limits count per signed-in user, else per client address."""
        user = self.user()
        if user:
            return f"user:{user['id']}"
        host = self.request.client.host if self.request.client else "unknown"
        return f"ip:{host}"


def get_caller(request: Request, response: Response, authorization: str | None = Header(None)) -> Caller:
    return Caller(request.app.state.identity, request, response, authorization)
