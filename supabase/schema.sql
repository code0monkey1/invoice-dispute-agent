-- InvoiceChaser Supabase Schema
-- Run once in the Supabase SQL editor (Project > SQL Editor > New query).
-- Safe to re-run: all statements use IF NOT EXISTS / ON CONFLICT DO NOTHING.

CREATE TABLE IF NOT EXISTS users (
    id                   TEXT PRIMARY KEY,
    email                TEXT UNIQUE NOT NULL,
    name                 TEXT,
    picture              TEXT,
    gmail_access_token   TEXT,
    gmail_refresh_token  TEXT,
    gmail_connected_at   TEXT,
    gmail_history_id     TEXT,
    telegram_chat_id     TEXT,
    created_at           TEXT DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS')
);

CREATE TABLE IF NOT EXISTS invoices (
    id                TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL REFERENCES users(id),
    client_name       TEXT NOT NULL,
    client_email      TEXT NOT NULL,
    invoice_amount    REAL NOT NULL,
    days_overdue      INTEGER NOT NULL DEFAULT 0,
    jurisdiction      TEXT,
    escalation_level  INTEGER NOT NULL DEFAULT 0,
    gmail_thread_id   TEXT,
    gmail_message_ids TEXT DEFAULT '[]',
    sender_name       TEXT,
    sender_business   TEXT,
    sender_email      TEXT,
    status            TEXT NOT NULL DEFAULT 'pending',
    created_at        TEXT DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS'),
    updated_at        TEXT DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS')
);

CREATE TABLE IF NOT EXISTS communication_history (
    id          BIGSERIAL PRIMARY KEY,
    invoice_id  TEXT NOT NULL REFERENCES invoices(id),
    type        TEXT NOT NULL,
    subject     TEXT,
    content     TEXT,
    direction   TEXT NOT NULL DEFAULT 'outbound',
    timestamp   TEXT DEFAULT to_char(NOW(), 'YYYY-MM-DD HH24:MI:SS')
);

-- Seed the guest user so unauthenticated invoices have a valid FK target.
INSERT INTO users (id, email, name)
VALUES ('guest', 'guest@invoicechaser', 'Guest')
ON CONFLICT (id) DO NOTHING;
