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

- Branch: `refactor/clean-architecture`, cut from `main` at `ac060cb`. Nothing pushed; no pull request.
- Baseline before any change: backend 761 passed, 13 skipped; frontend 178 passed, 6 skipped.
- Now: backend 971 passed, 13 skipped; frontend 178 passed, 6 skipped. `api/index.py` is about 1,270 lines (from 2,388).
- Done: groups 1-4, and 5.1-5.4. Last commit of 5.4: `89e0f7a`.
- 5.5 in progress (not ticked): the email preflight is domain policy (`src.domain.chat.email_preflight`, commit `af2e574`). Left: moving the chat and escalate routes.
- Next, decided: before moving chat/escalate (5.5), inbound reply (5.6) and approve/resume (5.7), move the helpers those four share out of `api/index.py` into one `web/` module (`serialize_messages`, `serialize_message_content`, `extract_state`, `action_card`, `extract_interrupt`, `attachment_note`, `generate_draft_preview`, `traced_run`, `run_id_of`, `prior_message_count`, `trim_action_response`). Otherwise each router factory needs 12+ callables. Pin with the OpenAPI snapshot and the email-card tests; then 5.5 to 5.8.
- Live eval for groups 3-4: the user approved a run on 2026-11-16 (local key confirmed not production's org), but every model call got `401 Invalid API Key` from Groq with the key in `.env` (no shell override). No result yet: it needs a valid key from the user, then a rerun (see "Live eval" below).

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
