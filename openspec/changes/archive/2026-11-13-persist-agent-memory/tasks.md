# Tasks

> Implement in the worktree `/Users/chiranjeev/Documents/invoice-dispute-agent-agent-memory` (branch `feat/persistent-agent-memory`). The planning artifacts live in the main checkout's untracked `openspec/`.

## 1. Dependencies

- [x] 1.1 Add `psycopg-pool>=3.2` to `requirements.txt` next to `psycopg[binary]` and verify `pip install -r requirements.txt` succeeds and `python -c "import psycopg_pool"` works.

## 2. Pooled checkpointer with visible fallback (design D1, D2, D5)

- [x] 2.1 Write failing tests in `tests/test_checkpointer.py` for `_make_checkpointer`: (a) no `DATABASE_URL` gives `MemorySaver` with status `{"store": "memory", "reason": "not_configured"}`; (b) a probe that raises gives `MemorySaver` and a reason that contains the error type but not the URL or password; (c) a successful probe gives `PostgresSaver` backed by a `ConnectionPool` whose kwargs include `autocommit=True`, `row_factory=dict_row`, `prepare_threshold=None`. Stub `ConnectionPool` so no network is used. Verify they fail with `pytest tests/test_checkpointer.py`.
- [x] 2.2 Rewrite `_make_checkpointer` in `src/agent.py`: hand `DATABASE_URL` straight to `ConnectionPool` as the conninfo (min_size=0, max_size=4, max_idle=60, `check=ConnectionPool.check_connection`, `sslmode=require`), probe with `SELECT 1` and a 5 s timeout, never call `setup()`, and expose `checkpointer_status`. Drop the `urlparse` manual parsing. Verify `pytest tests/test_checkpointer.py` passes.
- [x] 2.3 Write a failing test, then update `/api/health` in `api/index.py` to return `checkpointer: checkpointer_status`, removing the old `checkpointer_error`/`database_url_set` fields, and `status: "degraded"` when the store is memory and `VERCEL_ENV=production`. Verify with new cases in `tests/test_checkpointer.py` (production+memory → degraded, local+memory → ok, postgres → ok) and that the existing `tests/test_tracing.py` and `tests/test_langsmith.py` health assertions still pass.
- [x] 2.4 Update `.env.example`: transaction pooler on port 6543, the dedicated-role user format `langgraph_checkpointer.<ref>@aws-1-us-east-1.pooler.supabase.com`, a note that prepared statements are disabled in code, a warning not to use the `postgres` user, and a pointer to the setup step. Verify by reading the diff.

## 3. Table setup and lockdown (design D3, D4)

- [x] 3.1 Add `src/checkpoint_setup.py` (`python -m src.checkpoint_setup`). It builds the same pooled saver from `DATABASE_URL`, calls `setup()`, prints the resulting `checkpoint_migrations` version, and exits non-zero if `DATABASE_URL` is unset. Verify with a unit test that the unset case exits non-zero without connecting.
- [x] 3.2 Add to `supabase/schema.sql`: (a) the `langgraph_checkpointer` role exactly as created in prod (design D7). Use a `DO $$ ... IF NOT EXISTS (SELECT 1 FROM pg_roles ...)` block with LOGIN, CONNECTION LIMIT 10, `GRANT USAGE, CREATE ON SCHEMA public`, `GRANT langgraph_checkpointer TO postgres`, and both role timeouts, but **no password**, with a comment pointing to the rotation steps in design D7. (b) A block that, only where the tables exist (guarded `DO $$` on `pg_tables`), enables RLS on `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations` and runs `REVOKE ALL ... FROM anon, authenticated`. Comment it the same way as the trace tables. Verify both blocks are idempotent by running them twice against a local Postgres, before and after setup.
- [x] 3.3 Add an opt-in integration test `tests/test_checkpointer_postgres.py`, skipped unless `TEST_DATABASE_URL` is set. Using a real Postgres it should: run setup; build the agent with a scripted model; run a turn on `invoice-a`; build a **new** saver and agent (a simulated restart) and assert the history is identical; leave an HITL interrupt pending, restart, resume with approve and assert the draft is applied once; and assert a concurrent `invoice-b` doesn't mix in. Verify it passes locally against a throwaway Postgres (for example `docker run postgres:16`) and is skipped in a plain `pytest` run.
- [x] 3.4 Document the setup step and the "re-run on `langgraph-checkpoint-postgres` upgrade" rule in CLAUDE.md (Environment / Deployment) and README deploy notes. Verify the documented command matches 3.1.

## 4. Full-suite check

- [x] 4.1 Run `pytest` (whole backend suite, including eval tier 1) and confirm everything passes with no Postgres configured, i.e. tests still use `MemorySaver`.
- [x] 4.2 Ask for a code review of the branch diff (`/code-review`) and resolve the findings before opening a PR.

## 5. Production rollout (design Migration Plan: code first, credential second)

> Do **not** add `DATABASE_URL` to Vercel before 5.2 is live. With the old code it can hang cold starts (design Context, lock hazard).

- [x] 5.1 Create the dedicated role `langgraph_checkpointer` through the Supabase MCP. Generate the password locally and send only its SCRAM verifier. Check it through the transaction pooler: connection, role timeouts, prepare-free repeated queries, pipeline mode, pool health checks, and no access to `invoices`/`users`/`auth`. Done 2026-11-11. Credential at `~/.config/invoice-chaser/checkpointer.env` (mode 600).
- [x] 5.2 Merge and deploy the code **without** `DATABASE_URL`. Verify prod `/api/health` shows `checkpointer.store == "memory"`, reason `not_configured`, `status == "degraded"`.
- [x] 5.3 Run `set -a; source ~/.config/invoice-chaser/checkpointer.env; set +a; python -m src.checkpoint_setup`, which also locks the tables down. Verify with Supabase `list_tables` (four checkpoint tables, owner `langgraph_checkpointer`) and `get_advisors` security (no findings on them).
- [x] 5.4 Run `sed -n 's/^DATABASE_URL=//p' ~/.config/invoice-chaser/checkpointer.env | vercel env add DATABASE_URL --environment production --sensitive`, then redeploy production. Verify the Vercel env list shows `DATABASE_URL` (production, sensitive) and `/api/health` shows `checkpointer.store == "postgres"`, `status == "ok"`.
- [x] 5.5 Smoke test in prod: chat on an invoice, redeploy, and confirm the history is still there. Leave a draft pending, redeploy, approve it, and confirm exactly one email is sent. Confirm that an anon-key REST request to `/rest/v1/checkpoints` returns no rows. Done 2026-11-13 as a prod guest: history (4 messages) and a pending draft_polite_reminder survived two production redeploys unchanged, and the surviving draft was rejected from the new instance (200, card cleared). Approve + exactly-one-email was not run in prod (guests have no Gmail) and is covered by tests/test_checkpointer_postgres.py::test_a_pending_draft_survives_a_restart_and_is_sent_once.
- [x] 5.6 Update the `vercel-deploy-env-fragility` and `agent-evals-setup` memory notes: the checkpointer is now Postgres in prod.

## Workflow follow-up

- Follow-up change: a pg_cron retention job for checkpoint tables (keep the latest checkpoint per thread).
- Archive the change after the PR is merged and the prod smoke test passes.
