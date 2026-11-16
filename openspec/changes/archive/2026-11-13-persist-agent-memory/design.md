# Design

## Context

See proposal.md (Why). Constraints that shape the approach:

- **Runtime:** FastAPI on Vercel Fluid Compute (Python 3.13, region `iad1`). One instance serves concurrent requests on several threads and stays warm between requests, and instances come and go without notice.
- **Network:** Vercel egress is IPv4-only. The Supabase direct host (`db.<ref>.supabase.co`) is IPv6-only on this plan, so the app must use the shared Supavisor pooler at `aws-1-us-east-1.pooler.supabase.com` (project `fdsglieendnihbfozbag`).
- **Library:** `langgraph-checkpoint-postgres` 3.2.0. `PostgresSaver` needs connections with `autocommit=True` and `row_factory=dict_row` (what its own `from_conn_string` sets). It accepts either a `Connection` or a `ConnectionPool` and serialises use of a single connection with a lock.
- **Current code:** `src/agent.py:_make_checkpointer` opens one bare `psycopg.connect(...)` at import, calls `setup()`, and on any exception falls back to `MemorySaver`. `PostgresSaver` sets `row_factory=dict_row` on its own cursors, so the row format is fine. The defect is the missing `autocommit=True`: psycopg opens an implicit transaction that nothing ever commits. The saver *appears* to work on one warm instance (a connection sees its own uncommitted rows), and everything is rolled back when the instance dies. That's why prod has never had checkpoint tables.
- **Lock hazard in today's code:** that never-committed transaction holds the catalog locks from `CREATE TABLE IF NOT EXISTS`. The project has `idle_in_transaction_session_timeout = 0`, so a second instance running the same DDL blocks indefinitely and its cold start times out. Setting `DATABASE_URL` before this change ships is therefore unsafe (see Migration Plan).
- **Supabase default privileges:** tables created in `public` by `postgres` or `supabase_admin` automatically grant `anon` and `authenticated` full access (`arwdDxtm`). Tables created by any other role don't get those grants.
- **Existing pattern:** the trace tables (`agent_runs`, `agent_trace_steps`) are secured in `supabase/schema.sql` with RLS on, no policies, and `REVOKE ALL ... FROM anon, authenticated`. Retention uses pg_cron.
- **Tests** build the graph with `build_agent(model, MemorySaver())` and never touch Postgres.

## Goals / Non-Goals

**Goals:**
- One checkpointer object per instance, built at import as today, that works under concurrent requests and survives pooler-side connection drops.
- No DDL on the request or cold-start path.
- Fallback state that can be seen and explained from `/api/health`.

**Non-Goals:**
- Async checkpointer / async graph invocation (the routes are sync today).
- Checkpoint pruning or retention (follow-up).
- Moving checkpoints to a separate Postgres schema.

## Decisions

### D1. Transaction-mode pooler (6543) with prepared statements disabled
Connect via Supavisor **transaction mode** and pass `prepare_threshold=None` on every connection.
- *Why:* Supabase's docs recommend transaction mode for serverless clients. Every warm Vercel instance holding a session-mode connection uses one of the project's few pooler slots, and they run out as instances scale out. Transaction mode multiplexes. Prepared statements, the only reason session mode was chosen in July, are not needed. With `prepare_threshold=None`, psycopg never prepares statements.
- *Alternative:* session pooler (5432). It works, but each instance pins a backend connection and hits the free-tier pool limit. Rejected.
- *Alternative:* IPv4 add-on plus direct connection. It costs money and gives the same connection pressure. Rejected.
- *Note:* `setup()` DDL and migrations also run fine in transaction mode under autocommit, so one URL is enough.
- *Verified 2026-11-11* from a local machine with the D7 role: host `aws-1-us-east-1.pooler.supabase.com:6543` works, and so do 12 repeated parameterised queries with `prepare_threshold=None`, psycopg pipeline mode (used by `put`/`put_writes`) and a `ConnectionPool` with `check_connection`. The role's own `statement_timeout`/`idle_in_transaction_session_timeout` take effect through Supavisor.

### D2. A `psycopg_pool.ConnectionPool` instead of a single connection
Build `ConnectionPool(conninfo, min_size=0, max_size=2, open=True, check=ConnectionPool.check_connection, max_idle=60, kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": None, "sslmode": "require"})` and pass it to `PostgresSaver`.
- *Why:* `check_connection` checks a connection before handing it out, so a socket Supavisor closed while the instance idled is replaced rather than failing the request (spec: *Recovery from dropped database connections*). With `min_size=0`, an idle instance holds nothing open. *Correction found during implementation:* `PostgresSaver._cursor` takes its own `self.lock` even when given a pool, so checkpoint reads and writes on one instance still go one at a time. The pool buys self-healing connections, not parallelism. Each call is a few milliseconds, so this is fine.
- *Alternative:* keep one connection and reconnect when `conn.closed` is true. It needs hand-written retry logic, and requests still queue behind one lock. Rejected.
- *Connection info:* pass `DATABASE_URL` straight to the pool as a conninfo string rather than taking it apart with `urlparse`. This keeps percent-encoded passwords intact, which is what the current manual parsing was working around.

