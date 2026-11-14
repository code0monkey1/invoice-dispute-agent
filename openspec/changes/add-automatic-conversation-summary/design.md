# Design

## Context

See proposal.md. Messages live in LangGraph checkpoints; invoice facts and communication_history use Supabase REST. `src/checkpointer.py` provides persistent Postgres in production, with explicit setup under a separate checkpoint role. `GET /history` and useChat polling currently read messages; history prefetch is independent of invoice opening. `agent.update_state` can empty pending approval interrupts, so summary collection must never mutate/sync graph state. Vercel API maxDuration is 60 seconds. Baseline: 437 tests pass, five Postgres tests opt in.

The user's refinement during implementation supersedes automatic generation after each commit: generate once per opening, only for changed communications. No source-write triggers or scheduled workers are needed.

## Goals / Non-Goals

**Goals:** Durable summary per invoice, one explicit opening POST, changed-source detection, safe overlapping opens, failure recovery on later opening, read-only generation and full retained coverage.

**Non-Goals:** Generation on writes/polling/prefetch, background retries, automatic summary chat messages, replacing checkpoint memory, changing existing summary quick actions, external webhooks, or redesigning the chat UI.

## Decisions

### Dedicated summary table

Use invoice_conversation_summaries with invoice_id primary key/FK ON DELETE CASCADE, summary text, source_hash, generated_at, status, target_hash, lease_token, lease_until, retry_after and optional resumable progress. Ownership comes from the current invoice join, so guest migration needs no summary ownership rewrite. RLS enabled; revoke public table and function access; only service_role may use REST RPCs. This keeps generated text and concurrency bookkeeping out of business state and checkpoint interrupts.

### Communication fingerprint and source collection

Read agent.get_state directly and get_communications without syncing graph state. Canonicalize retained HumanMessage/AIMessage content, stable ids/order and draft tool proposals plus stored communication id/type/subject/body/direction/order. Exclude reasoning and tools' private internals. Hash the communication content, not invoice updated_at or wall-clock time: facts-only edits do not justify another AI call. Include latest invoice facts and pending approvals in generation input only when a communication change warrants it. Preserve attribution and avoid representing duplicated reply copies as separate client actions.

A read failure is not an empty transcript. Existing inbound storage keeps 2,000 characters per body; summarize all retained content and document that older omitted text cannot be recovered. Empty transcripts return null/empty without AI.

### Explicit open event separate from reads

useChat sends POST /api/invoices/{id}/summary once per invoice opening after the first real history load. A ref/visit guard prevents rerender/StrictMode effect duplication, and changing invoice ids starts a new visit. Revisiting an invoice sends another POST, but the backend source hash skips unchanged AI work. History polling, query focus refetch and prefetch stay GET-only. New communications during the same visit never trigger another POST. Preserve summary fields in cache updates and render no automatic summary chat message.

GET summary and GET history read saved text and freshness; neither calls AI. POST accepts an empty body only, authorizes using authorize_invoice_access before data access, rate-limits refreshes, and returns 200 for current/empty, 202 for busy/deferred/failed. Response: invoice_id, summary, source_version, generated_at, status and is_stale. History adds summary plus summary_metadata. A summary outage never hides messages or pending approvals.

### Lease and conditional publication

Collect current persisted sources and hash. If source_hash matches a successfully saved row, reuse it immediately. Otherwise acquire a database lease atomically via service-only RPC, including target_hash and a random fencing token. Another active lease returns saved data with refreshing/stale metadata. Do not keep a database transaction open during AI. Recheck the source hash before publication: if a message arrived, release and return stale/deferred without another generation in this visit. Publication is conditional on token and unexpired lease. A replacement worker fences out the expired worker. Failures retain prior text and covered hash, clear lease, set a short retry cooldown and sanitized error code. A later opening may retry; no background scheduler is installed.

### Tool-free bounded AI

Use a dedicated versioned system prompt with the configured Groq provider, explicit request timeout, max retries and output length. Do not call agent.invoke or bind tools. Treat source text as untrusted data; ask for chronology, promises/objections, payment facts and pending versus actual actions. Use ordered bounded chunks and a rolling synthesis for long history, saving progress keyed by target source hash. One opening starts one bounded refresh operation; for long transcripts its model calls process chunks as necessary, without silently dropping early messages. If the budget runs out, save progress and return 202; the next opening resumes that same source. No immediate retries beyond the bounded operation.

