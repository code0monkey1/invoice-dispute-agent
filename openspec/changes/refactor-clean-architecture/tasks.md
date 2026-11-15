# Tasks

Baseline on 2026-11-15 before any change: `pytest` 761 passed, 13 skipped; `npx vitest run` 178 passed, 6 skipped. Every task below ends with both suites at least at that baseline.

## 1. Regression net

- [x] 1.1 Add `tests/test_route_contract.py` pinning method, path and registration order of every route, and verify it passes against the unchanged app
- [x] 1.2 Add golden tests for `generate_draft_preview` (exact subject and body per draft type) and verify they pass unchanged
- [x] 1.3 Add characterization tests for the escalation next-level and cap rule, `already_sent_recently`, `prepare_chat_email` branches and `is_invoice_chat_message`, and verify they pass unchanged
- [x] 1.4 Add `tests/test_architecture.py` (import rule via `ast`, with an allow-list of current violations) and verify it passes and fails when a forbidden import is added

## 2. Injection seam

- [x] 2.1 Add `web/app.py` with `create_app(deps)` and a `Deps` dataclass; `api/index.py` builds `app` from it; verify the route contract test and full suite pass
- [x] 2.2 Move identity helpers to `web/identity.py` and use `Depends` in handlers; verify `tests/test_security.py` and `tests/test_pentest_invoice_writes.py` pass
- [x] 2.3 Move the request models to `web/schemas.py`; verify `tests/test_create_validation.py` passes
- [x] 2.4 Convert tests and `evals/harness.py` from patching `api.index` to injected fakes, one patched name at a time (`agent`, `invoke_agent_with_retry`, `get_user_gmail_tokens`, `fetch_received_email`, `send_email_via_gmail`, then the rest); verify each converted test fails when its fake is made to misbehave
- [x] 2.5 Extend the architecture test to forbid `setattr` patches on `api.index` in `tests/` and `evals/`; verify it passes

## 3. Domain

- [x] 3.1 Create `src/domain/invoice.py` with the commit rules from `invoice_service` as pure functions and unit tests that import nothing but the domain; verify `tests/test_invoice_service.py` still passes
- [x] 3.2 Move email templates to `src/domain/email_templates.py`, read by both the approval flow and `src/tools/drafting.py`; verify the golden tests from 1.2 pass unchanged
- [x] 3.3 Move escalation policy, the duplicate-send guard and the chat topic guard to `src/domain/`; verify the tests from 1.3 pass unchanged
- [x] 3.4 Tighten the architecture test so `src/domain/` may import only the standard library; verify it passes

## 4. Ports and adapters

- [x] 4.1 Add `src/ports.py` (`InvoiceStore`, `UserStore`, `CommunicationLog`, `EmailSender`, `InboundMail`, `AgentSession`, `TraceSink`, `Clock`); verify `FakeDB`-backed fakes satisfy them in a typing test
- [x] 4.2 Split `src/db.py` into `src/adapters/supabase/` implementing the store ports, with `db.py` re-exporting; verify the full suite passes
- [x] 4.3 Pass token persistence into the Gmail adapter and a `TraceSink` into the tracer so neither imports the database; verify `tests/test_tracing.py`, `tests/test_tracer_core.py` and `tests/test_approve_sends_email.py` pass
- [x] 4.4 Add `src/adapters/agent_session.py` owning thread config, the pending-interrupt walk and read-before-sync; replace the copies in `index.py`; verify `tests/test_history_keeps_approval.py` and `tests/test_invoice_list_approvals.py` pass
- [ ] 4.5 Remove adapter-to-adapter imports from the architecture allow-list; verify it passes

## 5. Use cases and routers

- [ ] 5.1 Extract health and traces to `web/routers/` and remove the shadowed second `/api/health`; verify `tests/test_traces_endpoint.py` and the route contract pass
- [ ] 5.2 Extract auth and sender profile (use case plus router); verify `tests/test_sender_profile.py` and `tests/test_security.py` pass
- [ ] 5.3 Extract invoice CRUD, upload, parsing and generator; verify `tests/test_generated_invoice.py`, `tests/test_create_validation.py` and `tests/test_settle_invoice.py` pass
- [ ] 5.4 Extract summary and history; verify `tests/test_summary_api.py` and `tests/test_history_keeps_approval.py` pass
- [ ] 5.5 Extract escalate and chat; verify `tests/test_escalate_invoice.py`, `tests/test_email_card_routing.py` and `tests/test_invoice_delivery_chat.py` pass
- [ ] 5.6 Extract inbound reply; verify `tests/test_reply_tracking.py` and `tests/test_tool_gate.py` pass
- [ ] 5.7 Add order-sensitive tests for approve/resume, then extract it; verify `tests/test_approve_sends_email.py` and `tests/test_real_graph_payments.py` pass
- [ ] 5.8 Reduce `api/index.py` to the entry point and delete `src/db.py` re-exports nothing uses; verify the full suite and `python -m evals.run` against the pre-refactor `evals/results/latest.md`

## 6. Frontend

- [ ] 6.1 Add hook tests, then move API calls out of `Dashboard`, `InvoiceTable`, `InvoiceForm`, `TracePanel`, `InvoiceGeneratorPage` and `AuthContext` into hooks; verify existing component tests pass unchanged
- [ ] 6.2 Split `ChatPanel.tsx` into a container hook and presentational components; verify `ChatPanel.test.tsx` passes unchanged
- [ ] 6.3 Split `LandingPage.tsx` into section components with no logic change; verify `npm run build` and `npm run lint` pass
- [ ] 6.4 Add a test that no file under `components/` imports `api.ts`; verify it passes

## 7. Integration

- [ ] 7.1 Empty the architecture-test allow-list and remove unused imports; verify the full backend and frontend suites pass
- [ ] 7.2 Update the architecture section of `CLAUDE.md` to the new layout and correct its Gmail-webhook and Telegram descriptions against the code; verify every path it names exists
- [ ] 7.3 Run the app locally and exercise create invoice, chat, approve a draft, escalate, settle and `/api/health`; verify each behaves as before
- [ ] 7.4 Deploy a Vercel preview and verify `/api/health` responds and the SPA loads