### D3. Tables are created by an explicit setup step, not at import
Add a small entry point (`python -m src.checkpoint_setup`) that builds the saver from `DATABASE_URL` and calls `setup()`. The setup command also applies the lockdown (D4) as the tables' owner, and fails if a migration left an INVALID index. A `CREATE INDEX CONCURRENTLY` cut off by the role's 15 s `statement_timeout` would otherwise be skipped forever by `IF NOT EXISTS`, and a session `SET` can't reliably lift the timeout through the transaction pooler. `supabase/schema.sql` repeats the lockdown idempotently.
- *Why:* `setup()` runs `CREATE TABLE IF NOT EXISTS` plus a migrations query on every cold start, which costs time on each cold start and gets run by many instances at once. LangGraph owns the table DDL and its migrations (`checkpoint_migrations`), so we call its `setup()` instead of copying its DDL into `schema.sql`. That copy would drift on library upgrades.
- *Ordering:* `setup()` must run before the `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` block. The schema.sql block guards with `IF EXISTS (SELECT 1 FROM pg_tables ...)`, so re-running `schema.sql` on a fresh project before setup doesn't fail.
- *Library upgrades:* bumping `langgraph-checkpoint-postgres` means re-running the setup entry point. Recorded in the README/CLAUDE.md deploy notes.

### D4. Lock the tables down like the trace tables
`ALTER TABLE checkpoints, checkpoint_blobs, checkpoint_writes, checkpoint_migrations ENABLE ROW LEVEL SECURITY;` with no policies, plus `REVOKE ALL ... FROM anon, authenticated`.
- *Why:* they live in `public`, which PostgREST exposes, and they contain full message text including client email contents. Because the D7 role creates them, they get no default grants to `anon`/`authenticated`, so they're never exposed, not even before this lockdown runs. The lockdown is defence in depth and keeps the security advisor clean. The app connects as the owning role, and owners bypass RLS (no `FORCE`), so the app is unaffected.
- *Who runs it:* `postgres` is a member of the D7 role, so the `schema.sql` block (run as `postgres` through the SQL editor or MCP) can `ALTER` tables the role owns.
- *Verification:* the Supabase security advisor (`get_advisors`) shows no `rls_disabled_in_public` findings for these tables.

### D5. Fail open, but visibly
Keep falling back to `MemorySaver` when `DATABASE_URL` is missing or the first connection check fails. Record a reason in a module-level `checkpointer_status`:

```
{ "store": "postgres" | "memory",
  "reason": null | "not_configured" | "<ErrorType>: <message>" }
```

`/api/health` adds this as `checkpointer` (replacing the bare type name and the separate `checkpointer_error` field) and sets top-level `status` to `"degraded"` when `store == "memory"` and `VERCEL_ENV == "production"`.
- *Why fail-open:* if the database blips at cold start, the app can keep serving with memory that doesn't survive a restart, instead of every route returning 500. The earlier outage was caused by just such an import-time failure, `vercel-deploy-env-fragility`. The failure is now visible from health.
- *Startup check (revised after code review):* one **direct** connection (`connect_timeout=5`), not a pool checkout. A pool would hide a bad password behind `PoolTimeout` and leave a worker retrying. It reads `max(v) FROM checkpoint_migrations` and compares it with the installed library's `len(PostgresSaver.MIGRATIONS)-1`: missing tables → `tables_missing`, older tables → `migrations_behind`. Both fall back to memory with a reason naming the setup command, so a skipped setup step or an unrun library upgrade shows as `degraded` instead of failing every chat. Only after the check passes is the pool built.
- *Health:* `degraded` when the store is memory and either `VERCEL_ENV=production` or the reason isn't `not_configured`, so a configured database that fails is visible in preview too.
- *Secret hygiene:* the recorded reason is built from the exception type and message only. psycopg error messages can include host and user but not the password. Still, before storing, any `DATABASE_URL` substring is stripped from the message, in case one is ever there.
- *Alternative:* fail closed in production, so chat returns 503 without memory. That guarantees durability but turns a DB blip into an outage. Rejected for now. It can be changed later without changing the storage design.

### D6. No change to the thread model or the sync path
Thread ids stay `invoice-<id>`. `sync_agent_state_from_invoice` and `has_pending_interrupt` keep working because they go through `agent.get_state` / `update_state`, which are backend-agnostic. Guest→user migration doesn't need to touch checkpoints: they're keyed by invoice id, not user id.

