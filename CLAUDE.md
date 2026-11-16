# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

InvoiceChaser — a multi-tenant, AI-powered invoice dispute agent for freelancers. Uses LangGraph to orchestrate a multi-level escalation system (Friendly → Formal → Legal) with human-in-the-loop approval before sending emails. Full-stack: FastAPI backend (Vercel serverless), React frontend, Supabase (Postgres) database. Each freelancer connects their own Gmail — data is isolated per `user_id`.

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

### Backend boundaries

- **`api/index.py`** exports the module-level FastAPI app for Vercel. **`web/bootstrap.py`** composes the live dependencies; collaborators are read through the mutable `Deps` container at call time so tests can replace them after import.
- **`web/app.py`**, **`web/identity.py`**, **`web/schemas.py`**, and **`web/routers/`** own HTTP setup, identity, validation and feature routes. `web/spa.py` serves `frontend/dist` when a frontend build exists. The API includes OAuth, sender profiles, invoice files/CRUD, chat, summaries/history, approvals, tracing, and the Resend inbound webhook at `/api/email/inbound`.
- **`src/domain/`** contains invoice rules, escalation policy, email wording, the duplicate-send window and the chat-topic guard. It imports only the standard library. Shared email wording preserves the original, distinct tool-result and approval-preview amount formatting.
- **`src/ports.py`** defines store, email, session, tracing and clock protocols. **`src/usecases/`** owns application flows and depends only on ports and the domain. `src/usecases/invoices.py` owns invoice writes, including payment outcomes, escalation and settlement.
- **`src/adapters/supabase/`** implements persistence and encrypted OAuth token storage. **`src/adapters/agent_session.py`** owns invoice thread addressing, interrupt inspection and read-before-sync. `src/db.py` and `src/services/invoice_service.py` have been removed.
- **`src/agent.py`**, **`src/tools/`**, and **`src/middleware/`** remain the LangGraph adapter. `src/checkpointer.py` selects pooled Postgres checkpoints or memory fallback. Payment/status tools require human approval; `web/approval.py` reads pending state before syncing, sends and logs approved email before resuming, then commits the approved outcome through the invoice use case.
- **`src/services/gmail_service.py`** sends mail using injected token persistence. **`src/services/resend_inbound.py`** verifies and fetches received replies; **`web/inbound_reply.py`** runs the reply analysis. Inbound replies arrive through Resend, not a Gmail push webhook. There are no Telegram routes or notifications in the current application.
- **`src/services/conversation_summary.py`** maintains persisted conversation summaries. **`src/observability/tracer.py`** receives an injected trace sink and writes redacted, fail-open traces; HTTP responses expose run IDs through `X-Trace-Id`.

### Frontend (`frontend/src/`)

React 19 + TypeScript + Tailwind CSS 4 + React Router. `api.ts` is the backend gateway, called through `hooks/`. `hooks/queries.ts` shares query keys/options. `contexts/AuthContext.tsx` provides the session from `hooks/useAuthSession.ts`; `hooks/useInvoiceFiles.ts` handles parsing and generated-invoice persistence. `components/ChatPanel.tsx` composes `hooks/useChatPanel.ts` with views under `components/chat/`. `components/LandingPage.tsx` composes sections under `components/landing/`. Production components and context providers cannot import the API gateway directly; the frontend architecture test enforces this boundary.

Backend architecture rules are enforced in `tests/test_architecture.py`, with an empty violations allow-list. Tests/evals replace `Deps` collaborators rather than patching entry-point exports.

### Escalation Levels
- **Level 0:** Invoice setup only (`update_invoice_details`)
- **Level 1:** Friendly reminders + status checks + payment marking
- **Level 2:** + Formal demand letters + late fee calculations
- **Level 3:** + Small claims lookup (Tavily) + court filing guide + final notice

### Key Data Flow
1. User creates invoice → agent starts at Level 0
2. Chat triggers agent with dynamic tool set based on current level
3. Draft tools produce email content → HITL interrupt for approval
4. On approval → Gmail sends email, tracks thread ID on invoice
5. Client replies arrive via the signed Resend webhook → stored as inbound communications → agent analysis

### Evals (`evals/`)
Golden set in `evals/golden/level_{0..3}.yaml`. `harness.py` runs a case through the real API and graph, offline (fake DB, Gmail outbox, canned search). `checks.py` grades it from its traces: tool choice, approval invariant, tone rules, LLM judge. Tier 1 (`tests/test_eval_invariants.py`) replays scripted runs on every test run. Tier 2 (`python -m evals.run`) uses the live model, writes `evals/results/latest.md`, and gates CI (`.github/workflows/evals.yml`). `python -m evals.promote` turns a bad trace into a case. When you change prompts or tools, run the live eval.

### Tests
`pytest` (backend, includes eval tier 1) and `cd frontend && npx vitest run`. The fakes shared by tests and evals are in `tests/fakes.py`.

## External Services
- **Groq API** (LLM — configurable with `GROQ_MODEL`, default `openai/gpt-oss-120b`)
- **Tavily API** (web search for legal procedures)
- **Google OAuth + Gmail API** (auth + email send/read/watch)

## Environment
Copy `.env.example` to `.env`. Required keys: `GROQ_API_KEY`, `TAVILY_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `SECRET_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`. Optional: `DATABASE_URL` (conversation store, see Deployment; leave empty locally, and tests force memory), `LANGSMITH_TRACING` + `LANGSMITH_API_KEY` + `LANGSMITH_AGENT_ID`/`LANGSMITH_AGENT_ENVIRONMENT` (or `LANGSMITH_PROJECT`, never both) (LangSmith alongside the built-in tracer; runs labelled by `langsmith_config`; tests and evals force it off), `EVAL_JUDGE_MODEL` (eval judge, default `openai/gpt-oss-20b`), `RESEND_API_KEY` + `RESEND_INBOUND_DOMAIN` + `RESEND_WEBHOOK_SECRET` (for verified inbound replies), `CORS_ALLOW_ORIGINS` (comma-separated origins for cross-origin dev).
