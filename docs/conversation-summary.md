# Saved invoice conversation summaries

Opening an invoice requests `POST /api/invoices/{invoice_id}/summary` once when its compact summary/current invoice data loads. Full conversation
history is not fetched on opening. The backend compares all retained chat/email content to
the last successful summary's fingerprint. Unchanged communications reuse the
stored summary without calling AI. Invoice-only edits (for example changing an
amount) do not trigger generation; current invoice facts are used the next time
communications change and a summary is generated.

New chat messages and inbound/outbound email do **not** generate summaries when
they are saved. Polling, history prefetch, focus refetch, and switching to the
trace tab do not generate them either. A message arriving while the invoice is
open waits until the next opening. There is no cron or background generation.
The existing “Give me a summary” quick action remains a separate explicit chat
request; it does not update the saved summary.

## Storage and API

`invoice_conversation_summaries` holds one row per invoice: summary text,
source version, generation timestamp, and private lease/progress/retry fields.
It joins the invoice for ownership, including guest invoices later assigned to
an account. The table has RLS and no public database role access; RPCs are
executable only by the backend service role.

An authenticated owner (or the guest session that owns the invoice) can call:

```http
POST /api/invoices/{invoice_id}/summary
Authorization: Bearer <token>
```

No body is necessary; `{}` is also accepted. Caller-provided summary text,
transcripts, and invoice IDs in the body are rejected. A current result is 200:

```json
{
  "invoice_id": "<storage-invoice-id>",
  "summary": "The client promised payment tomorrow. A reminder draft awaits approval.",
  "source_version": "<sha256-of-retained-communications>",
  "generated_at": "2026-11-14T10:00:00+00:00",
  "status": "current",
  "is_stale": false
}
```

`GET` on that path returns saved data and freshness and **never** invokes AI.
`GET /api/invoices/{invoice_id}/history` includes the same text as `summary`
and the four metadata fields as `summary_metadata`. A missing/unavailable
summary never hides chat messages or waiting approvals. The frontend preserves these fields in the persistent React Query cache and
shows the saved summary immediately on reopening. The summary endpoints also
return compact `state`, `interrupt`, `has_history`, and `has_outbound` metadata
without prior message or email bodies. Full history is fetched only after
**View conversation history** is selected; **Hide conversation history** stops
its polling. Hover/focus prefetch only compact summaries, never full history.
The active chat uses `include_history=false` on chat/escalate/resume requests to
return only the current exchange. Default API responses remain compatible with
existing clients. Summaries are not appended as chat messages.

Statuses:

| Status | Meaning |
| --- | --- |
| `empty` | No retained conversation; null summary, no AI call. |
| `current` | Saved summary covers the current communication fingerprint. |
| `pending` | Communications changed, generation was deferred, or a long history needs a later opening to finish. |
| `refreshing` | Another opening owns a live generation lease. |
| `failed` | A generation attempt failed; saved text is preserved. |
| `unavailable` | Summary storage or a source cannot be read; chat remains usable. |

POST returns 202 for pending, refreshing, failed or unavailable results. The
client does not retry automatically during that visit. A later opening may
retry after the failure's 30-second cooldown or a stopped worker's 50-second
lease. Summary POSTs have a separate limit of ten per owner/IP per minute;
reads are unaffected. New communications during generation make its result
stale/deferred without starting another generation for the same opening.

## Model and retained sources

Generation uses a dedicated tool-free Groq model (`SUMMARY_MODEL`, default
`openai/gpt-oss-20b`; independent of the chasing agent) with a 10-second call timeout, no provider retries and
2,000 output tokens. The refresh operation has a 30-second budget and processes
at most two 24,000-character chunks per opening. Normal conversations use one
model call. Larger transcripts preserve ordered chunk progress and resume on
a later opening, without silently discarding early history. Changed source
content invalidates prior progress. An expiring database lease and fencing token
prevent overlapping workers from overwriting newer results.

The summarizer reads committed human/assistant messages, proposed draft actions,
pending approvals, retained communications, and current invoice facts. It omits
model reasoning and raw tool outputs, labels unverified senders, and distinguishes
proposals from actual outbound send records. It cannot send email, use dispute
tools, write business state, or consume approval interrupts.

Inbound email persistence currently retains only the first **2,000 characters**
of a body. The summary covers all *retained* content; older omitted text cannot
be reconstructed. Full chat history remains authoritative if a model omits or
misstates a detail.

## Rollout and rollback

Apply the final `Conversation summaries` block in `supabase/schema.sql` as the
schema owner using a migration. It only creates an additive table and service
RPCs, and can be reapplied without deleting data. Existing invoice conversations
populate lazily when opened; do not eagerly generate summaries as a backfill.
No new credentials, checkpoint-role grants, triggers or cron jobs are required.

