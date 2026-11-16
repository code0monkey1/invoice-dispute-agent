# Handoff: clean-architecture refactor

Read this first if you are a new session continuing the work. Update the "State" section at the end of every task group and commit it.

## How to resume

1. `git checkout refactor/clean-architecture`
2. Read `proposal.md` (why), `design.md` (decisions and layout), then `tasks.md` (the checklist; `- [x]` is done).
3. Confirm the suites are green before changing anything:
   - `.venv/bin/python -m pytest -q` from the repo root
   - `cd frontend && npx vitest run`
4. Take the first unchecked task in `tasks.md`. `/opsx:apply refactor-clean-architecture` does the same.

## Rules for every task

- Behavior does not change: same routes, responses, email text, prompts, tools, schema.
- Test first: pin current behavior (or write the failing test for a new seam), then move code, then run both suites.
- One commit per task; tick the task in `tasks.md` in the same commit.
- Never change the expected values in `tests/test_policy_golden.py` or the route set in `tests/test_route_contract.py` to make a move pass.
- When a violation is fixed, delete its line from `KNOWN_VIOLATIONS` in `tests/test_architecture.py`; that test requires an exact match.
- Commit only files this work touches. The working tree had unrelated uncommitted changes when the branch was cut (`.gitignore`, `evals/results/latest.*`, another OpenSpec change's `tasks.md`, several untracked folders); leave them alone.

## State

- Branch: `refactor/clean-architecture`, cut from `main` at `ac060cb`.
- Baseline before any change: backend 761 passed, 13 skipped; frontend 178 passed, 6 skipped.
- Now: backend 988 passed, 13 skipped. `api/index.py` is the 19-line entry point; `web/bootstrap.py` is the composition root.
- Done: groups 1-5 (backend). Next: group 6 (frontend), then group 7 (integration). Groups 1-5 ship as one pull request first; group 6 onwards is a follow-up branch.
- Live eval: a full local run on 2026-11-16 at `61e0f92` failed its gate on three cases. A/B runs on `main` vs the branch showed them to be model variance: identical captured model inputs, `l2-quality-dispute` flaky on `main` too, `l1-client-promises-date` 7/7 on `main` and 10/15 on the branch with the last 10 at 9/10; `l0-injected-reply` failed in the baseline as well. The PR's required `golden-set` CI check is the eval gate for the final code.
- Tasks 5.6, 5.7 and a 5.8 draft were done by another tool (Codex) on 2026-11-16 in this same checkout. Reviewed against the original code: faithful except the 5.8 draft dropping INFO logging and the SPA comments (fixed in `cb46ace`). Agents must not share a checkout at the same time.

### Layout so far

- `src/domain/`: invoice rules, email templates, chat-topic guard, duplicate-send window. Standard library only.
- `src/ports.py`: the Protocols. `src/adapters/supabase/` (the whole former `db.py`; `src/db.py` aliases it in `sys.modules` until 5.8), `src/adapters/agent_session.py` (thread config, interrupt walk, read-before-sync).
- `src/usecases/`: `auth.py`, `sender_profile.py`, `invoices.py`. They depend on ports only; `src/services/invoice_service.py` still holds `apply_approved_outcome` and `set_escalation_level` until 5.5/5.7.
- `web/`: `app.py` (factory, `Deps`, `Live`), `identity.py`, `schemas.py`, `routers/` (health, traces, accounts, invoices).

### How use cases are wired

- Build them in `api/index.py` with `Live(lambda: deps.db)` / `Live(lambda: deps.agent_session)`, never with `deps.db` itself: a use case built at import must see a database a test swaps later (`tests/test_wiring.py`).
- Routers get the app's helpers as arguments and keep the original handler names and docstrings: `tests/test_openapi_contract.py` compares the schema with `tests/contract/openapi.json`.

### Review of the other session's commits (`086e343`..`46846ca`)

Ten commits were made by a different tool between this file's previous update and now. Reviewed against the original code on 2026-11-15; fixed with tests:
- `d5f6e3f`: the chat guard loaded all the owner's invoices before its quick checks (an extra database read per chat message).
- `86fcd5e`: history skipped the sync only for well-formed approval interrupts; it used to skip it for any interrupt.
- `3213fac`: the account use cases held the import-time `deps.db`.
- `a42c2b5`: five renamed handlers and three dropped docstrings changed the OpenAPI schema.
- `7838130`: its unwired 5.3 draft had five differences from the original handlers (listed in that commit).
Accepted as-is: `src/db.py` was moved whole, not split, into one adapter module; chat now always uses the `invoice-{id}` thread (only an unprefixed thread id behaves differently, and it now reaches the invoice's real conversation).

## Things learned that the tasks do not say

- **Import order (fixed in group 2).** `api/index.py` used to copy `src.db` names at import, so a test module importing it at the top could break `tests/conftest.py`'s storage patches. It now calls `deps.db.<name>()`. Keep it that way: never copy a collaborator's function into a module at import.
- **New invoices start at escalation level 0**, not 1.
- **The SPA catch-all** is registered only when `frontend/dist` exists, and its path is computed relative to `api/index.py`. Keep that correct when it moves to `web/`.
- **`vercel.json`** names `api/index.py`, and Vercel looks for the module-level `app` there. Both stay.
- **How to check a converted test still tests something:** make its fake ineffective (e.g. have `Overrides` ignore its members) and confirm the test fails. Two tests needed stronger assertions for this in group 2.
- **The silent-patch risk.** If a caller moves out of `api/index.py` while the old name is still imported there, `monkeypatch.setattr(api_index, ...)` succeeds but does nothing. Convert a test to an injected fake before moving the code it fakes, and check the test fails when the fake misbehaves.
- **Already covered, no new tests needed:** the chat email preflight (`tests/test_email_card_routing.py`), the chat topic guard (`tests/test_invoice_delivery_chat.py`), the top escalation level (`tests/test_escalate_invoice.py`).
- **Possibly stale docs:** `CLAUDE.md` describes a Gmail push webhook and Telegram routes; `api/index.py` has neither. Check the rest of the repo in task 7.2.
- **Dead code to remove in group 5 or 7:** the second `/api/health` (shadowed, never reached), unused imports in `api/index.py` (`Flow`, `id_token`, `google_requests`, `StaticFiles`, `update_user_history_id`, `get_user_by_email`), and `build_initial_invoice_message` once a search confirms no caller.
- **Live eval** (`python -m evals.run`) is due after groups 3 and 5, because templates and tools move. Never run it with production's Groq key or organisation: that once used up production's daily quota (user's memory note `agent-evals-setup`). Use `--pace 8`, `DATABASE_URL=`, a fake `SUPABASE_URL`, and `--out-dir` in the scratchpad with `--baseline evals/results/baseline.json`, so the user's uncommitted `evals/results/latest.*` aren't overwritten.
- **Review another tool's commits before building on them.** Tests passing wasn't enough: of the regressions above, only the draft's would have failed a test. Compare each moved function with the original (AST-normalised diff) and check what a use case captures at import.

### Release continuation

- PR #33 live agent and summary evals passed. Its backend job exposed FastAPI 0.163.1's lazy included routers: the route contract's direct `app.routes` walk saw no API routes. Reproduced both failures with CI's FastAPI installed in an isolated target; switched only inspection to FastAPI's public `iter_route_contexts` when available. Expected routes are unchanged. Full suite: 988 passed, 13 skipped with both local FastAPI 0.135.3 and CI FastAPI 0.163.1.
- Local Homebrew default Node is broken (missing simdjson dylib); use `PATH=/opt/homebrew/opt/node@22/bin:$PATH`. Frontend baseline: 178 passed, 6 skipped.
- Independent backend review found two compatibility gaps, both fixed with failing-first regression tests: Gmail token reads now follow a swapped `deps.db`; draft tools retain their original no-comma amount formatting and explicit-zero/negative balance rules while sharing wording with the unchanged approval preview. Full suite after fixes: 1001 passed, 13 skipped. Policy golden expectations and the route set remain unchanged.
- User confirmed release target: existing Vercel project; no Netlify setup requested.

### Frontend follow-up

- Task 6.1: components with existing hooks keep them; InvoiceForm parsing and generated-invoice persistence now use useInvoiceFiles, and AuthProvider delegates to useAuthSession. Existing component tests unchanged. Added file-operation and session hook tests. Backend 988 passed/13 skipped; frontend 184 passed/6 skipped; production build passes.
- Task 6.2: ChatPanel now composes a container hook, ChatConversation, ChatSidebar and shared settlement confirmation. Existing ChatPanel tests unchanged; all 184 frontend tests pass, production build and lint pass.
- Task 6.3: LandingPage sections moved verbatim to components/landing, including the original timed demo and FAQ structured data. Backend 988 passed/13 skipped; frontend 184 passed/6 skipped; build and lint pass.
- Task 6.4: AST-based frontend boundary test rejects static imports, re-exports and dynamic imports of api.ts under components and contexts. Frontend 186 passed/6 skipped, build and lint pass.
- Task 7.1: backend architecture allow-list already empty; removed the remaining unused bootstrap import. Expanded CI classification to include moved policy/adapters/use cases/HTTP modules and summary seams; failing-first cases proved the old classifier skipped them. Full backend: 1011 passed/13 skipped; frontend: 186 passed/6 skipped, build and lint pass. Boundary check excludes component test fixtures (which intentionally import the mocked API).
