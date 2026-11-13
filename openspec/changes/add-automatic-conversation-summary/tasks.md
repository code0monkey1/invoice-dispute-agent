# Tasks

## 1. Storage and concurrency

- [x] 1.1 Reuse the clean feat/chat-summary-on-open worktree based on origin/main; verify original local changes remain untouched and baseline backend tests pass.
- [x] 1.2 Write failing storage tests, then implement the private per-invoice summary table, service-only claim/publish/progress/failure RPCs and database helpers. Verify real local Postgres tests cover persistence, uniqueness, RLS, expired leases, concurrent opens, fenced stale publication and idempotent migration.

## 2. Summary service

- [ ] 2.1 Write failing tests then implement read-only canonical conversation collection and communication hashing. Verify changed chat/email content invalidates, unchanged/facts-only updates reuse, empty history skips AI and source failures are not treated as empty.
- [ ] 2.2 Write failing tests then implement a separate tool-free summarizer, bounded long-history chunking/resumable progress and lease-guarded publication. Verify chronology, promises, objections, draft/unverified attribution, early/late facts, prompt injection, timeout preservation, duplicate opens and communication arriving mid-generation.
- [ ] 2.3 Document source scope, statuses, call budgets and the 2,000-character retained inbound body limit; verify examples against service tests.

## 3. API and history

- [ ] 3.1 Write failing API tests then add owner-authorized POST/GET summary endpoints and nullable summary/summary_metadata to every successful history path. Verify guest and signed-in access, ownership transfer, cross-invoice denial, malformed ids, empty-body validation, rate limits, 200/202 behavior, read-only GET, unavailable store and pending approval preservation.
- [ ] 3.2 Document the API and on-open-only behavior; verify chat/create/resume/escalate/inbound and history reads never invoke the summarizer, and summary failure never changes action outcomes or sends email.

## 4. Frontend invoice-open trigger

- [ ] 4.1 Write failing hook tests then request summary once per invoice opening after real history loads, with StrictMode/visit protection. Verify unchanged reopen relies on backend reuse, switching invoices refreshes the correct id, polling/prefetch/focus/chat mutations do not regenerate, and summary fields survive cache updates and failed requests.
- [ ] 4.2 Add API/types and expose saved summary through useChat without inserting a chat message. Verify frontend tests, lint and build and document no generation while an invoice remains open.

## 5. Verification and release

- [ ] 5.1 Run the full backend suite, real Postgres summary/checkpoint integration tests, frontend suite, lint and build; verify all pass and record existing warnings separately.
- [ ] 5.2 Review the complete diff and get one fresh whole-branch review; address significant findings with regression tests and validate OpenSpec strictly. Verify no unrelated edits or eager-generation wiring remain.
- [ ] 5.3 Deploy preview and verify owned test invoice POST/GET/history agreement, cumulative content, unchanged reopen reuse, changed communication refresh on next opening, pending approval preservation and recoverable failure; record URL and results.
- [ ] 5.4 Open/update the focused PR, pass CI, merge main and push; verify the tested commits are on origin/main and record PR URL/merge SHA.
- [ ] 5.5 Apply the additive production migration, deploy merged SHA to Vercel production and verify alias, ready status, deployed SHA, persistent checkpoints and summary table readiness. Record deployment ID/URL.
- [ ] 5.6 Verify owned production invoice lazy summary creation, unchanged reuse, later-message refresh only on reopening, restart persistence and cross-owner denial without sending real email; record evidence and rollback instructions.

## Workflow follow-up

- Sync/archive after implementation and production verification are complete.