Before release, run backend/frontend suites, lint/build, and the opt-in real
Postgres tests. `TEST_DATABASE_URL` must name a **local throwaway database**;
these integration fixtures create test tables and clear test summary rows.

```bash
TEST_DATABASE_URL='postgresql://user@127.0.0.1:55439/invoice_summary_test?sslmode=disable' \
  python -m pytest tests/test_summary_store_postgres.py tests/test_checkpointer_postgres.py -q
```

Verify preview then production using an owned disposable invoice: first POST
saves, repeated POST reuses the same version/timestamp, a new message alone
does not change the saved version, and the next opening refreshes it. GET and
history agree; a different owner receives 404; a pending draft remains actionable.
Verify `/api/health` reports persistent checkpoints. Confirm Vercel's production
alias points to the tested merge SHA.

If rollback is needed, revert the feature commit and redeploy the preceding
application version. Leave the private additive table and successful summaries
in place; invoices, communications and checkpoints are unaffected.

## Summary golden evaluation

`evals/summary_cases.json` contains 20 synthetic cases covering balances,
promises, disputed amounts, payment changes, missed/withdrawn promises, drafts
versus delivery, unverified senders, injection, speaker attribution and Unicode.
`python -m evals.summary` runs the production summary prompt and asks a separate
model family to judge grounding, coverage, attribution and safety. Each criterion
must score at least 4/5 and the judge must explicitly mark the case positive.
At least **85% of all cases** must pass; missing, invalid and provider-error
judgments fail closed. Incomplete runs never pass. Model-family validation
prevents GPT-OSS variants from judging each other.

The summary CI job uses a different-family Qwen judge and uploads a JSON/Markdown
scorecard. It is separate from the existing chasing-agent golden set: each runs
when its own prompts, model code or fixtures change. No unrelated agent eval
failure is treated as summary quality evidence. GPT-OSS summary generation uses
low reasoning effort within its output budget; see [Groq's reasoning documentation](https://console.groq.com/docs/reasoning).

The required `summary-golden-set` gate always runs. It fails if change
classification fails or a relevant evaluation is skipped/cancelled/failed;
fork code never receives provider secrets and must be evaluated on a trusted
maintainer branch before merge. The protected main branch requires this gate
alongside backend/frontend and chasing-agent gates, including admin merges.
These 20 judged fixtures cover short histories; long-history carry-forward and
resume mechanics are separately covered by deterministic service tests.

### Sequences of updates

The same command also runs eight synthetic sequences (31 checkpoints) from
`evals/summary_sequences.json`: withdrawn/replaced promises, successive and
corrected partial payments, corrected payment dates, follow-up dates distinct
from promises, and an older unresolved objection through eight refreshes.

At every checkpoint, generation receives the actual previous generated summary,
only new messages/emails, current invoice facts and pending approvals. The
independent judge receives the complete accumulated authoritative history and
cumulative expected/forbidden facts. Expected facts never enter the generator's
input. A negative or missing judge verdict cannot repair the next summary;
generation failures retain the prior summary and include the uncovered delta
in the next attempt.

A sequence is positive only when **every checkpoint** is positive. Single
summaries, complete sequences and individual sequence checkpoints must each
reach **85%**, with all expected evaluations present. Strong single-summary
scores cannot hide sequence failures. Reports include every checkpoint,
candidate text, input character counts, verdict/error, model identities and
SHA-256 hashes of the prompt and both fixture files. Interrupted runs fail.
The existing required GitHub `summary-golden-set` check runs both cohorts,
including when only the new sequence fixture changes.

This is an evaluation of the proposed incremental input strategy. Production
refreshes still rebuild from retained history when communications change;
no production coverage cursors, persistence changes or incremental refreshes
are introduced by this evaluation extension.

### Prompt support for cumulative memory

The shared prompt treats `earlier_summary` as retained conversation memory and
merges new records into it. It preserves current financial position and material
payment corrections, original/corrected/withdrawn commitments, conditional
promises, and the specific reason/status of earlier objections. Follow-up dates
remain distinct from client payment promises. It also preserves who said what,
including unverified claims and explicit business/legal confirmations, instead
of replacing the conversation with empty financial headings.

This improves the instructions used for chunk carry-forward and tested
incremental inputs. Production still collects retained history when changed
communications warrant a refresh. Backend coverage checkpoints and delta-only
source retrieval require a separate implementation; changing the prompt alone
does not reduce production history retrieval or enable that optimization.
