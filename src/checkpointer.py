"""Where the agent keeps each invoice's conversation (LangGraph checkpoints).

Postgres when DATABASE_URL is set, reachable and set up, so chats and pending
approvals survive restarts and are shared by every server instance. Memory
otherwise, which `checkpointer_status` says, and /api/health reports.

DATABASE_URL is Supabase's transaction pooler (port 6543), logged in as the
dedicated `langgraph_checkpointer` role (supabase/schema.sql). Tables are
created once with `python -m src.checkpoint_setup`, never at import.
"""
from __future__ import annotations

import logging

import psycopg
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT_S = 5   # one connection attempt (startup check and each reconnect)
POOL_WAIT_S = 10        # how long a request waits for a pooled connection
TABLES = ("checkpoints", "checkpoint_blobs", "checkpoint_writes", "checkpoint_migrations")
LATEST_MIGRATION = len(PostgresSaver.MIGRATIONS) - 1
SETUP_HINT = "run python -m src.checkpoint_setup"


def connection_kwargs(url: str) -> dict:
    """Connection settings for PostgresSaver behind Supabase's transaction pooler.

    - autocommit: PostgresSaver never commits, so without it nothing is saved.
    - prepare_threshold=None: the transaction pooler can't keep prepared statements.
    - row_factory=dict_row: what PostgresSaver expects (as in its from_conn_string).
    """
    kwargs = {"autocommit": True, "row_factory": dict_row, "prepare_threshold": None,
              "connect_timeout": CONNECT_TIMEOUT_S}
    if "sslmode" not in conninfo_to_dict(url):
        kwargs["sslmode"] = "require"
    return kwargs


def build_pool(url: str) -> ConnectionPool:
    """check_connection replaces a connection the pooler closed while we were idle;
    min_size=0 keeps nothing open on an idle instance. PostgresSaver uses one
    connection at a time (it holds its own lock), so a small pool is enough."""
    return ConnectionPool(
        url,
        min_size=0,
        max_size=2,
        max_idle=60,
        timeout=POOL_WAIT_S,
        check=ConnectionPool.check_connection,
        kwargs=connection_kwargs(url),
        open=True,
    )


def _connect(url: str, **kwargs):
    return psycopg.connect(url, **kwargs)


def _schema_problem(url: str) -> str | None:
    """None when the tables exist at the installed library's migration version."""
    with _connect(url, **connection_kwargs(url)) as conn:
        try:
            row = conn.execute("SELECT max(v) AS v FROM checkpoint_migrations").fetchone()
        except psycopg.errors.UndefinedTable:
            return f"tables_missing: {SETUP_HINT}"
    version = row["v"] if row else None
    if version is None or version < LATEST_MIGRATION:
        return f"migrations_behind: tables at {version}, library needs {LATEST_MIGRATION}; {SETUP_HINT}"
    return None


def _redacted(error: Exception, url: str) -> str:
    message = str(error)
    secrets = [url]
    try:
        password = conninfo_to_dict(url).get("password")
        if password:
            secrets.append(password)
    except Exception:
        pass
    for secret in secrets:
        message = message.replace(secret, "***")
    return f"{type(error).__name__}: {message}".strip()[:300]


def _memory(reason: str):
    logger.error("Conversation store unavailable, using memory: %s", reason)
    return MemorySaver(), {"store": "memory", "reason": reason}


def make_checkpointer(url: str | None):
    """Return (saver, status). status is {"store": "postgres"|"memory", "reason": str|None}.

    The startup check uses one direct connection, so a bad password or an
    unreachable host is reported as such (not as a pool timeout), and no pool
    is left retrying in the background. It also checks the tables are set up,
    so a missing setup step shows in /api/health instead of failing every chat.
    """
    url = (url or "").strip()
    if not url:
        return MemorySaver(), {"store": "memory", "reason": "not_configured"}
    try:
        problem = _schema_problem(url)
    except Exception as e:
        return _memory(_redacted(e, url))
    if problem:
        return _memory(problem)
    return PostgresSaver(build_pool(url)), {"store": "postgres", "reason": None}
