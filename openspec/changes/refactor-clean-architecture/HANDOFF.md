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
- Done: task group 1 (regression net), commit `4e5dbe9`. Backend is now 793 passed, 13 skipped.
- Next: task 2.1, the app factory and `Deps` container.
- Nothing has been pushed and no pull request is open.

## Things learned that the tasks do not say

- **Import order trap.** `tests/conftest.py` patches `src.db.upload_invoice_file` and `download_invoice_file`, but `api/index.py` copies those names at import. The patch only works because `api.index` is first imported inside the `client` fixture, after the patch is active. A test module that imports `api.index` at the top breaks `tests/test_generated_invoice.py`. Import it inside functions until task 2.4 replaces these patches with injected fakes.
- **New invoices start at escalation level 0**, not 1.
- **The SPA catch-all** is registered only when `frontend/dist` exists, and its path is computed relative to `api/index.py`. Keep that correct when it moves to `api/app.py`.
- **`vercel.json`** names `api/index.py`, and Vercel looks for the module-level `app` there. Both stay.
- **The silent-patch risk.** If a caller moves out of `api/index.py` while the old name is still imported there, `monkeypatch.setattr(api_index, ...)` succeeds but does nothing. Convert a test to an injected fake before moving the code it fakes, and check the test fails when the fake misbehaves.
- **Already covered, no new tests needed:** the chat email preflight (`tests/test_email_card_routing.py`), the chat topic guard (`tests/test_invoice_delivery_chat.py`), the top escalation level (`tests/test_escalate_invoice.py`).
- **Possibly stale docs:** `CLAUDE.md` describes a Gmail push webhook and Telegram routes; `api/index.py` has neither. Check the rest of the repo in task 7.2.
- **Dead code to remove in group 5 or 7:** the second `/api/health` (shadowed, never reached), unused imports in `api/index.py` (`Flow`, `id_token`, `google_requests`, `StaticFiles`, `update_user_history_id`, `get_user_by_email`), and `build_initial_invoice_message` once a search confirms no caller.
- **Live eval** (`python -m evals.run`) is due after groups 3 and 5, because templates and tools move. It uses the Groq API and is rate-limited.
