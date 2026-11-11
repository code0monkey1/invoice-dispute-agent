"""Every table supabase/schema.sql creates is kept away from Supabase's public API.

Only the backend touches these tables, through the REST API with the service
role key (which bypasses RLS). Supabase gives `anon` and `authenticated` full
privileges on any table `postgres` creates in `public`, so each table needs
both: RLS on (no rows through the public keys) and those privileges revoked
(not even discoverable, e.g. in the GraphQL schema at /graphql/v1).
"""
import re
from pathlib import Path

SCHEMA = (Path(__file__).resolve().parent.parent / "supabase" / "schema.sql").read_text()
# Drop comments so a table named in a comment doesn't count.
SQL = re.sub(r"--[^\n]*", "", SCHEMA)

TABLES = re.findall(r"CREATE TABLE IF NOT EXISTS\s+(\w+)", SQL, re.IGNORECASE)


def _statements(prefix: str) -> list[str]:
    return [s.strip() for s in SQL.split(";") if s.strip().upper().startswith(prefix)]


def test_schema_creates_the_tables_we_expect():
    assert {"users", "invoices", "communication_history", "agent_runs", "agent_trace_steps"} <= set(TABLES)


def test_every_table_has_row_level_security():
    enabled = {m for s in _statements("ALTER TABLE")
               for m in re.findall(r"ALTER TABLE\s+(\w+)\s+ENABLE ROW LEVEL SECURITY", s, re.IGNORECASE)}
    assert set(TABLES) - enabled == set()


def test_every_table_is_revoked_from_the_public_roles():
    revoked = set()
    for s in _statements("REVOKE ALL ON"):
        m = re.match(r"REVOKE ALL ON\s+(?!SEQUENCE)(.+?)\s+FROM\s+(.+)$", s, re.IGNORECASE | re.DOTALL)
        if m and {"anon", "authenticated"} <= {r.strip() for r in m.group(2).split(",")}:
            revoked |= {t.strip() for t in m.group(1).split(",")}
    assert set(TABLES) - revoked == set()


def test_every_serial_sequence_is_revoked_from_the_public_roles():
    serial_tables = re.findall(r"CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\(\s*id\s+BIGSERIAL", SQL, re.IGNORECASE)
    revoked = {seq for s in _statements("REVOKE ALL ON SEQUENCE")
               for seq in re.findall(r"(\w+_id_seq)", s)}
    assert {f"{t}_id_seq" for t in serial_tables} - revoked == set()
