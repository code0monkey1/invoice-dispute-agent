"""
Supabase database layer for the Invoice Dispute Agent.

Provides Fernet-encrypted token storage and query helpers for users,
invoices, and communication history. Tables are pre-created via
supabase/schema.sql — run that once in the Supabase SQL editor.
"""

import base64
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Optional, Sequence

from cryptography.fernet import Fernet
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Supabase client singleton
# ---------------------------------------------------------------------------

_supabase_client: Optional[Client] = None
_INVOICE_ID_SEPARATOR = "__inv__"
_SUPABASE_TIMEOUT_SECONDS = 20


def _create_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
    return create_client(url, key)


def get_supabase() -> Client:
    global _supabase_client

    # In Vercel serverless, reusing the same HTTP client across warm invocations
    # can trigger transient socket errors. A fresh client per call is more stable.
    if os.environ.get("VERCEL"):
        return _create_supabase_client()

    if _supabase_client is None:
        _supabase_client = _create_supabase_client()
    return _supabase_client


def _supabase_rest_url(table: str, query: Optional[Sequence[tuple[str, str]]] = None) -> str:
    base_url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not base_url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in environment")

    url = f"{base_url.rstrip('/')}/rest/v1/{table}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(list(query), doseq=True)}"
    return url


def _supabase_rest_request(
    method: str,
    table: str,
    *,
    query: Optional[Sequence[tuple[str, str]]] = None,
    payload: Optional[dict] = None,
    prefer: Optional[str] = None,
):
    key = os.environ.get("SUPABASE_KEY")
    if not key:
        raise RuntimeError("SUPABASE_KEY must be set in environment")

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer

    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        _supabase_rest_url(table, query),
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=_SUPABASE_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase REST {method} {table} failed: {exc.code} {details}") from exc

    if not raw:
        return None
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Token encryption
# ---------------------------------------------------------------------------

