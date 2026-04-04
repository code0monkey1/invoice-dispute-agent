# Gmail + Telegram Integration Design

**Date:** 2026-04-04
**Status:** Approved

## Overview

Replace Resend with Gmail API as the single email layer (send + receive). Add real-time push notifications via Google Pub/Sub for incoming emails. Integrate Telegram bot for instant mobile notifications. Agent analyzes incoming replies and suggests next actions with HITL approval.

## Goals

1. **Monitor for client replies** — surface replies in the chat panel
2. **Detect payment emails** — identify payment confirmations from banks/PayPal/Stripe
3. **Replace Resend entirely** — send and receive through Gmail
4. **Notify via Telegram** — real-time mobile alerts for incoming emails and escalation events
5. **Agent-assisted analysis** — AI analyzes replies and suggests next steps (HITL)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        Frontend                          │
│  React + Vite + Tailwind                                │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐    │
│  │Dashboard  │  │ChatPanel │  │/auth/google/callback│    │
│  │+Gmail btn │  │+inbound  │  │(OAuth redirect)     │    │
│  │           │  │ emails   │  │                     │    │
│  └──────────┘  └──────────┘  └────────────────────┘    │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                    FastAPI Backend                        │
│                                                          │
│  Existing:                    New:                        │
│  ├── /api/chat               ├── /api/auth/google/*      │
│  ├── /api/invoices/*         ├── /api/gmail/webhook      │
│  ├── /api/invoices/resume    │                           │
│                                                          │
│  ┌─────────────────────────────────────────────┐        │
│  │              Services                        │        │
│  │  ┌──────────────┐  ┌─────────────────────┐  │        │
│  │  │ GmailService │  │ TelegramService     │  │        │
│  │  │ send/read    │  │ send_notification   │  │        │
│  │  └──────────────┘  └─────────────────────┘  │        │
│  └─────────────────────────────────────────────┘        │
│                                                          │
│  ┌─────────────────────────────────────────────┐        │
│  │           SQLite (data/invoice_agent.db)     │        │
│  │  users │ invoices │ communication_history    │        │
│  └─────────────────────────────────────────────┘        │
│                                                          │
│  ┌─────────────────────────────────────────────┐        │
│  │           LangGraph Agent                    │        │
│  │  Existing tools + mark_pending + mark_paid   │        │
│  │  HITL middleware (unchanged)                  │        │
│  └─────────────────────────────────────────────┘        │
└──────────────────────┬──────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │Gmail API │ │Telegram  │ │Google    │
    │send/read │ │Bot API   │ │Pub/Sub   │
    └──────────┘ └──────────┘ └──────────┘
```

## Section 1: OAuth 2.0 Flow

### Google Cloud Console Setup (manual, one-time)

1. Create Google Cloud project
2. Enable Gmail API + Cloud Pub/Sub API
3. Create OAuth 2.0 credentials (Web Application type)
4. Scopes: `openid`, `email`, `profile`, `gmail.send`, `gmail.readonly`, `gmail.modify`
5. Redirect URI: `http://localhost:5173/auth/google/callback` (dev)

### Authentication Flow

Google OAuth serves as both **app sign-in** and **Gmail access grant** in a single flow:

1. User visits the app → Landing page shows "Sign in with Google" button
2. Frontend redirects to Google consent screen (requests profile + Gmail scopes)
3. Google redirects back with auth code to `/auth/google/callback`
4. Frontend sends code to `POST /api/auth/google/callback`
5. Backend exchanges code for access + refresh tokens
6. Backend fetches user profile (name, email) from Google's userinfo endpoint
7. Creates or updates user record in SQLite `users` table (tokens encrypted with Fernet)
8. Returns a session token (JWT) to the frontend
9. Frontend stores JWT in localStorage, includes it in all API requests
10. Refresh token used to obtain new access tokens as needed

**One flow, two outcomes:** User is authenticated AND Gmail is connected.

### Scopes

- `openid` — user identity
- `email` — user email address
- `profile` — user name
- `gmail.send` — send emails
- `gmail.readonly` — read emails
- `gmail.modify` — mark emails as read

### New Endpoints

- `GET /api/auth/google/url` — returns Google OAuth consent URL
- `POST /api/auth/google/callback` — exchanges auth code for tokens, creates session
- `GET /api/auth/me` — returns current user info (from JWT)
- `POST /api/auth/logout` — clears session

### Frontend Changes

- Landing page: "Sign in with Google" button (replaces current unprotected access)
- `/auth/google/callback` route captures code and sends to backend
- Auth context/provider wraps the app — stores JWT, redirects unauthenticated users to landing
- Dashboard and ChatPanel become truly protected routes (check JWT, not just a local flag)
- User avatar + email shown in header when signed in

## Section 2: GmailService

### File: `src/services/gmail_service.py`

```
GmailService(credentials)
  ├── send_email(to, subject, body, thread_id?) → message_id, gmail_thread_id
  ├── get_replies(client_email, after_timestamp?) → list of emails
  ├── search_emails(query) → list of emails
  ├── get_thread(thread_id) → full email thread
  └── mark_as_read(message_id) → void
```

### Key Decisions

- Store `gmail_thread_id` in invoice state when sending dispute emails — enables tracking exact thread for replies
- `get_replies()` filters by `from:client_email` + stored thread ID — only gets replies to our emails
- Resend fully removed. All sending through Gmail API.

### State Changes (`src/state.py`)

- Add `gmail_thread_id: str` — tracks Gmail conversation thread
- Add `gmail_message_ids: list` — tracks sent message IDs to avoid processing outbound as replies

### Send Flow Migration

- `api/index.py` `send_email()` switches from Resend to `GmailService.send_email()`
- `resend` dependency removed
- Env vars `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_OVERRIDE_TO` removed

## Section 3: SQLite Persistence

### File: `src/db.py`

### Schema

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    gmail_access_token TEXT,       -- Fernet encrypted
    gmail_refresh_token TEXT,      -- Fernet encrypted
    gmail_connected_at TEXT,
    gmail_history_id TEXT,         -- last processed Pub/Sub history ID
    telegram_chat_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE invoices (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    client_name TEXT NOT NULL,
    client_email TEXT NOT NULL,
    invoice_amount REAL NOT NULL,
    days_overdue INTEGER NOT NULL DEFAULT 0,
    jurisdiction TEXT,
    escalation_level INTEGER NOT NULL DEFAULT 0,
    gmail_thread_id TEXT,
    gmail_message_ids TEXT,        -- JSON array
    status TEXT NOT NULL DEFAULT 'pending',  -- pending / paid / disputed
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE communication_history (
    id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    type TEXT NOT NULL,            -- reminder / demand / notice / client_reply / payment_detected
    subject TEXT,
    content TEXT,
    direction TEXT NOT NULL,       -- inbound / outbound
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);
```

### Key Decisions

- SQLite file at `data/invoice_agent.db` (gitignored)
- Replaces in-memory `INVOICES` dict and `SENDER_OVERRIDES` dict
- LangGraph checkpointer remains `InMemorySaver` (agent conversation state separate from business data)
- OAuth tokens encrypted at rest using Fernet symmetric encryption (`SECRET_KEY` env var)
- Simple `get_db()` function, raw SQL with thin wrapper — no ORM
- **Single-user model**: A default user record is created on first run (no login/signup flow). Multi-user can be added later.

### New Dependency

- `cryptography` (for Fernet token encryption)

## Section 4: Gmail Push Notifications (Pub/Sub)

### How It Works

1. After OAuth, backend calls `gmail.users().watch()` to register for push notifications
2. Gmail sends notification to Pub/Sub topic when new email arrives
3. Pub/Sub forwards to backend webhook
4. Backend fetches actual email content via Gmail API and processes it

### Google Cloud Setup (completed)

- Pub/Sub topic: `projects/{project-id}/topics/gmail-notifications`
- Push subscription: endpoint `https://nebulose-eduardo-sphagnous.ngrok-free.dev/api/gmail/webhook`
- `gmail-api-push@system.gserviceaccount.com` granted Pub/Sub Publisher role

### New Endpoint: `POST /api/gmail/webhook`

```
Pub/Sub notification arrives
  ↓
Decode: extract user email + history_id
  ↓
Fetch new messages since last history_id (gmail.users().history().list())
  ↓
Filter: only messages FROM client emails that match active invoices
  ↓
For each matching reply:
  ├── Save to communication_history (direction: inbound)
  ├── Feed to agent: "Client replied: {content}"
  ├── Agent analyzes and suggests next steps (HITL — waits for approval)
  └── Send Telegram notification
```

### Watch Renewal

- Gmail watch expires every 7 days
- Renewed on app startup + daily timer

### Local Development

- ngrok static domain: `nebulose-eduardo-sphagnous.ngrok-free.dev`
- Run: `ngrok http 8000 --url=nebulose-eduardo-sphagnous.ngrok-free.dev`

## Section 5: Telegram Notifications

### File: `src/services/telegram_service.py`

```
TelegramService(bot_token, chat_id)
  └── send_notification(message) → bool
```

Simple HTTP POST to `https://api.telegram.org/bot{token}/sendMessage`.

### Bot Details

- Bot: @freelance_invoices_bot
- Bot token: stored in `TELEGRAM_BOT_TOKEN` env var
- Chat ID: stored in `TELEGRAM_CHAT_ID` env var

### Notification Triggers

- Client replies to a dispute email → "📩 Client [name] replied to Invoice #[id]: [first 100 chars]"
- Payment email detected → "💰 Payment notification detected for Invoice #[id]"
- Escalation level changes → "⚠️ Invoice #[id] escalated to Level [n]"

## Section 6: Agent Integration — Incoming Email Processing

### Processing Flow

```
Gmail push notification
  ↓
GmailService.get_new_messages(since=last_history_id)
  ↓
For each new inbound email:
  ├── Match to invoice (by gmail_thread_id or client_email)
  ├── Save to communication_history (direction: inbound)
  ├── Classify:
  │     ├── client_reply → feed to agent for analysis
  │     └── payment_notification → feed to agent for detection
  ├── Agent analyzes and suggests next steps (HITL)
  └── TelegramService.send_notification()
```

### New Agent Tools

- `mark_invoice_pending(invoice_id, follow_up_date)` — client promised payment
- `mark_invoice_paid(invoice_id)` — payment confirmed

Both require HITL approval.

### Prompt Additions (all escalation levels)

```
## Analyzing Client Replies
When a client reply is received, analyze the tone and content:
- If they agree to pay → suggest mark_invoice_pending with a follow-up date
- If they dispute the amount → summarize their objection, suggest response options
- If they ignore/deflect → suggest escalation
- If payment confirmed → suggest mark_invoice_paid
Always explain your reasoning before suggesting an action.
```

### Frontend Changes

- Inbound emails appear as distinct message type (different styling, labeled "Client Reply" or "Payment Notification")
- Agent analysis follows as next message with action suggestions
- HITL approval card for suggested actions (same pattern as draft approval)

## Files to Create

| File | Purpose |
|------|---------|
| `src/services/gmail_service.py` | Gmail API wrapper (send, read, search, watch) |
| `src/services/telegram_service.py` | Telegram bot notification sender |
| `src/db.py` | SQLite database setup + query helpers |
| `src/tools/payment_tools.py` | mark_invoice_pending, mark_invoice_paid |
| `frontend/src/pages/GoogleCallback.tsx` | OAuth redirect handler |

## Files to Modify

| File | Change |
|------|--------|
| `api/index.py` | New auth/webhook endpoints, replace Resend with Gmail, use SQLite |
| `src/agent.py` | Register payment tools |
| `src/state.py` | Add gmail_thread_id, gmail_message_ids |
| `src/middleware/dynamic_tools.py` | Gate payment tools by escalation level |
| `src/prompts/v1/*.txt` | Add reply analysis instructions |
| `frontend/src/App.tsx` | Add /auth/google/callback route |
| `frontend/src/pages/Dashboard.tsx` | Gmail connect button + status |
| `frontend/src/pages/ChatPanel.tsx` | Inbound email display |
| `frontend/src/api.ts` | New API calls (auth, gmail status) |
| `requirements.txt` | Add google-auth, google-api-python-client, cryptography; remove resend |
| `.env.example` | Update env vars |

## Dependencies

### Add
- `google-auth`
- `google-auth-oauthlib`
- `google-api-python-client`
- `cryptography`
- `PyJWT` (for session tokens)

### Remove
- `resend`

## Environment Variables

```
# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:5173/auth/google/callback
GOOGLE_PUBSUB_TOPIC=projects/{project-id}/topics/gmail-notifications

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Security
SECRET_KEY=  # 32-byte key for Fernet encryption of OAuth tokens

# Existing (unchanged)
GROQ_API_KEY=
TAVILY_API_KEY=
```

## Infrastructure

| Service | Tier | Cost |
|---------|------|------|
| Gmail API | Free (user-authenticated) | $0 |
| Google Pub/Sub | Free tier (10GB/month) | $0 |
| Google OAuth | Free | $0 |
| Telegram Bot API | Free | $0 |
| ngrok (dev only) | Free static domain | $0 |
| SQLite | Built-in Python | $0 |
