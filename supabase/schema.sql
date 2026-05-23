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
    invoice_file_path TEXT,
    invoice_file_name TEXT,
    invoice_file_mime TEXT,
    invoice_file_size INTEGER,
    sender_name       TEXT,
    sender_business   TEXT,
    sender_email      TEXT,
    status            TEXT NOT NULL DEFAULT 'active',
    created_at        TEXT DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
    updated_at        TEXT DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS')
);

ALTER TABLE invoices ADD COLUMN IF NOT EXISTS amount_paid REAL NOT NULL DEFAULT 0;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS invoice_file_path TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS invoice_file_name TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS invoice_file_mime TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS invoice_file_size INTEGER;
ALTER TABLE invoices ALTER COLUMN status SET DEFAULT 'active';

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