def _get_fernet() -> Fernet:
    """Return a Fernet instance whose key is derived from SECRET_KEY."""
    secret = os.environ.get("SECRET_KEY", "default-insecure-secret-key-change-me")
    key_bytes = hashlib.sha256(secret.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_token(token: str) -> str:
    """Encrypt *token* and return the result as a UTF-8 string."""
    return _get_fernet().encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt an encrypted token string and return the plaintext."""
    return _get_fernet().decrypt(encrypted.encode()).decode()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def init_db() -> None:
    """No-op: Supabase tables are pre-created via supabase/schema.sql."""
    pass


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def build_invoice_storage_id(user_id: str, invoice_id: str) -> str:
    """Create a per-user storage ID while preserving the public invoice number."""
    encoded = base64.urlsafe_b64encode(invoice_id.encode()).decode().rstrip("=")
    return f"{user_id}{_INVOICE_ID_SEPARATOR}{encoded}"


def parse_public_invoice_id(storage_id: str) -> str:
    """Recover the original invoice number from a storage ID when possible."""
    if _INVOICE_ID_SEPARATOR not in storage_id:
        return storage_id

    _, encoded = storage_id.split(_INVOICE_ID_SEPARATOR, 1)
    try:
        padding = "=" * (-len(encoded) % 4)
        return base64.urlsafe_b64decode(f"{encoded}{padding}".encode()).decode()
    except Exception:
        return storage_id


def upsert_user(
    user_id: str,
    email: str,
    name: Optional[str],
    picture: Optional[str],
    access_token: str,
    refresh_token: str,
) -> dict:
    """Insert or update a user record. Tokens are Fernet-encrypted before storage."""
    data = {
        "id": user_id,
        "email": email,
        "name": name,
        "picture": picture,
        "gmail_access_token": encrypt_token(access_token),
        "gmail_refresh_token": encrypt_token(refresh_token),
        "gmail_connected_at": _now(),
    }
    _supabase_rest_request(
        "POST",
        "users",
        query=[("on_conflict", "id")],
        payload=data,
        prefer="resolution=merge-duplicates",
    )
    return get_user(user_id)


def get_user(user_id: str) -> Optional[dict]:
    """Return the user row for *user_id* as a ``dict``, or ``None``."""
    rows = _supabase_rest_request(
        "GET",
        "users",
        query=[("select", "*"), ("id", f"eq.{user_id}")],
    ) or []
    return rows[0] if rows else None


def get_user_by_email(email: str) -> Optional[dict]:
    """Return the user row matching *email* as a ``dict``, or ``None``."""
    rows = _supabase_rest_request(
        "GET",
        "users",
        query=[("select", "*"), ("email", f"eq.{email}")],
    ) or []
    return rows[0] if rows else None


def get_user_gmail_tokens(user_id: str) -> Optional[tuple[str, str]]:
    """
    Return ``(access_token, refresh_token)`` for *user_id* with tokens
    decrypted, or ``None`` if the user does not exist or has no tokens.
    """
    user = get_user(user_id)
    if not user:
        return None
    enc_access = user.get("gmail_access_token")
    enc_refresh = user.get("gmail_refresh_token")
    if not enc_access or not enc_refresh:
        return None
    return decrypt_token(enc_access), decrypt_token(enc_refresh)


def update_user_gmail_tokens(
    user_id: str,
    access_token: str,
    refresh_token: Optional[str] = None,
) -> None:
    """Update the stored Gmail tokens for *user_id*."""
    updates: dict = {
        "gmail_access_token": encrypt_token(access_token),
        "gmail_connected_at": _now(),
    }
    if refresh_token is not None:
        updates["gmail_refresh_token"] = encrypt_token(refresh_token)
    _supabase_rest_request(
        "PATCH",
        "users",
        query=[("id", f"eq.{user_id}")],
        payload=updates,
    )


def update_user_history_id(user_id: str, history_id: str) -> None:
    """Persist the latest Gmail history ID for *user_id*."""
    _supabase_rest_request(
        "PATCH",
        "users",
        query=[("id", f"eq.{user_id}")],
        payload={"gmail_history_id": history_id},
    )


# ---------------------------------------------------------------------------
# Invoice helpers
# ---------------------------------------------------------------------------

def create_invoice(
    invoice_id: str,
    user_id: str,
    client_name: str,
    client_email: str,
    invoice_amount: float,
    days_overdue: int,
    jurisdiction: Optional[str],
) -> dict:
    """Insert a new invoice row and return it as a ``dict``."""
    now = _now()
    data = {
        "id": invoice_id,
        "user_id": user_id,
        "client_name": client_name,
        "client_email": client_email,
        "invoice_amount": invoice_amount,
        "days_overdue": days_overdue,
        "jurisdiction": jurisdiction,
        "created_at": now,
        "updated_at": now,
    }
    _supabase_rest_request("POST", "invoices", payload=data)
    return get_invoice(invoice_id)


def get_invoice(invoice_id: str) -> Optional[dict]:
    """Return the invoice row for *invoice_id* as a ``dict``, or ``None``."""
    rows = _supabase_rest_request(
        "GET",
        "invoices",
        query=[("select", "*"), ("id", f"eq.{invoice_id}")],
    ) or []
    return rows[0] if rows else None


def get_invoices_by_user(user_id: str) -> list[dict]:
    """Return all invoices belonging to *user_id*, newest first."""
    return _supabase_rest_request(
        "GET",
        "invoices",
        query=[("select", "*"), ("user_id", f"eq.{user_id}"), ("order", "created_at.desc")],
    ) or []


def update_invoice(invoice_id: str, **kwargs) -> Optional[dict]:
    """
    Update arbitrary columns on an invoice row.

    Always bumps ``updated_at`` to the current timestamp.
    Returns the updated row as a ``dict``, or ``None`` if not found.
    """
    if not kwargs:
        return get_invoice(invoice_id)

    updates = {k: v for k, v in kwargs.items() if k != "updated_at"}
    updates["updated_at"] = _now()

    _supabase_rest_request(
        "PATCH",
        "invoices",
        query=[("id", f"eq.{invoice_id}")],
        payload=updates,
    )
    return get_invoice(invoice_id)


def get_invoices_by_client_email(client_email: str) -> list[dict]:
    """
    Return all active (non-resolved, non-cancelled) invoices for a given
    client email address, newest first.
    """
    rows = _supabase_rest_request(
        "GET",
        "invoices",
        query=[("select", "*"), ("client_email", f"eq.{client_email}"), ("order", "created_at.desc")],
    ) or []
    return [row for row in rows if row.get("status") not in {"resolved", "cancelled"}]


# ---------------------------------------------------------------------------
# Communication history helpers
# ---------------------------------------------------------------------------

def add_communication(
    invoice_id: str,
    comm_type: str,
    subject: Optional[str],
    content: Optional[str],
    direction: str = "outbound",
) -> dict:
    """
    Append a communication record and return it as a ``dict``.

    *comm_type* is a free-form string (e.g. ``"email"``, ``"telegram"``).
    *direction* is ``"outbound"`` or ``"inbound"``.
    """
    data = {
        "invoice_id": invoice_id,
        "type": comm_type,
        "subject": subject,
        "content": content,
        "direction": direction,
        "timestamp": _now(),
    }
    rows = _supabase_rest_request(
        "POST",
        "communication_history",
        payload=data,
        prefer="return=representation",
    ) or []
    return rows[0]


def get_communications(invoice_id: str) -> list[dict]:
    """Return all communication records for *invoice_id*, oldest first."""
    return _supabase_rest_request(
        "GET",
        "communication_history",
        query=[("select", "*"), ("invoice_id", f"eq.{invoice_id}"), ("order", "timestamp.asc")],
    ) or []
