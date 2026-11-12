# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

InvoiceChaser — a multi-tenant, AI-powered invoice dispute agent for freelancers. Uses LangGraph to orchestrate a multi-level escalation system (Friendly → Formal → Legal) with human-in-the-loop approval before sending emails. Full-stack: FastAPI backend (Vercel serverless), React frontend, Supabase (Postgres) database. Each freelancer connects their own Gmail and Telegram chat — data is isolated per `user_id`.

## Commands

### Backend
```bash
uvicorn api.index:app --reload --host 0.0.0.0 --port 8000   # Dev server
python main.py                                                 # CLI mode (interactive HITL testing)
```

### Frontend
```bash
cd frontend && npm run dev       # Vite dev server (port 5173)
cd frontend && npm run build     # Production build (tsc + vite)
cd frontend && npm run lint      # ESLint
```

### Deployment
Vercel serverless — `vercel.json` routes frontend to `frontend/dist`, backend to `api/index.py` (60s timeout).

Conversation store: `DATABASE_URL` is Supabase's transaction pooler (6543), logged in as the `langgraph_checkpointer` role (never `postgres`). Create its tables with `python -m src.checkpoint_setup`, which also locks them down. Re-run it after upgrading `langgraph-checkpoint-postgres`: until then startup reports `migrations_behind` and falls back to memory. Ship code that reads `DATABASE_URL` before adding the variable to Vercel. `/api/health` → `checkpointer` shows which store is live; `status: "degraded"` means production is on memory, or a configured database failed.

## Architecture

