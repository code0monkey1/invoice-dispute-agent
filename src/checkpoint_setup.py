"""Create or upgrade the agent's conversation tables (LangGraph checkpoints).

Run once per database, and again whenever langgraph-checkpoint-postgres is
upgraded (it may add migrations; until then the app reports
`migrations_behind` and keeps conversations in memory).

    set -a; source ~/.config/invoice-chaser/checkpointer.env; set +a
    python -m src.checkpoint_setup

Connect as the langgraph_checkpointer role so it owns the tables. As their
owner it also locks them away from the public API (RLS on, no anon or
authenticated privileges), the same as the block in supabase/schema.sql.
"""
import os
import sys

from src.checkpointer import TABLES, build_pool


def _lock_down(conn) -> None:
    public_roles = [r["rolname"] for r in conn.execute(
        "SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')").fetchall()]
    for table in TABLES:
        conn.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')
        for role in public_roles:
            conn.execute(f'REVOKE ALL ON public."{table}" FROM "{role}"')


def _invalid_indexes(conn) -> list[str]:
    """A CREATE INDEX CONCURRENTLY cut off (e.g. by the role's statement_timeout)
    leaves an INVALID index that IF NOT EXISTS would then skip forever."""
    rows = conn.execute(
        """SELECT i.indexrelid::regclass::text AS name
             FROM pg_index i JOIN pg_class t ON t.oid = i.indrelid
            WHERE t.relname = ANY(%s) AND NOT i.indisvalid""",
        (list(TABLES),),
    ).fetchall()
    return [r["name"] for r in rows]


def main() -> int:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        print("DATABASE_URL is not set; nothing to set up.", file=sys.stderr)
        return 2

    from langgraph.checkpoint.postgres import PostgresSaver

    pool = build_pool(url)
    try:
        PostgresSaver(pool).setup()
        with pool.connection() as conn:
            _lock_down(conn)
            invalid = _invalid_indexes(conn)
            row = conn.execute(
                "SELECT max(v) AS v, current_user AS role FROM checkpoint_migrations"
            ).fetchone()
        if invalid:
            print(f"Invalid indexes (a migration was interrupted): {', '.join(invalid)}. "
                  "DROP INDEX them and run this again.", file=sys.stderr)
            return 1
        print(f"Checkpoint tables ready and locked down: migration version {row['v']}, "
              f"owner role {row['role']}.")
        return 0
    finally:
        pool.close()


if __name__ == "__main__":
    sys.exit(main())
