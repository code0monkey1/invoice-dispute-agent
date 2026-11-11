"""The agent's conversation store: Postgres when configured and reachable, memory otherwise.

No network: ConnectionPool is replaced by a fake that records how it was built.
"""
import psycopg
import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row

import src.checkpointer as cp

URL = "postgresql://langgraph_checkpointer.ref:s3cretPw@aws-1-us-east-1.pooler.supabase.com:6543/postgres"


class FakeProbe:
    """Stands in for the startup connection: answers the migration-version query."""
    def __init__(self, version=None, error=None):
        self.version, self.error, self.calls = version, error, []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if isinstance(self.error, psycopg.OperationalError):
            raise self.error
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, *args):
        if self.error:
            raise self.error
        probe = self

        class Result:
            def fetchone(self):
                return {"v": probe.version}
        return Result()


class FakePool:
    instances = []

    def __init__(self, conninfo, **options):
        self.conninfo, self.options = conninfo, options
        FakePool.instances.append(self)

    @staticmethod
    def check_connection(conn):
        pass


LATEST = len(PostgresSaver.MIGRATIONS) - 1


@pytest.fixture
def fake_pool(monkeypatch):
    FakePool.instances = []
    monkeypatch.setattr(cp, "ConnectionPool", FakePool)
    return FakePool


def probe(monkeypatch, **kw):
    fake = FakeProbe(**kw)
    monkeypatch.setattr(cp, "_connect", fake)
    return fake


@pytest.mark.parametrize("url", [None, "", "   "])
def test_without_a_database_url_memory_is_used_and_says_why(fake_pool, monkeypatch, url):
    fake = probe(monkeypatch, version=LATEST)
    saver, status = cp.make_checkpointer(url)
    assert isinstance(saver, MemorySaver)
    assert status == {"store": "memory", "reason": "not_configured"}
    assert fake.calls == [] and fake_pool.instances == []


def test_an_unreachable_database_falls_back_to_memory_without_leaking_the_secret(fake_pool, monkeypatch):
    probe(monkeypatch, error=psycopg.OperationalError(
        f'connection to "{URL}" failed: password authentication failed (password s3cretPw)'
    ))
    saver, status = cp.make_checkpointer(URL)
    assert isinstance(saver, MemorySaver)
    assert status["store"] == "memory"
    assert status["reason"].startswith("OperationalError")
    assert "password authentication failed" in status["reason"], "the real cause, not a pool timeout"
    assert "s3cretPw" not in status["reason"]
    assert URL not in status["reason"]
    assert fake_pool.instances == [], "no pool (and no retrying worker) for a database we can't reach"


def test_missing_tables_fall_back_to_memory_and_say_how_to_fix_it(fake_pool, monkeypatch):
    probe(monkeypatch, error=psycopg.errors.UndefinedTable('relation "checkpoint_migrations" does not exist'))
    saver, status = cp.make_checkpointer(URL)
    assert isinstance(saver, MemorySaver)
    assert status["reason"].startswith("tables_missing")
    assert "checkpoint_setup" in status["reason"]
    assert fake_pool.instances == []


@pytest.mark.parametrize("version", [None, LATEST - 1])
def test_tables_behind_the_installed_library_fall_back_to_memory(fake_pool, monkeypatch, version):
    probe(monkeypatch, version=version)
    saver, status = cp.make_checkpointer(URL)
    assert isinstance(saver, MemorySaver)
    assert status["reason"].startswith("migrations_behind")
    assert "checkpoint_setup" in status["reason"]


def test_a_ready_database_gives_a_pooled_postgres_saver(fake_pool, monkeypatch):
    fake = probe(monkeypatch, version=LATEST)
    saver, status = cp.make_checkpointer(URL)
    assert isinstance(saver, PostgresSaver)
    assert status == {"store": "postgres", "reason": None}

    probe_url, probe_kwargs = fake.calls[0]
    assert probe_url == URL
    assert probe_kwargs["connect_timeout"] == cp.CONNECT_TIMEOUT_S

    pool = fake_pool.instances[0]
    assert saver.conn is pool
    assert pool.conninfo == URL, "the URL is passed through untouched (percent-encoding intact)"
    assert pool.options["min_size"] == 0
    assert pool.options["timeout"] == cp.POOL_WAIT_S
    assert pool.options["check"] is FakePool.check_connection
    kwargs = pool.options["kwargs"]
    assert kwargs["autocommit"] is True
    assert kwargs["row_factory"] is dict_row
    assert kwargs["prepare_threshold"] is None
    assert kwargs["sslmode"] == "require"


def test_an_explicit_sslmode_in_the_url_is_respected(fake_pool, monkeypatch):
    probe(monkeypatch, version=LATEST)
    cp.make_checkpointer("postgresql://u:p@localhost:5432/postgres?sslmode=disable")
    assert "sslmode" not in fake_pool.instances[0].options["kwargs"]


# --- /api/health -------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("status, vercel_env, expected", [
    ({"store": "memory", "reason": "not_configured"}, "production", "degraded"),
    ({"store": "memory", "reason": "OperationalError: timeout"}, "production", "degraded"),
    ({"store": "memory", "reason": "not_configured"}, None, "ok"),
    ({"store": "memory", "reason": "not_configured"}, "preview", "ok"),
    ({"store": "memory", "reason": "tables_missing: run setup"}, "preview", "degraded"),
    ({"store": "memory", "reason": "OperationalError: refused"}, None, "degraded"),
    ({"store": "postgres", "reason": None}, "production", "ok"),
])
async def test_health_reports_the_conversation_store(client, monkeypatch, status, vercel_env, expected):
    import src.agent as agent_module
    monkeypatch.setattr(agent_module, "checkpointer_status", status)
    if vercel_env:
        monkeypatch.setenv("VERCEL_ENV", vercel_env)
    else:
        monkeypatch.delenv("VERCEL_ENV", raising=False)

    body = (await client.get("/api/health")).json()

    assert body["status"] == expected
    assert body["checkpointer"] == status
    assert "checkpointer_error" not in body and "database_url_set" not in body


# --- python -m src.checkpoint_setup -------------------------------------------

@pytest.mark.parametrize("value", [None, ""])
def test_setup_refuses_to_run_without_a_database_url(fake_pool, monkeypatch, capsys, value):
    import src.checkpoint_setup as setup_cmd
    if value is None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("DATABASE_URL", value)

    assert setup_cmd.main() != 0
    assert "DATABASE_URL" in capsys.readouterr().err
    assert fake_pool.instances == [], "nothing may connect"