### Agent Core (`src/`)
- **`agent.py`** — LangGraph state machine. Its checkpointer comes from `checkpointer.py`: a pooled `PostgresSaver` when `DATABASE_URL` works, `MemorySaver` otherwise (`checkpointer_status` says which and why). Middleware dynamically filters available tools and system prompts based on escalation level.
- **`state.py`** — `FreelancerContext` and `AgentState` dataclasses defining agent state shape.
- **`prompts.py`** — Prompt loading utilities.
- **`middleware/`** — Three middleware layers:
  - `dynamic_tools.py` — Gates tools by escalation level (LEVEL_0/1/2/3_TOOLS: each level's own email only)
  - `dynamic_prompts.py` — Shifts system prompt tone per escalation level
  - HITL middleware for draft approval interrupts
- **`tools/`** — Tool definitions organized by function: `drafting.py` (email templates), `escalation.py` (level progression), `invoice.py` (status/fees), `legal.py` (Tavily web search), `payment_tools.py` (mark paid/pending)
- **`services/`** — `escalation_policy.py` (pure ladder rules: which email each level may send, one-step moves), `invoice_service.py` (the only writer of invoice facts: status, payments, promise-to-pay `follow_up_date`, escalation level via `escalate`/`start_ladder`, settling; routes call it, tools never touch the DB), `gmail_service.py` (send/read/watch via Gmail API), `resend_inbound.py` (client replies matched by per-invoice `reply_token`)
- **Data flow for agent changes:** payment/status tools are HITL-gated and only propose changes in agent state. On approve, `/resume` passes the agent's response to `invoice_service.apply_approved_outcome`, which validates and commits it. `sync_agent_state_from_invoice` then refreshes the checkpoint from the DB, which is the source of truth.
- **`observability/tracer.py`** — Per-step tracing. `trace_run()` opens a run (chat, escalate, resume, inbound_reply, cli) and steps are recorded by `middleware/tracing.py` (model and tool calls), `enforce_tool_gate` (refused tools) and the API (interrupts, human decisions, email sends). Runs are buffered, then written to `agent_runs` + `agent_trace_steps` in two requests. Text is redacted and capped, and writes are fail-open (counted in `/api/health`). The run id travels in `FreelancerContext.trace_run_id` and comes back as the `X-Trace-Id` header.
- **Tool gate** (`middleware/dynamic_tools.py: enforce_tool_gate`) — an `after_model` hook listed *after* HITL so it runs first. It refuses tools not allowed at the current level (including another level's email), and `CLIENT_REPLY_BLOCKED` tools (`update_invoice_details`, `escalate_dispute`) on runs started by a client reply (`FreelancerContext.untrusted_input`).
- **`db.py`** — Supabase REST wrappers with Fernet-encrypted token storage. Tables (in `supabase/schema.sql`): `users`, `invoices`, `communication_history`, `agent_runs`, `agent_trace_steps` (traces: RLS on, 30-day pg_cron purge). Per-user scoping enforced at the API layer; guests get a per-session `guest-<uuid>` ID via HTTP-only cookie.

### API (`api/index.py`)
Single-file FastAPI backend. Handles: Google OAuth (with guest→user data migration), invoice CRUD (ownership-checked via `authorize_invoice_access`), chat (agent invocation with thread_id config), HITL resume decisions, Gmail webhook for inbound client replies, per-user Telegram connect/webhook/notifications.

### Frontend (`frontend/src/`)
React 19 + TypeScript + Tailwind CSS 4 + React Router. Key pages: Landing, Dashboard (invoice list/stats), ChatPanel (agent conversation with HITL approval UI). Auth via `AuthContext` (JWT + Google profile). API calls in `api.ts`.

### Escalation Levels
A strict ladder, with the rules in `src/services/escalation_policy.py`. Escalation emails don't stack: each level may send only its own email, as many times as needed. The invoice delivery email is allowed at every level.
- **Level 0:** Invoice setup only (`update_invoice_details`, which starts the ladder at 1)
- **Level 1 (Friendly):** polite reminder, status check, payment tools, `escalate_dispute`
- **Level 2 (Formal):** formal demand letter, status check, payment tools, `escalate_dispute`
- **Level 3 (Legal):** final notice, small claims lookup (Tavily), court filing guide, status check, payment tools. Nothing above.

The level only rises, one step at a time, and only when the freelancer approves. That happens through the Escalate button (`/escalate`) or an approved `escalate_dispute` proposal (HITL card, approve/reject only). `invoice_service.escalate()` is the only writer, a conditional update from the level the caller saw. Chat runs never save a level, and a client reply can't propose an escalation. `send_approved_draft` checks the email against the saved level right before Gmail (`level_mismatch`).

### Key Data Flow
1. User creates invoice → agent starts at Level 0
2. Chat triggers agent with dynamic tool set based on current level
3. Draft tools produce email content → HITL interrupt for approval
4. On approval → Gmail sends email, tracks thread ID on invoice
5. Client replies arrive via Gmail push webhook → stored as inbound communications → Telegram notification

### Evals (`evals/`)
Golden set in `evals/golden/level_{0..3}.yaml`. `harness.py` runs a case through the real API and graph, offline (fake DB, Gmail outbox, canned search). `checks.py` grades it from its traces: tool choice, approval invariant, tone rules, LLM judge. Tier 1 (`tests/test_eval_invariants.py`) replays scripted runs on every test run. Tier 2 (`python -m evals.run`) uses the live model, writes `evals/results/latest.md`, and gates CI (`.github/workflows/evals.yml`). `python -m evals.promote` turns a bad trace into a case. When you change prompts or tools, run the live eval.

### Tests
`pytest` (backend, includes eval tier 1) and `cd frontend && npx vitest run`. The fakes shared by tests and evals are in `tests/fakes.py`.

## External Services
- **Groq API** (LLM — llama-3.3-70b-versatile)
- **Tavily API** (web search for legal procedures)
- **Google OAuth + Gmail API** (auth + email send/read/watch)
- **Telegram Bot API** (push notifications)

## Environment
Copy `.env.example` to `.env`. Required keys: `GROQ_API_KEY`, `TAVILY_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `SECRET_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`. Optional: `DATABASE_URL` (conversation store, see Deployment; leave empty locally, and tests force memory), `LANGSMITH_TRACING` + `LANGSMITH_API_KEY` + `LANGSMITH_AGENT_ID`/`LANGSMITH_AGENT_ENVIRONMENT` (or `LANGSMITH_PROJECT`, never both) (LangSmith alongside the built-in tracer; runs labelled by `langsmith_config`; tests and evals force it off), `EVAL_JUDGE_MODEL` (eval judge, default `openai/gpt-oss-20b`), `EVAL_JUDGE_GROQ_API_KEY` (optional second Groq key for the judge; CI paces the live eval with `--pace 20` to stay under Groq's free-tier 8k tokens/min), `TELEGRAM_BOT_TOKEN` + `TELEGRAM_BOT_USERNAME` + `TELEGRAM_WEBHOOK_SECRET` (for per-user Telegram notifications), `GOOGLE_PUBSUB_TOPIC` (for Gmail push), `CORS_ALLOW_ORIGINS` (comma-separated origins for cross-origin dev).