## Risks / Trade-offs

- [Summary stays old while invoice remains open] → Deliberate user-requested behavior; metadata marks stale, next opening refreshes.
- [Concurrent opens/StrictMode] → Client visit guard and database lease plus fingerprint reuse.
- [Server stops or provider times out] → Saved summary remains; expiring lease and progress permit a later opening retry.
- [Long transcript exceeds deadline] → Persist chunk progress and defer to next opening rather than truncate or run detached work.
- [Model omission] → Grounding/attribution fixtures plus sampled live quality checks; retained history remains authoritative.

## Migration Plan

1. Work in the clean existing summary worktree; preserve the original workspace.
2. Apply additive table/RPC migration in isolated local Postgres, verify idempotency, RLS, fencing and restart persistence, then deploy preview with schema available.
3. Run backend/frontend suites, lint/build, preview API and opening/polling checks on an owned test invoice; preserve approvals and send no real client mail.
4. Review, pass CI, merge main and deploy the merged SHA to the linked Vercel production project. Verify alias, deployment status, SHA and persistent checkpoint health.
5. Verify production POST/GET/history, reuse after unchanged reopen, refresh after new communication and no generation before reopening. Existing invoices populate lazily when opened; no eager AI backfill.
6. Roll back application code if needed; leave the additive private table/data in place. No source-write triggers or scheduler require rollback.

## User refinement: summary first, full history on demand

The initial and polled request reads the summary with compact invoice/approval metadata, not full messages or communication bodies. Cache this data in React Query for instant reopen. The once-per-opening POST checks persisted sources and only generates for changed communications. Full GET history stays disabled until View conversation history is selected; no hover/focus history prefetch. Current-session chat uses delta-only mutation responses and separate session messages. After history is explicitly requested it can be polled while visible. No source writes trigger generation. Show the saved summary using the existing Markdown renderer, and a clear View conversation history / Hide conversation history control with loading/retry feedback.

## Evaluation-only extension: sequences of updates

Keep production refresh behavior unchanged. Add synthetic append-only sequences to the live summary eval. At each checkpoint send the actual previously generated summary, only not-yet-summarized messages/emails, current invoice facts and pending approvals through the production prompt/model helper. The judge receives the complete accumulated authoritative sources and explicit cumulative expected/forbidden facts, never a generated summary as its source of truth. Expected facts are never sent to the generator.

A sequence passes only when every checkpoint passes grounding, coverage, attribution and safety. Require both the existing single-summary cohort and the sequence cohort independently to meet 85%, and require all expected cases/checkpoints to complete. Preserve actual generated text after a negative or unavailable judge verdict so the judge cannot repair the chain. Generation failures retain the prior summary and leave that input uncovered; the next checkpoint includes the missed delta. Record each step's verdict, errors and input sizes, plus prompt and both fixture hashes. Missing or malformed judgments fail closed.

Cover withdrawn/replaced promises, successive and corrected partial payments, corrected promise dates versus follow-up dates, and an unresolved early objection through eight refreshes. CI must classify the new fixture as a summary change and retain the required aggregate gate. The resulting score measures the proposed incremental input strategy, not a production persistence/cursor implementation.

## Incremental-specific prompt fix

The first complete local experiment passed only 4/8 sequences; the subsequent trusted CI run passed 5/8. Keep both fixture files, expected facts, judge rubric, model families and 85% cohort thresholds unchanged. Revise the shared production prompt to treat earlier_summary as cumulative memory and to carry forward material facts across procedural updates. Require explicit current financial position, preserved correction/withdrawal chronology and objection details, and distinguish approved follow-up dates from client payment promises. Instructions must be general; include no fixture answers or specific test values.

Before committing, run the complete golden set, additional synthetic holdouts, automated suites and independent review. Then require protected GitHub checks before merging and verify the exact merged deployment in production. This release changes the shared prompt and required evaluation coverage; production source collection still rebuilds changed conversations from retained history. No database coverage cursors or incremental retrieval are enabled.
