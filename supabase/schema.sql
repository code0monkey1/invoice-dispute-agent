-- InvoiceChaser Supabase Schema
-- Run once in the Supabase SQL editor (Project > SQL Editor > New query).
-- Safe to re-run: all statements use IF NOT EXISTS / ON CONFLICT DO NOTHING.

CREATE TABLE IF NOT EXISTS users (
    id                    TEXT PRIMARY KEY,
    email                 TEXT UNIQUE,
    name                  TEXT,
    picture               TEXT,
    gmail_access_token    TEXT,
    gmail_refresh_token   TEXT,
    gmail_connected_at    TEXT,
    gmail_history_id      TEXT,
    is_guest              BOOLEAN NOT NULL DEFAULT FALSE,
    created_at            TEXT DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS')
);

-- Migrations for tables that may pre-date the columns above.
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_guest BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ALTER COLUMN email DROP NOT NULL;
-- Legacy Telegram columns are left in place if they already exist; we just
-- stop reading or writing them. They can be dropped manually later if desired.

CREATE TABLE IF NOT EXISTS invoices (
    id                TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL REFERENCES users(id),
    client_name       TEXT NOT NULL,
    client_email      TEXT NOT NULL,
    invoice_amount    REAL NOT NULL,
    amount_paid       REAL NOT NULL DEFAULT 0,
    days_overdue      INTEGER NOT NULL DEFAULT 0,
    jurisdiction      TEXT,
    escalation_level  INTEGER NOT NULL DEFAULT 0,
    gmail_thread_id   TEXT,
    gmail_message_ids TEXT DEFAULT '[]',
    reply_token       TEXT UNIQUE,
    invoice_file_path TEXT,
    invoice_file_name TEXT,
    invoice_file_mime TEXT,
    invoice_file_size INTEGER,
    sender_name       TEXT,
    sender_business   TEXT,
    sender_email      TEXT,
    status            TEXT NOT NULL DEFAULT 'active',
    follow_up_date    TEXT,
    created_at        TEXT DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
    updated_at        TEXT DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS')
);

ALTER TABLE invoices ADD COLUMN IF NOT EXISTS amount_paid REAL NOT NULL DEFAULT 0;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS invoice_file_path TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS invoice_file_name TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS invoice_file_mime TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS invoice_file_size INTEGER;
ALTER TABLE invoices ALTER COLUMN status SET DEFAULT 'active';
-- Reply tracking: approved emails carry Reply-To inv-<reply_token>@<inbound domain>.
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS reply_token TEXT UNIQUE;
-- Promise to pay: set with status "pending" when the user approves mark_invoice_pending.
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS follow_up_date TEXT;

CREATE TABLE IF NOT EXISTS communication_history (
    id          BIGSERIAL PRIMARY KEY,
    invoice_id  TEXT NOT NULL REFERENCES invoices(id),
    user_id     TEXT REFERENCES users(id),
    type        TEXT NOT NULL,
    subject     TEXT,
    content     TEXT,
    direction   TEXT NOT NULL DEFAULT 'outbound',
    timestamp   TEXT DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS')
);

-- Migration: add user_id to communication_history, backfill from invoices, then enforce NOT NULL.
ALTER TABLE communication_history ADD COLUMN IF NOT EXISTS user_id TEXT REFERENCES users(id);
UPDATE communication_history c
   SET user_id = i.user_id
  FROM invoices i
 WHERE c.invoice_id = i.id AND c.user_id IS NULL;
CREATE INDEX IF NOT EXISTS idx_communication_user ON communication_history(user_id);
CREATE INDEX IF NOT EXISTS idx_communication_invoice ON communication_history(invoice_id);
-- A user's invoices, newest first (get_invoices_by_user: every dashboard load and
-- every chat message). Also serves the guest -> account migration's user_id filter.
CREATE INDEX IF NOT EXISTS idx_invoices_user_created ON invoices (user_id, created_at DESC);

-- Legacy 'guest' row preserved for any rows still pointing at it.
-- New unauthenticated visitors get their own guest-<uuid> rows instead (see src/db.py:ensure_guest_user).
INSERT INTO users (id, email, name, is_guest)
VALUES ('guest', NULL, 'Legacy Shared Guest', TRUE)
ON CONFLICT (id) DO NOTHING;

-- Private bucket for original invoice uploads. Server-side service role uploads bypass RLS.
INSERT INTO storage.buckets (id, name, public)
VALUES ('invoice-files', 'invoice-files', false)
ON CONFLICT (id) DO NOTHING;

-- Sender profile (used by the Invoice Generator module).
ALTER TABLE users ADD COLUMN IF NOT EXISTS sender_profile JSONB NOT NULL DEFAULT '{}'::jsonb;

-- ---------------------------------------------------------------------------
-- Agent traces (src/observability/tracer.py). One row per agent run (a chat
-- message, an escalation, a resume after a human decision, a client reply),
-- and one row per step of it: model calls, tool calls, refused tools,
-- interrupts, human decisions, sent emails. Text is redacted before it is
-- written. Times are TIMESTAMPTZ (unlike the TEXT columns above) because
-- retention needs date arithmetic and the trace viewer needs ms ordering.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_runs (
    id              TEXT PRIMARY KEY,
    user_id         TEXT,                     -- owner at the time; access goes through the invoice
    invoice_id      TEXT REFERENCES invoices(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL,            -- chat | escalate | resume | inbound_reply | cli
    status          TEXT NOT NULL,            -- ok | interrupted | error
    prompt_version  TEXT,
    model           TEXT,
    level_start     INTEGER,
    level_end       INTEGER,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    latency_ms      INTEGER,
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    cost_usd        NUMERIC(12, 8),
    step_count      INTEGER,
    error           TEXT
);

CREATE TABLE IF NOT EXISTS agent_trace_steps (
    id            BIGSERIAL PRIMARY KEY,
    run_id        TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    seq           INTEGER NOT NULL,
    type          TEXT NOT NULL,              -- model_call | tool_call | gate_blocked | interrupt | human_decision | email_send
    name          TEXT,
    payload       JSONB NOT NULL DEFAULT '{}'::jsonb,
    latency_ms    INTEGER,
    input_tokens  INTEGER,
    output_tokens INTEGER,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (run_id, seq)
);

-- The trace viewer: an invoice's runs, newest first. The UNIQUE above serves step lookups.
CREATE INDEX IF NOT EXISTS idx_agent_runs_invoice_started ON agent_runs (invoice_id, started_at DESC);
-- Guest -> account migration, and the retention purge.
CREATE INDEX IF NOT EXISTS idx_agent_runs_user ON agent_runs (user_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_started ON agent_runs (started_at);

-- Only the server (service role, which bypasses RLS) reads or writes traces.
-- With RLS on and no policies, the public anon key can't read them via PostgREST.
ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_trace_steps ENABLE ROW LEVEL SECURITY;
-- And not even discoverable (e.g. in the GraphQL schema) to the public or signed-in roles.
REVOKE ALL ON agent_runs, agent_trace_steps FROM anon, authenticated;
REVOKE ALL ON SEQUENCE agent_trace_steps_id_seq FROM anon, authenticated;

-- Keep traces for 30 days. Steps go with their run (ON DELETE CASCADE).
-- Re-running reschedules the same named job.
CREATE EXTENSION IF NOT EXISTS pg_cron;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        PERFORM cron.schedule(
            'purge-agent-traces',
            '15 3 * * *',
            $job$DELETE FROM agent_runs WHERE started_at < NOW() - INTERVAL '30 days'$job$
        );
    END IF;
END $$;
