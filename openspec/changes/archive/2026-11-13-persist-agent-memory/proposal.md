# Proposal

## Why

When a Vercel instance is recycled (redeploy, scale-out, idle shutdown), every invoice's agent conversation is lost: chat history disappears from the ChatPanel, and a pending approval card can vanish. Production runs on `InMemorySaver` (`/api/health` reports `"checkpointer": "InMemorySaver"`, `"database_url_set": false`). The existing Postgres path in `src/agent.py` can't work as written either. It opens the connection without `autocommit=True`, so nothing `PostgresSaver` writes is ever committed. A warm instance seems to remember, because a connection sees its own uncommitted writes, but everything is rolled back when the instance is recycled. That's why the Supabase project has no `checkpoint*` tables, even though `DATABASE_URL` was set at one point. The uncommitted DDL also holds catalog locks with no timeout (`idle_in_transaction_session_timeout` is 0), so with today's code a second instance's cold start can hang on `CREATE TABLE IF NOT EXISTS`.

## What Changes

- Store LangGraph checkpoints (each invoice thread `invoice-<id>`) in the existing Supabase Postgres, so conversation history and pending approvals survive instance restarts and are shared across concurrent instances.
- Replace the single connection opened at import with a small, self-healing connection pool, configured for Supabase's **transaction-mode pooler** (port 6543; prepared statements off) as Supabase recommends for serverless.
- Connect as a dedicated least-privilege database role (`langgraph_checkpointer`) that owns only the checkpoint tables, instead of the admin `postgres` user.
- Create the checkpoint tables once, through a schema/migration step rather than on every cold start, and lock them down like the trace tables: RLS on, no policies, and `anon`/`authenticated` privileges revoked, so chat contents never leak through PostgREST.
- Make a fallback to in-memory storage visible: `/api/health` reports when the persistent store is configured but unavailable, or is missing in production, instead of passing silently.
- Document the required `DATABASE_URL` (transaction pooler string) in `.env.example`. Setting it in Vercel production is an operator step.

Out of scope: pruning old checkpoints (deferred; tracked as a follow-up), changing what the agent remembers, and the invoice DB staying the source of truth for invoice facts (`sync_agent_state_from_invoice` is unchanged).

## Capabilities

### New Capabilities
- `agent-conversation-memory`: How an invoice's agent conversation (messages, agent state, pending approvals) is persisted and restored across server instances, how its storage is secured, and how its health is reported.

### Modified Capabilities
<!-- None: no existing specs in openspec/specs/. -->

## Impact

- **Code:** `src/agent.py` (`_make_checkpointer`), `api/index.py` (`/api/health`), a new one-off setup entry point for the checkpoint tables.
- **Dependencies:** add `psycopg-pool` (already installed transitively; pin it explicitly).
- **Database:** the login role `langgraph_checkpointer` (created 2026-11-11) and the four LangGraph tables it will own (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`) in Supabase project `fdsglieendnihbfozbag`, plus the role definition (without password) and RLS/revoke statements in `supabase/schema.sql`.
- **Config/ops:** `DATABASE_URL` is the role's transaction-pooler URL, already created and verified. It's kept outside any repo at `~/.config/invoice-chaser/checkpointer.env` and is added to Vercel production **only after the fixed code is deployed**. `.env.example` guidance moves from session to transaction pooler.
- **Tests:** existing tests build agents with `MemorySaver` and stay unaffected. New unit tests cover checkpointer construction and the health reporting.
- **Latency:** every agent step now does a Postgres round trip through the pooler (us-east-1, same region as the Vercel function `iad1`).
