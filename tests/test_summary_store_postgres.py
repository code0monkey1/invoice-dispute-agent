"""Atomic summary claims/publication in a throwaway local Postgres (opt in)."""
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row

URL = os.getenv("TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not URL, reason="set local TEST_DATABASE_URL")
MARKER = "-- Conversation summaries (generated only when an invoice is opened)."


@pytest.fixture
def conn():
    assert urlsplit(URL).hostname in {"localhost", "127.0.0.1", "::1"}
    with psycopg.connect(URL, autocommit=True, row_factory=dict_row) as c:
        for role in ("anon", "authenticated", "service_role"):
            if not c.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
                c.execute(f'CREATE ROLE "{role}" NOLOGIN' + (' BYPASSRLS' if role == 'service_role' else ''))
        c.execute("CREATE TABLE IF NOT EXISTS invoices (id text PRIMARY KEY)")
        c.execute("CREATE TABLE IF NOT EXISTS communication_history (id bigint, invoice_id text, direction text, timestamp text)")
        sql = Path('supabase/schema.sql').read_text()
        assert MARKER in sql, "summary migration not implemented"
        migration = sql[sql.index(MARKER):]
        c.execute(migration)
        c.execute(migration)  # rerunning migration preserves rows and functions
        c.execute("INSERT INTO invoices(id) VALUES ('summary-test') ON CONFLICT DO NOTHING")
        c.execute("DELETE FROM invoice_conversation_summaries WHERE invoice_id='summary-test'")
        yield c


def claim(c, token=None, version='v1'):
    token = token or uuid4()
    return token, c.execute("SELECT * FROM claim_invoice_summary(%s,%s,%s)", ('summary-test', version, token)).fetchone()


def publish(c, token, version='v1', text='saved summary'):
    return c.execute("SELECT publish_invoice_summary(%s,%s,%s,%s) AS ok", ('summary-test', token, version, text)).fetchone()['ok']


def test_summary_persists_and_unchanged_source_is_reused(conn):
    token, row = claim(conn)
    assert row['summary'] is None
    assert publish(conn, token)
    with psycopg.connect(URL, autocommit=True, row_factory=dict_row) as another:
        row = another.execute("SELECT * FROM invoice_conversation_summaries WHERE invoice_id='summary-test'").fetchone()
        assert row['summary'] == 'saved summary'
        assert row['source_version'] == 'v1' and row['generated_at']
        assert claim(another)[1] is None
    assert conn.execute("SELECT count(*) AS n FROM invoice_conversation_summaries WHERE invoice_id='summary-test'").fetchone()['n'] == 1


def test_overlapping_instances_only_one_claims(conn):
    def attempt(_):
        with psycopg.connect(URL, autocommit=True, row_factory=dict_row) as other:
            return claim(other)[1]
    with ThreadPoolExecutor(max_workers=5) as pool:
        rows = list(pool.map(attempt, range(5)))
    assert sum(r is not None for r in rows) == 1


def test_expired_worker_cannot_publish_after_takeover(conn):
    old, _ = claim(conn)
    conn.execute("UPDATE invoice_conversation_summaries SET lease_until=clock_timestamp()-interval '1 second'")
    new, row = claim(conn, version='v2')
    assert row is not None
    assert publish(conn, new, 'v2', 'new summary')
    assert not publish(conn, old)
    assert conn.execute("SELECT summary FROM invoice_conversation_summaries").fetchone()['summary'] == 'new summary'


def test_expired_worker_cannot_publish_even_without_takeover(conn):
    token, _ = claim(conn)
    conn.execute("UPDATE invoice_conversation_summaries SET lease_until=clock_timestamp()-interval '1 second'")
    assert not publish(conn, token)


def test_failure_preserves_summary_and_progress_is_fenced(conn):
    first, _ = claim(conn)
    assert publish(conn, first)
    second, _ = claim(conn, version='v2')
    assert conn.execute("SELECT progress_invoice_summary(%s,%s,%s,%s::jsonb)", ('summary-test', second, 'v2', '{"next": 2, "text": "partial"}')).fetchone()['progress_invoice_summary']
    assert conn.execute("SELECT release_invoice_summary(%s,%s,%s)", ('summary-test', second, 'timeout')).fetchone()['release_invoice_summary']
    row = conn.execute("SELECT * FROM invoice_conversation_summaries").fetchone()
    assert row['summary'] == 'saved summary' and row['source_version'] == 'v1'
    assert row['status'] == 'failed' and row['progress']['next'] == 2
    assert claim(conn, version='v2')[1] is None  # cooldown
    assert not publish(conn, second, 'v2')


@pytest.mark.parametrize('role', ['anon', 'authenticated'])
def test_public_roles_cannot_read_or_execute(conn, role):
    for table in ['invoice_conversation_summaries']:
        assert not conn.execute("SELECT has_table_privilege(%s,%s,'SELECT') AS ok", (role, table)).fetchone()['ok']
    assert not conn.execute("SELECT has_function_privilege(%s,'claim_invoice_summary(text,text,uuid)','EXECUTE') AS ok", (role,)).fetchone()['ok']
    conn.execute(f'SET ROLE "{role}"')
    try:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT * FROM invoice_conversation_summaries")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            claim(conn)
    finally:
        conn.execute('RESET ROLE')


def test_service_role_can_claim_and_publish(conn):
    conn.execute('SET ROLE service_role')
    try:
        token, row = claim(conn)
        assert row is not None and publish(conn, token)
    finally:
        conn.execute('RESET ROLE')
