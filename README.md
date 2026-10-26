<div align="center">

# InvoiceChaser

### An AI agent that chases unpaid invoices. You approve the emails.

Drop in an overdue invoice. The agent reads it, drafts each reminder, reads the client's replies and suggests when to get firmer, from friendly to formal to legal. Nothing is sent from your Gmail until you approve it.

**Built with LangChain · LangGraph · Groq · FastAPI · React · Supabase · Resend**

[Live app](https://invoice-chaser-chi.vercel.app/) &nbsp;&bull;&nbsp; [How it works](#how-it-works) &nbsp;&bull;&nbsp; [Promise to pay](#promise-to-pay-and-how-invoice-data-is-written) &nbsp;&bull;&nbsp; [Architecture](#architecture) &nbsp;&bull;&nbsp; [Setup](#getting-started) &nbsp;&bull;&nbsp; [Agent design](#how-the-agent-is-built)

</div>

---

## How it works

<p align="center">
  <img src="docs/how-it-works.svg" alt="Animated flow: you add the invoice, the agent reads it and drafts an email, you approve it, it sends from your Gmail, the client replies, the reply comes back through Resend Inbound, the agent reads it and you pick the next step." width="100%">
</p>

You do three things. The agent does the rest:

1. **You add the invoice.** Upload the PDF or DOCX you already sent, or create one with the built-in invoice generator.
2. **You approve each email.** The agent drafts every message. You approve, edit or reject it before anything is sent.
3. **You decide when to get firmer.** The agent reads each client reply and suggests the next step. Escalating from Friendly to Formal to Legal is always your call.

### The full lifecycle, step by step

```mermaid
sequenceDiagram
    autonumber
    actor You
    participant App as InvoiceChaser (React)
    participant API as FastAPI
    participant Agent as LangChain agent
    participant Gmail as Your Gmail (send-only)
    actor Client
    participant Resend as Resend Inbound

    You->>App: Drop in invoice PDF
    App->>API: POST /api/invoices/parse
    API-->>App: Client, email, amount, due date
    You->>App: Confirm details
    App->>API: POST /api/invoices/upload
    API->>Agent: Start thread at Level 1 (Friendly)
    Agent-->>API: Draft polite reminder (paused for approval)
    API-->>App: Draft waiting for you
    Note over App: Dashboard shows it under "Waiting for you"
    You->>App: Approve (or edit / reject)
    App->>API: POST /api/invoices/{id}/resume
    API->>Gmail: Send, with Reply-To: you + inv-token@…resend.app
    Gmail->>Client: Email from your own address
    Client-->>Gmail: Reply lands in your inbox
    Client-->>Resend: Same reply reaches the tracking address
    Resend->>API: POST /api/email/inbound (signed webhook)
    API->>Agent: Store reply on the invoice, analyse it
    Agent-->>App: Summary and a suggested next step
    You->>App: Escalate to Formal (your call)
    App->>API: POST /api/invoices/{id}/escalate
    API->>Agent: Level 2, draft a formal demand
    Agent-->>App: New draft waiting for your approval
```

---

## Features

| Feature | What it does |
|---|---|
| **Invoice PDF parsing** | Reads a PDF or DOCX (up to 10 MB) and fills in the invoice number, client, email, amount, due date and jurisdiction. Uses the LLM, with a pattern-matching fallback. Scanned images aren't supported. |
| **Invoice generator** | Creates an invoice PDF from three templates (Modern, Classic, Minimal) with an optional payment link (Stripe, Lemon Squeezy, PayPal), then hands it straight to the agent. |
| **Three escalation levels** | Friendly, Formal and Legal. Each level unlocks different tools and a different tone of voice. |
| **Approval on every send** | Every email draft, and every payment-status change, pauses for your approval. You can edit the draft before it sends. |
| **Escalation on your terms** | The "Escalate" button raises the level directly and asks the agent for a draft in the new tone. It doesn't depend on the model deciding to escalate. |
| **Sends from your Gmail** | Uses Google's `gmail.send` scope only. InvoiceChaser can send the emails you approve, but it can't read your inbox. |
| **Reply tracking** | Each email carries a unique Reply-To address. Client replies reach your inbox and, through Resend Inbound, the invoice's timeline, where the agent analyses them. |
| **Small-claims research** | At the Legal level, the agent looks up small-claims procedures for the client's jurisdiction (Tavily web search) and can write a court-filing guide. This is information, not legal advice. |
| **Promise to pay** | When a client commits to a date, the agent proposes marking the invoice pending. After you approve, the date is saved on the invoice, shown on the dashboard ("Promised to pay by Nov 15, 2026") and flagged if it passes. [More below](#promise-to-pay-and-how-invoice-data-is-written). |
| **Dashboard** | A "Waiting for you" queue of drafts needing approval, the amount outstanding and collected, and every invoice's current status in plain language. |
| **Demo mode** | Try everything without signing up. Demo data stays in your browser session, and no emails are sent. |

> **Removed for now:** late-fee calculation and Telegram notifications. Neither is offered in the app or advertised on the site.

---

## Promise to pay, and how invoice data is written

<p align="center">
  <img src="docs/promise-to-pay.svg" alt="Animated flow: the client promises to pay by a date, the agent proposes marking the invoice pending, you approve, invoice_service checks the date and saves it, the agent remembers it, the dashboard shows it, a missed date is flagged, and payment settles the invoice. Underneath, the three kinds of change invoice_service refuses." width="100%">
</p>

### Why it was added

"I'll pay on the 15th" is the most common reply to a reminder, and the most important one to remember. Before this change, approving `mark_invoice_pending` returned a confirmation message and **saved nothing**. The promise and its date disappeared, the dashboard never showed them, and the agent didn't know them on the next turn. You'd either chase a client who had already committed, or forget to follow up when the date passed.

Fixing it showed a deeper problem: invoice data was written from several places in `api/index.py`. The escalation level was written in three routes, one of which rewrote it after every approval. Payment changes were reconciled inside `/resume`. Settling lived in its own route. So the fix had two parts:

1. **Promise to pay.** `mark_invoice_pending` now proposes `status: "pending"` and a validated `follow_up_date`. Approving it saves both on the invoice (`invoices.follow_up_date`). The agent sees the promise in its context, and the dashboard shows it.
2. **One writer for invoice data.** Every change to an invoice's status, payments, promised date, escalation level or client details goes through `src/services/invoice_service.py`. Routes call it, and tools never touch the database.

### Approving a promise

```mermaid
sequenceDiagram
    autonumber
    actor Client
    actor You
    participant App as Dashboard / Chat
    participant API as FastAPI /resume
    participant Agent as LangGraph agent
    participant Svc as invoice_service
    participant DB as Supabase invoices

    Client-->>App: "Paying in full on Nov 15" (reply on the timeline)
    You->>App: "Client promised to pay on 2026-11-15"
    App->>API: POST /api/chat
    API->>Agent: invoke
    Agent-->>API: mark_invoice_pending(follow_up_date="2026-11-15"), paused
    API-->>App: Status change to confirm
    Note over DB: Nothing has been saved yet
    You->>App: Approve
    App->>API: POST /api/invoices/{id}/resume
    API->>Agent: Command(resume=approve)
    Agent->>Agent: Tool checks the date, sets status "pending" + follow_up_date in state
    Agent-->>API: Final state
    API->>Svc: apply_approved_outcome(id, state, "mark_invoice_pending")
    Svc->>DB: GET invoice (is it settled?)
    Svc->>DB: PATCH status=pending, follow_up_date WHERE status != paid
    Svc-->>API: Saved invoice as agent state
    API->>Agent: Write back only the fields that differ
    API-->>App: state.status = pending, follow_up_date
    Note over App: "Promised to pay by Nov 15, 2026"<br/>after Nov 15: "Promise missed (Nov 15, 2026)"
```

### What approval is allowed to change

Approving a tool commits only what that tool is allowed to change. Each payment tool has its own allow-list (`COMMITTABLE_BY_TOOL`), and everything else in agent state is ignored:

| Approved tool | May change | Allowed statuses |
|---|---|---|
| `mark_invoice_pending` | `status`, `follow_up_date` | `pending` |
| `record_partial_payment` | `amount_paid`, `status` | `active`, `pending`, `paid` |
| `mark_invoice_paid` | `amount_paid`, `status` | `paid` |
| any email draft | nothing on the invoice | n/a |

```mermaid
sequenceDiagram
    autonumber
    participant API as /resume
    participant Svc as invoice_service
    participant DB as Supabase

    API->>Svc: apply_approved_outcome(id, state, approved_tool)
    Svc->>DB: GET invoice
    alt invoice is settled (status = paid)
        Svc-->>API: unchanged, nothing written
    else approved tool is an email draft
        Svc-->>API: unchanged, even if state says "paid"
    else payment tool
        Svc->>Svc: keep only this tool's fields
        Svc->>Svc: amount finite? clamp to 0..invoice total
        Svc->>Svc: status in this tool's allow-list?
        Svc->>Svc: follow_up_date a real YYYY-MM-DD date?
        Svc->>DB: PATCH changes WHERE status != paid
        Svc-->>API: saved state
    end
```

### A settle that races an approval

The settle button and a late approval can arrive at the same moment. Both writes carry the condition `status != paid`, so the database decides. A settled invoice stays settled.

```mermaid
sequenceDiagram
    participant A as Request A: /settle
    participant B as Request B: /resume (approve pending)
    participant DB as Supabase

    B->>DB: GET invoice: status = active
    A->>DB: PATCH status=paid WHERE status != paid
    DB-->>A: 1 row updated, settled
    B->>DB: PATCH status=pending WHERE status != paid
    DB-->>B: 0 rows updated
    Note over DB: Invoice stays settled.<br/>The promise isn't saved.
```

### Found by trying to break it

The feature was tested adversarially, including through the real LangGraph agent with a scripted model (`tests/test_real_graph_payments.py`). These are the failures that turned up, and what fixes them now:

| Attack | What used to happen | Now |
|---|---|---|
| Approve an email draft while agent state says `status: "paid"` | The invoice was marked paid and chasing stopped | Email approvals commit no invoice changes |
| The model records a payment of `inf` | The tool clamped it to the total and the invoice was marked paid | The tool and the service reject non-finite or non-positive amounts |
| The model puts `inf`/`NaN` in any tool call | Chat and history returned 500 on every load, so that invoice's chat stopped loading | Responses replace `inf`/`NaN` with `null` (`SafeJSONResponse`) |
| An approval lands just after a settle | The invoice could be reopened | Writes carry `status != paid` |
| `PATCH /details` with `a@x.com, evil@y.com` or a 5,000-character name | Saved as is | 422: one address, names up to 200 characters |
| An ungated tool (`update_invoice_details`) resets the level to 1 | The level was written back on the next approval | The level can only go up |

Other accounts, guests, replayed approvals and dates like `"next friday"` were tried too. They're covered in `tests/test_pentest_invoice_writes.py`.

### Why not an open-source CRM?

We considered giving the agent a CRM (contacts, notes, deals) to work through. We decided against it:

- **Licences:** the popular open-source CRMs (Twenty, EspoCRM, SuiteCRM, Frappe CRM) are AGPL-3.0. The serious MIT option, Atomic CRM, has no model for invoices, payments or disputes.
- **Right shape for an agent:** agents do better with a few workflow-shaped tools than with a CRM's generic create/read/update API. `invoice_service` is that layer, built around invoices.
- **How collections tools work:** AR products like Chaser and Upflow treat the accounting ledger (Xero, QuickBooks) as the source of truth and keep only the chasing layer themselves. An accounting connector is the likely next integration, not a CRM.

---

## Architecture

```mermaid
flowchart LR
    subgraph Browser
      UI["React 19 + Vite + Tailwind 4<br/>Landing · Dashboard · Chat · Invoice generator"]
    end

    subgraph Vercel["Vercel (serverless)"]
      API["FastAPI<br/>api/index.py"]
      AG["LangChain agent<br/>tool gating · tone · approvals"]
      API --> AG
    end

    UI -- "/api/*" --> API
    AG -- "LLM (GROQ_MODEL)" --> GROQ["Groq<br/>openai/gpt-oss-120b"]
    AG -- "Legal level" --> TAV["Tavily<br/>web search"]
    AG -- "checkpoints" --> PG[("LangGraph checkpointer<br/>Postgres or in-memory")]
    API -- "users · invoices · replies · files" --> SB[("Supabase<br/>Postgres + Storage")]
    API -- "send-only" --> GM["Gmail API"]
    RS["Resend Inbound<br/>inv-token@…resend.app"] -- "signed webhook" --> API
```

### API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/auth/google/url` | Sign-in link with basic profile access only (no warning screen) |
| `GET /api/auth/gmail/connect-url` | "Connect Gmail" link asking for `gmail.send` only (signed-in users) |
| `POST /api/auth/google/callback` | Exchanges the OAuth code. Saves Gmail access only if `gmail.send` was granted |
| `POST /api/invoices/parse` | Extracts invoice fields from a PDF or DOCX (works for guests too) |
| `POST /api/invoices` · `POST /api/invoices/upload` | Creates an invoice and starts the agent thread |
| `GET /api/invoices` | Lists invoices, including `awaiting_approval` for the dashboard queue |
| `POST /api/chat` | Talks to the agent about one invoice. Clearly off-topic questions are filtered out |
| `POST /api/invoices/{id}/escalate` | Raises the level and asks the agent for a draft in the new tone |
| `POST /api/invoices/{id}/resume` | Approve, edit or reject the waiting draft. Approved emails are sent via Gmail |
| `POST /api/email/inbound` | Resend webhook for client replies (Svix signature verified) |

---

## How the agent is built

### Escalation levels and tool gating

The agent only sees the tools for its current level (`src/middleware/dynamic_tools.py`), and its system prompt changes with the level (`src/middleware/dynamic_prompts.py`, prompts in `src/prompts/v1/`).

| Level | Tone | Tools added |
|---|---|---|
| **0 · Setup** | n/a | `update_invoice_details`, `check_invoice_status`, `draft_invoice_delivery_email` |
| **1 · Friendly** | Warm, assumes good faith | `draft_polite_reminder`, `escalate_dispute`, payment-status tools |
| **2 · Formal** | Firm, businesslike | `draft_formal_demand_letter` |
| **3 · Legal** | Final notice | `draft_final_notice`, `lookup_small_claims_procedures`, `generate_court_filing_guide` |

The day ranges shown on the site (7–30, 30–60, 60+ days late) are guidance for you. They aren't thresholds in the code.

### Human in the loop

`HumanInTheLoopMiddleware` (in `src/agent.py`) pauses the agent whenever it calls one of these tools:

| Pauses for your approval | Runs without approval |
|---|---|
| `draft_invoice_delivery_email`, `draft_polite_reminder`, `draft_formal_demand_letter`, `draft_final_notice` | `check_invoice_status`, `update_invoice_details`, `escalate_dispute` |
| `mark_invoice_pending`, `mark_invoice_paid`, `record_partial_payment` | `lookup_small_claims_procedures`, `generate_court_filing_guide` |

When you approve, `/resume` reads the waiting draft **before** syncing invoice details into the agent. LangGraph's `update_state()` clears a pending interrupt, so reading it afterwards would lose the draft. It then sends the email to the client address saved on the invoice, and reports `email_status`: `sent`, `demo`, `gmail_not_connected` or `failed`.

### State, memory and context

- **Agent state** (`src/state.py`): client, amounts, days overdue, jurisdiction, escalation level and status, persisted per invoice thread (`invoice-{id}`) by the LangGraph checkpointer (Postgres when `DATABASE_URL` is set).
- **Source of truth:** the Supabase `invoices` table, written only through `src/services/invoice_service.py`. Only fields that have changed are written into the agent, so a waiting draft isn't wiped when you open an invoice.
- **Promise to pay:** `status: "pending"` plus `follow_up_date` (YYYY-MM-DD), saved when you approve `mark_invoice_pending` and shown in the agent's context.
- **Indexes:** `invoices (user_id, created_at DESC)` serves "this user's invoices, newest first", which runs on every dashboard load and chat message.
- **Runtime context** (`FreelancerContext`): your name, business and payment terms, injected per request.

---

## Tech stack

| Layer | Technology |
|---|---|
| LLM | Groq, model set by `GROQ_MODEL` (default `openai/gpt-oss-120b`, which supports tool calling) |
| Agent | LangChain (`create_agent`, middleware, tools); LangGraph for checkpoints and `Command` |
| Backend | FastAPI on Vercel serverless (Python) |
| Data | Supabase Postgres + Storage (invoice files) |
| Email | Gmail API (send-only) for sending; Resend Inbound (free plan) for replies |
| Search | Tavily (Legal level only) |
| Frontend | React 19, Vite, Tailwind CSS 4, Vitest |

---

## Project structure

```
api/index.py                  FastAPI routes: auth, invoices, chat, escalate, resume, inbound email
src/
  agent.py                    Agent assembly, approval middleware, checkpointer
  state.py                    Agent state + FreelancerContext
  invoice_parser.py           PDF/DOCX text extraction + LLM field extraction (with fallback)
  db.py                       Supabase REST access, encrypted Gmail tokens, reply-token lookup
  tools/                      drafting, escalation, invoice status, legal research, payment status
  middleware/                 dynamic tools and prompts per escalation level
  prompts/v1/                 System prompts for levels 0–3
  services/
    gmail_service.py          Send-only Gmail client (supports Reply-To)
    resend_inbound.py         Reply tokens, webhook signature check, received-email fetch
    invoice_service.py        The only writer of invoice data: status, payments, promise to pay, level, settling
frontend/src/
  components/                 LandingPage, Dashboard, InvoiceTable, ChatPanel, DraftApproval, invoice-generator/
  contexts/AuthContext.tsx    Sign-in, Connect Gmail, demo mode
  hooks/                      useChat (approve, reject, escalate), useInvoices
supabase/schema.sql           Tables, including invoices.reply_token and invoices.follow_up_date
tests/                        Backend tests (pytest)
docs/how-it-works.svg         The animated flow above
docs/promise-to-pay.svg       The animated promise-to-pay flow
```

---

## Getting started

### Prerequisites

- Python 3.11+ and Node.js 18+
- Free accounts: [Groq](https://console.groq.com), [Tavily](https://app.tavily.com), [Supabase](https://supabase.com), a Google Cloud OAuth client, and [Resend](https://resend.com) (free plan, no card)

### Install

```bash
git clone https://github.com/code0monkey1/invoice-dispute-agent.git
cd invoice-dispute-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && cd ..
cp .env.example .env
```

Fill in `.env`. Every variable is described in `.env.example`.

### Configure the services

1. **Supabase:** run `supabase/schema.sql` in the SQL editor. It's safe to re-run, and it adds `invoices.reply_token`.
2. **Google OAuth:** on the consent screen, request `openid`, `userinfo.email`, `userinfo.profile` and `gmail.send` only. Set the redirect URI to `http://localhost:5173/auth/google/callback` (plus your production URL). Send-only access needs Google's free verification, not the paid security assessment.
3. **Resend Inbound:**
   - Copy your receiving address (`<id>.resend.app`) into `RESEND_INBOUND_DOMAIN`, and create an API key.
   - Add an `email.received` webhook pointing to `https://<your-app>/api/email/inbound`, and put its signing secret in `RESEND_WEBHOOK_SECRET`.
   - Resend can't reach `localhost`, so test replies on a deployed URL or through a tunnel.

### Run locally

```bash
# Terminal 1: backend (the Vite dev server proxies /api to port 8000)
uvicorn api.index:app --reload --port 8000

# Terminal 2: frontend
cd frontend && npm run dev
```

Open http://localhost:5173.

### Tests

```bash
pytest                       # backend (includes adversarial tests and real-graph payment flows)
cd frontend && npm run test  # frontend
```

---

## Deploy to Vercel

`vercel.json` builds the frontend and serves every route through `api/index.py`. In the Vercel project, set the same variables as `.env`, including `GROQ_MODEL`, `RESEND_API_KEY`, `RESEND_INBOUND_DOMAIN` and `RESEND_WEBHOOK_SECRET`. Then point the Resend webhook at `https://<your-app>/api/email/inbound`.

---

## License

MIT
