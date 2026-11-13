# Proposal

## Why

InvoiceChaser has an on-demand summary prompt but no persisted cumulative summary. A freelancer opening an invoice should get a catch-up summary once, with an AI call only when saved chat or email communications changed since its last successful summary.

## What Changes

- Add owner-authorized POST/GET `/api/invoices/{invoice_id}/summary`.
- Request refresh once per invoice opening. Reuse the stored summary if the communication fingerprint is unchanged; polling, prefetching, incoming messages, and chat mutations do not generate summaries.
- Store one row per invoice in `invoice_conversation_summaries`, with summary text, source version, generation time, and short-lived concurrency/retry state. Include `summary` and freshness metadata in history.
- Summarize all retained conversation and communications, distinguish drafts from sent emails and unverified senders, preserve pending approvals, and bound model calls.
- Test, review, merge to `main`, and verify Vercel production deployment.

- Show the locally cached summary first; retrieve full conversation history only when the owner chooses View conversation history. Summary responses provide compact invoice/approval metadata; active chat can request delta-only responses.

## Capabilities

### New Capabilities

- `conversation-summary`: Private durable cumulative summaries, generated once on invoice open only when persisted communication content changed; read/refresh contracts, freshness, concurrency and failures.

### Modified Capabilities

None. Existing quick actions and durable agent memory remain unchanged.

## Impact

- `api/index.py`, a new tool-free summary service, database helpers and an additive Supabase table/RPC migration.
- Frontend API/types/cache and invoice-open hook; no model calls in history reads, polling, prefetching, message writes, or inbound webhooks.
- Service/API/frontend and real Postgres concurrency tests, documentation, preview and production verification.
- The existing `feat/chat-summary-on-open` is clean at the same `4cb07e2` as main and can be reused. No unfinished summary API was found on inspected branches/PRs.
- User refinement during apply: opening-triggered refresh replaces the original post-commit generation plan. No invalidation triggers, scheduled drain, background generation, or eager backfill is needed.
