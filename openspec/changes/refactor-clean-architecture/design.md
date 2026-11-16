# Design

## Context

See `proposal.md` for motivation. Constraints that shape the approach:

- Vercel serves everything through the module-level `app` in `api/index.py`; the SPA catch-all finds `frontend/dist` relative to that file.
- `tests/conftest.py` sets environment variables before the app is imported, and fakes the database at `src.db._supabase_rest_request`. Those tests go through real HTTP handlers, so they describe behavior and survive code moves.
- About 50 `monkeypatch.setattr` calls target `api.index` attributes. They pin a function's location, not its behavior.
- Importing `src.agent` builds the Groq model, the checkpointer and the compiled graph.
- Actual policy is small: roughly 700 lines across `invoice_service`, `email_drafts` and helpers in `index.py`.

## Goals / Non-Goals

**Goals:**

- Policy imports only the standard library and is testable without any framework.
- Use cases depend on ports; adapters and the HTTP layer depend inward.
- Fakes are passed in, never patched in.
- The dependency rule is enforced by a test.
- Every commit keeps the full suite green.

**Non-Goals:**

- No change to routes, responses, email text, prompts, tools or schema.
- No abstraction over LangGraph beyond one session adapter. The agent, tools and middleware remain the LangGraph adapter layer.
- No lazy construction of the agent; import-time behavior is unchanged.
- No new libraries (no DI framework, no import-linter).

## Decisions

**Layout**

```
api/index.py     entry point: app = create_app(deps)
web/app.py       factory, Deps container, middleware, exception handlers
web/identity.py  identity as Depends
web/schemas.py   request models
web/routers/     auth, invoices, chat, approval, inbound, traces, health
src/domain/      policy, stdlib only
src/ports.py     Protocols
src/usecases/    one module per flow
src/adapters/    supabase, gmail, resend, agent_session, tracing
```

- **The HTTP layer lives in `web/`, not `api/`.** Vercel can treat each Python file under `api/` as its own serverless function, which would publish `api/app.py` or a router file as an endpoint. Only the entry point stays in `api/`. Alternative: underscore-prefixed files in `api/`; rejected because it relies on a naming convention nobody will remember.
- **`Deps` is one mutable container read at call time.** Code reads `deps.agent`, not a module global, so a test that swaps a field affects every caller wherever that caller lives. This is what removes the silent-patch risk; constructor injection per use case follows as flows are extracted.
- **Ports only where a second implementation exists.** `FakeDB`, the eval Gmail outbox and `ScriptedModel` already are those implementations. Alternative: a port for every collaborator; rejected because it adds files without removing coupling.
- **`typing.Protocol` over abstract base classes.** Existing fakes satisfy a Protocol without inheriting from it. Alternative: ABCs; rejected because every fake would need editing for no behavioral gain.
- **A plain dataclass `Deps` plus `app.state`, read through `Depends`.** Alternative: a DI library; rejected as an extra dependency for about eight collaborators.
- **Seam before extraction.** Tests are converted from patches to injected fakes while the code is still in `index.py`. Extraction then cannot silently disable a fake. Alternative: extract first and fix tests after; rejected because a patched name that is still imported keeps "working" while the real collaborator runs.
- **Characterization tests before each move.** Golden tests pin the email text, escalation rule, duplicate-send window and chat preflight exactly as they behave today, including any oddities. Oddities are recorded, not fixed, in this change.
- **Architecture test written with `ast`.** It asserts the import rule and carries an allow-list of today's violations that shrinks per phase. Alternative: import-linter; rejected to avoid a dependency.
- **One source for email wording.** Templates move to `src/domain/` and both `src/tools/drafting.py` and the approval flow read them there. Text stays byte-identical.
- **`AgentSession` adapter.** It owns the `thread_id` config, the pending-interrupt walk (copied in five places) and the rule that state is read before it is synced.
- **`src/db.py` is split behind store ports, with `db.py` re-exporting during the transition.** It is deleted once nothing imports it.
- **Approve/resume is extracted last.** It is the longest flow and its step order affects correctness, so it gets extra order-sensitive tests first.
- **Frontend keeps a single `api.ts` gateway.** Components stop importing it and use hooks instead, following the existing `hooks/queries.ts` pattern. Alternative: per-feature API modules; rejected as churn without a decoupling gain.

## Risks / Trade-offs

- [A converted test no longer exercises what the patch did] → Convert one patched name at a time and confirm the test still fails when the fake misbehaves.
- [Email text drifts while templates are unified] → Golden tests compare full strings; the live eval runs after the domain and use-case phases.
- [The step order in approve/resume changes] → Order-sensitive tests are added before extraction; that flow moves in its own commit.
- [SPA serving breaks when the catch-all moves] → A test asserts the route is registered when `frontend/dist` exists; a Vercel preview is checked before merge.
- [Env-var ordering in `conftest.py` breaks] → `create_app` reads configuration when called, and `api/index.py` still calls it at import.
- [A long-lived branch conflicts with feature work] → One draft pull request per phase, each mergeable alone.
- [More files and indirection] → Accepted; bounded by the "second implementation" rule for ports.

## Migration Plan

Each phase merges separately and leaves production behavior unchanged, so rollback is reverting that phase's pull request. No data migration and no environment changes.

## Open Questions

- Whether `CLAUDE.md`'s Gmail push webhook and Telegram descriptions are stale or describe code outside `api/`. Checked during cleanup; it does not affect the structure.
