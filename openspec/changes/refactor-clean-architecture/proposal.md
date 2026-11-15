# Proposal

## Why

Invoice rules cannot run without FastAPI, LangGraph, Supabase or Gmail: `api/index.py` (2,388 lines, 26 routes) mixes HTTP, identity, checkpoint handling, email sending and policy, and `src/services/invoice_service.py` imports the Supabase layer directly. Tests insert fakes by patching `api.index` attributes, so moving code can silently disable a fake instead of failing a test, which makes every later change riskier.

## What Changes

- Add a regression net before any code moves: a route contract test, golden tests for policy that lives in the HTTP layer, and an import-rule test.
- Add an injection seam: an app factory with a dependency container and FastAPI `Depends`, replacing patches on `api.index` in tests and in `evals/harness.py`.
- Move business policy into a `src/domain/` package that imports only the standard library: invoice commit rules, escalation policy, email templates, the duplicate-send guard and the chat topic guard.
- Define ports (`src/ports.py`) and move Supabase, Gmail, Resend, tracing and checkpoint access behind them in `src/adapters/`.
- Extract use cases (`src/usecases/`) and split `api/index.py` into feature routers under `web/`; `api/index.py` stays as the Vercel entry point.
- Frontend: components reach the backend only through hooks; `ChatPanel` and `LandingPage` are split into smaller parts.
- Remove dead code found on the way: the shadowed second `/api/health` route and unused imports.

No route, response shape, email text or database schema changes. Nothing here is breaking.

## Capabilities

### New Capabilities

None. This change alters structure only, so the change sets `skip_specs: true`.

### Modified Capabilities

None. The requirements in `agent-conversation-memory`, `chat-email-approval` and `chat-quick-actions` stay as written and must keep passing.

## Impact

- Backend: `api/index.py`, `src/db.py`, `src/services/`, `src/observability/tracer.py`, new `web/` (`app.py`, `identity.py`, `schemas.py`, `routers/`), `src/domain/`, `src/ports.py`, `src/usecases/`, `src/adapters/`.
- Tests and evals: about 25 test files that patch `api.index`, `tests/conftest.py`, `tests/fakes.py`, `evals/harness.py`.
- Frontend: `ChatPanel`, `Dashboard`, `InvoiceTable`, `InvoiceForm`, `TracePanel`, `InvoiceGeneratorPage`, `AuthContext`, `LandingPage`, and the hooks they use.
- Deployment: `vercel.json` keeps pointing at `api/index.py`, which keeps exporting `app`.
- Docs: `CLAUDE.md` architecture section.
- No new runtime dependencies.
