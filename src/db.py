"""
SQLite database layer for the Invoice Dispute Agent.

Provides schema initialisation, Fernet-encrypted token storage, and query
helpers for users, invoices, and communication history.
"""

import base64
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = _PROJECT_ROOT / "data" / "invoice_agent.db"

# ---------------------------------------------------------------------------
# Token encryption
# ---------------------------------------------------------------------------

def _get_fernet() -> Fernet:
    """Return a Fernet instance whose key is derived from SECRET_KEY."""
    secret = os.environ.get("SECRET_KEY", "default-insecure-secret-key-change-me")
    # Derive a 32-byte key and base64url-encode it as Fernet requires.
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
# Connection helper
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    """
    Open (and if necessary create) the SQLite database.

    - Creates the ``data/`` directory if it does not exist.
    - Enables WAL journal mode for better concurrency.
    - Enforces foreign-key constraints.
    - Returns rows as :class:`sqlite3.Row` objects (dict-like).
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create all tables if they do not already exist."""
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id                   TEXT PRIMARY KEY,
                email                TEXT UNIQUE NOT NULL,
                name                 TEXT,
                picture              TEXT,
                gmail_access_token   TEXT,
                gmail_refresh_token  TEXT,
                gmail_connected_at   TEXT,
                gmail_history_id     TEXT,
                telegram_chat_id     TEXT,
                created_at           TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS invoices (
                id                TEXT PRIMARY KEY,
                user_id           TEXT NOT NULL,
                client_name       TEXT NOT NULL,
                client_email      TEXT NOT NULL,
                invoice_amount    REAL NOT NULL,
                days_overdue      INTEGER NOT NULL DEFAULT 0,
                jurisdiction      TEXT,
                escalation_level  INTEGER NOT NULL DEFAULT 0,
                gmail_thread_id   TEXT,
                gmail_message_ids TEXT DEFAULT '[]',
                status            TEXT NOT NULL DEFAULT 'pending',
                created_at        TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at        TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS communication_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id  TEXT NOT NULL,
                type        TEXT NOT NULL,
                subject     TEXT,
                content     TEXT,
                direction   TEXT NOT NULL DEFAULT 'outbound',
                timestamp   TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id)
            );
            """
        )


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def upsert_user(
    user_id: str,
    email: str,
    name: Optional[str],
    picture: Optional[str],
    access_token: str,
    refresh_token: str,
) -> dict:
    """
    Insert or update a user record.

    Tokens are Fernet-encrypted before storage.  Returns the resulting row
    as a plain ``dict``.
    """
    enc_access = encrypt_token(access_token)
    enc_refresh = encrypt_token(refresh_token)

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO users (id, email, name, picture,
                               gmail_access_token, gmail_refresh_token,
                               gmail_connected_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                email               = excluded.email,
                name                = excluded.name,
                picture             = excluded.picture,
                gmail_access_token  = excluded.gmail_access_token,
                gmail_refresh_token = excluded.gmail_refresh_token,
                gmail_connected_at  = CURRENT_TIMESTAMP
            """,
            (user_id, email, name, picture, enc_access, enc_refresh),
        )

    return get_user(user_id)


def get_user(user_id: str) -> Optional[dict]:
    """Return the user row for *user_id* as a ``dict``, or ``None``."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


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
    """
    Update the stored Gmail tokens for *user_id*.

    If *refresh_token* is ``None`` only the access token is updated.
    """
    enc_access = encrypt_token(access_token)

    with get_db() as conn:
        if refresh_token is not None:
            enc_refresh = encrypt_token(refresh_token)
            conn.execute(
                """
                UPDATE users
                SET gmail_access_token  = ?,
                    gmail_refresh_token = ?,
                    gmail_connected_at  = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (enc_access, enc_refresh, user_id),
            )
        else:
            conn.execute(
                """
                UPDATE users
                SET gmail_access_token = ?,
                    gmail_connected_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (enc_access, user_id),
            )


def update_user_history_id(user_id: str, history_id: str) -> None:
    """Persist the latest Gmail history ID for *user_id*."""
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET gmail_history_id = ? WHERE id = ?",
            (history_id, user_id),
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
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO invoices
                (id, user_id, client_name, client_email, invoice_amount,
                 days_overdue, jurisdiction)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_id,
                user_id,
                client_name,
                client_email,
                invoice_amount,
                days_overdue,
                jurisdiction,
            ),
        )
    return get_invoice(invoice_id)


def get_invoice(invoice_id: str) -> Optional[dict]:
    """Return the invoice row for *invoice_id* as a ``dict``, or ``None``."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM invoices WHERE id = ?", (invoice_id,)
        ).fetchone()
    return dict(row) if row else None


def get_invoices_by_user(user_id: str) -> list[dict]:
    """Return all invoices belonging to *user_id*, newest first."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM invoices WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def update_invoice(invoice_id: str, **kwargs) -> Optional[dict]:
    """
    Update arbitrary columns on an invoice row.

    Always bumps ``updated_at`` to the current timestamp.
    Returns the updated row as a ``dict``, or ``None`` if not found.
    """
    if not kwargs:
        return get_invoice(invoice_id)

    # Always refresh the updated_at timestamp.
    kwargs["updated_at"] = "CURRENT_TIMESTAMP"

    # Build SET clause.  updated_at uses a SQL function, not a bound param.
    set_parts = []
    params = []
    for key, value in kwargs.items():
        if key == "updated_at":
            set_parts.append("updated_at = CURRENT_TIMESTAMP")
        else:
            set_parts.append(f"{key} = ?")
            params.append(value)

    params.append(invoice_id)
    sql = f"UPDATE invoices SET {', '.join(set_parts)} WHERE id = ?"

    with get_db() as conn:
        conn.execute(sql, params)

    return get_invoice(invoice_id)


def get_invoices_by_client_email(client_email: str) -> list[dict]:
    """
    Return all *active* (non-resolved, non-cancelled) invoices for a given
    client email address, newest first.
    """
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM invoices
            WHERE client_email = ?
              AND status NOT IN ('resolved', 'cancelled')
            ORDER BY created_at DESC
            """,
            (client_email,),
        ).fetchall()
    return [dict(r) for r in rows]


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
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO communication_history
                (invoice_id, type, subject, content, direction)
            VALUES (?, ?, ?, ?, ?)
            """,
            (invoice_id, comm_type, subject, content, direction),
        )
        row_id = cursor.lastrowid

    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM communication_history WHERE id = ?", (row_id,)
        ).fetchone()
    return dict(row)


def get_communications(invoice_id: str) -> list[dict]:
    """Return all communication records for *invoice_id*, oldest first."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM communication_history
            WHERE invoice_id = ?
            ORDER BY timestamp ASC
            """,
            (invoice_id,),
        ).fetchall()
    return [dict(r) for r in rows]