### D7. A dedicated least-privilege role, not `postgres`
The checkpointer connects as `langgraph_checkpointer` (pooler user `langgraph_checkpointer.fdsglieendnihbfozbag`). The role has `LOGIN` (no per-role connection limit: Supavisor opens server connections up to its own pool size, and a lower role limit would reject them mid-request; found in code review), and `USAGE, CREATE` on schema `public`, and nothing else: it can't read `invoices`, `users`, `communication_history` or the `auth` schema. It also has role-level `statement_timeout = 15s` and `idle_in_transaction_session_timeout = 30s`. `postgres` is granted membership so admin SQL can manage the tables it owns.
- *Why:* Supabase's docs advise against giving the `postgres` password to external services and recommend one role per service. A leaked `DATABASE_URL` then exposes only chat checkpoints rather than the whole database. Tables the role creates don't inherit Supabase's `anon`/`authenticated` default grants (see Context). The role timeouts make the lock hazard described in Context impossible for this connection, whatever the client code does. Using this role also means nobody had to reset the `postgres` password.
- *Credential handling:* the password (40 random alphanumerics) was generated locally. Only its SCRAM-SHA-256 verifier was sent through the Supabase MCP (`CREATE ROLE ... PASSWORD 'SCRAM-SHA-256$...'`). The full URL lives in `~/.config/invoice-chaser/checkpointer.env` (mode 600, outside any repo) and goes into Vercel through stdin, never on a command line or in the transcript.
- *Rotation:* generate a new verifier locally, run `ALTER ROLE langgraph_checkpointer PASSWORD '<verifier>'`, then update the file and the Vercel env var and redeploy.
- *Alternative:* the `postgres` user. It puts an admin credential in Vercel, needs a dashboard password reset (the password isn't stored anywhere), and creates tables that start out writable by anon. Rejected.

## Risks / Trade-offs

- [Every agent step adds Postgres round trips (put + writes), roughly 5–20 ms each from iad1 to us-east-1] → Acceptable next to LLM latency. Watch it in the existing traces (`latency_ms`).
- [Checkpoint tables grow without bound (one row per step plus blobs)] → Fine at current volume. A pg_cron prune that keeps the latest checkpoint per thread is a follow-up.
- [Supabase free project gets paused for inactivity → probe fails → app quietly runs on memory] → Health now reports `degraded`. Restoring the project and redeploying recovers.
- [`DATABASE_URL` reaches prod while the old code is still deployed, e.g. another branch's deploy picks it up → cold starts hang on the lock hazard] → Rollout order: the fixed code ships first and the env var is added afterwards (Migration Plan). The D7 role's 30 s idle-in-transaction timeout caps the damage even if the order slips.
- [Role-level `statement_timeout = 15s` cuts off an unusually slow checkpoint write] → Far above expected latency. If it ever trips it shows as a traced error, and the timeout can be raised with `ALTER ROLE`.
- [Library upgrade adds a checkpoint migration that hasn't been run] → `PostgresSaver` would fail on the new schema at runtime. Mitigation: deploy notes require re-running the setup entry point when that package version changes.
- [Interrupts pending in today's in-memory store are lost at cutover] → Unavoidable, and the first deploy would lose them anyway. Freelancers re-trigger the draft.

## Migration Plan

Order matters because of the lock hazard: **code first, credential second.**

1. ✅ Done 2026-11-11: create the D7 role through the MCP and check it through the transaction pooler. Credential at `~/.config/invoice-chaser/checkpointer.env`.
2. Merge and deploy the code **without** `DATABASE_URL`. It's backward compatible: it behaves as today and `/api/health` reports `degraded`.
3. Create the tables as the role: `set -a; source ~/.config/invoice-chaser/checkpointer.env; set +a; python -m src.checkpoint_setup`. Then apply the lockdown block from `supabase/schema.sql`.
4. Add the env var through stdin: `sed -n 's/^DATABASE_URL=//p' ~/.config/invoice-chaser/checkpointer.env | vercel env add DATABASE_URL --environment production --sensitive`. Then redeploy production. Check `/api/health` → `checkpointer.store == "postgres"`, `status == "ok"`.
5. Smoke test: chat on an invoice, redeploy, reopen, and confirm the history is there. Leave a draft pending, redeploy, approve it, and confirm exactly one email is sent.
6. Run `get_advisors` (security) and confirm there are no findings on the checkpoint tables.

**Rollback:** remove `DATABASE_URL` from Vercel production and redeploy. The app goes back to in-memory memory with no code change. The tables and role can stay in place. To revoke the credential entirely: `ALTER ROLE langgraph_checkpointer NOLOGIN`.
