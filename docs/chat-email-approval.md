# Email review cards from chat

On an active invoice, explicit owner requests such as “draft a polite reminder”,
“send the formal demand” or “prepare the final notice” open the existing email
review card. Follow-ups such as “let's send it as a mail”, “show the send card”
or “use the chat email facility” can resolve an email from recent assistant
draft context. An ambiguous reference asks which email is intended. Summary,
research, quoted instructions and client-reply text do not activate this routing.

The API authorizes invoice access first, checks required details/current level,
and places the chosen draft tool in request-local context. The model request
offers only that allowed draft tool and requires one call, using a preparation
prompt instead of the advisory prompt's status-check instructions. A provider
returning no valid required action
receives a bounded 503 preparation error, rather than a fictitious composer.
The normal tool gate and human-approval middleware still apply. The intent is
not saved in graph state and cannot force another draft during approval/resume.

Existing pending approvals are read before synchronization and reused without
clearing their interrupts. “If not already sent” checks successful outbound
records for that email type and reports a recorded delivery without preparing
a duplicate. Failed sends or earlier assistant claims do not count as delivery.
An explicit new draft/resend still needs approval and displays earlier-delivery
information. Failure to verify a conditional delivery returns a retryable error.

## Card and API contract

The existing `interrupt` fields `tool`, `args` and `description` remain intact.
Email cards can additionally contain `notes: string[]`, for earlier deliveries
and actual invoice attachment availability. The same card builder is used for
chat, compact summary data and explicit history. Notes are displayed outside
subject/body and never become part of the approved email text. Current stored
invoice amounts and recipient override outdated prose or graph facts in previews.
Invoice delivery uses the same factual base draft in its preview and tool output,
including total, paid and remaining amounts. Model-written financial or attachment
claims cannot override it; the owner can still edit the subject and body on the
review card. Missing or malformed required tool arguments return a preparation
error before an approval card can be created.

No uploaded invoice file means no invoice attachment. Only the existing invoice
delivery flow attaches a stored invoice; other email types disclose that the
uploaded invoice is not attached. This fix does not generate PDFs or expand
attachment support. Existing `/resume` approval, Gmail connection checks, send
deduplication and truthful success/failure reporting remain the delivery path.
Chat words alone never approve or send anything.

## Regression checks

The golden harness supports optional sanitized conversation history and past
successful-delivery fixtures. It records actual outbox size before approval.
Every expected email card must match its tool and have zero pre-approval sends;
missing evidence/results and provider errors fail the structural card gate,
independently of aggregate tool accuracy or tone. Existing thresholds remain.
Automated and live-model golden runs use a fake Gmail outbox and canned legal
search; they cannot construct a real Gmail client. Preview/production smoke
checks prepare cards on owned disposable invoices without approving delivery.

## Verification and rollout

Released on November 15, 2026 through [PR #31](https://github.com/code0monkey1/invoice-dispute-agent/pull/31),
functional merge `2008a7c886bf6f29492f0cfa79dcf1261fa94247`.

- Local backend: 761 passed, 13 environment-dependent skips. Frontend: 178 passed,
  6 existing skips; lint/build and strict OpenSpec validation passed. Independent
  reviews found no critical or important issues.
- [Required live CI](https://github.com/code0monkey1/invoice-dispute-agent/actions/runs/43678832470):
  35/36 cases passed (97.2%), every expected email card correct, 100% approval and
  tone checks, zero pre-approval deliveries, judge mean 4.71/5. The remaining
  Legal payment-report proposal miss is within the unchanged noncritical tolerance.
  The agent was `openai/gpt-oss-120b`; the separate judge was `openai/gpt-oss-20b`.
- [Final preview](https://invoice-chaser-6rcrqfa8l-code0monkey1s-projects.vercel.app):
  13 checks passed on the exact tested revision. Earlier broad preview passed 25
  checks, including contextual requests and informational answers.
- [Production](https://invoice-chaser-chi.vercel.app): canonical alias and merged
  SHA verified; PostgreSQL checkpointer healthy; all 13 card/access checks passed.
  Both disposable invoices and their communication/checkpoint fixtures were removed.
  The deployment error/fatal log scan returned zero records. No real email approval
  or send endpoint was invoked, and the referenced real invoice remained read-only.

The repairs remove conflicting advisory status checks from selected preparation,
make card creation explicitly precede delivery approval, and remove copyable
placeholders from tool instructions. The original 36 cases, quality thresholds,
stage progression and level allowlists are unchanged. Protected backend, frontend,
golden-set and summary-golden-set checks passed before merge; the summary prompt
and its 85% gate are unchanged. No schema migration or backfill is needed.

The preceding application commit is `6c34e0d3557f543a00b68bbf89cf963ba3ce1902`.
For application rollback, redeploy that commit from a clean checkout with the
current production environment, retaining invoice/communication/checkpoint data.
Reusing the old deployment would also restore its obsolete Groq credential snapshot.
