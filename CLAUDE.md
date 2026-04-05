# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

InvoiceChaser — an AI-powered invoice dispute agent for freelancers. Uses LangGraph to orchestrate a multi-level escalation system (Friendly → Formal → Legal) with human-in-the-loop approval before sending emails. Full-stack: FastAPI backend (Vercel serverless), React frontend, SQLite database.

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

## Architecture

### Agent Core (`src/`)
- **`agent.py`** — LangGraph state machine with InMemorySaver checkpointer. Middleware dynamically filters available tools and system prompts based on escalation level.
- **`state.py`** — `FreelancerContext` and `AgentState` dataclasses defining agent state shape.
- **`prompts.py`** — Prompt loading utilities.
- **`middleware/`** — Three middleware layers:
  - `dynamic_tools.py` — Gates tools by escalation level (LEVEL_0/1/2/3_TOOLS constants)
  - `dynamic_prompts.py` — Shifts system prompt tone per escalation level
  - HITL middleware for draft approval interrupts
- **`tools/`** — Tool definitions organized by function: `drafting.py` (email templates), `escalation.py` (level progression), `invoice.py` (status/fees), `legal.py` (Tavily web search), `payment_tools.py` (mark paid/pending)
- **`services/`** — `gmail_service.py` (send/read/watch via Gmail API), `telegram_service.py` (bot notifications)
- **`db.py`** — SQLite with WAL mode, Fernet encryption for stored tokens. Tables: `users`, `invoices`, `communications`. Auto-initializes via `init_db()`.

### API (`api/index.py`)
Single-file FastAPI backend (~800 lines). Handles: Google OAuth, invoice CRUD, chat (agent invocation with thread_id config), HITL resume decisions, Gmail webhook for inbound client replies, Telegram notifications.

### Frontend (`frontend/src/`)
React 19 + TypeScript + Tailwind CSS 4 + React Router. Key pages: Landing, Dashboard (invoice list/stats), ChatPanel (agent conversation with HITL approval UI). Auth via `AuthContext` (JWT + Google profile). API calls in `api.ts`.

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
5. Client replies arrive via Gmail push webhook → stored as inbound communications → Telegram notification

## External Services
- **Groq API** (LLM — llama-3.3-70b-versatile)
- **Tavily API** (web search for legal procedures)
- **Google OAuth + Gmail API** (auth + email send/read/watch)
- **Telegram Bot API** (push notifications)

## Environment
Copy `.env.example` to `.env`. Required keys: `GROQ_API_KEY`, `TAVILY_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `SECRET_KEY`. Optional: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GOOGLE_PUBSUB_TOPIC`.
