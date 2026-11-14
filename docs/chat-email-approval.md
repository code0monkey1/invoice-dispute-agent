# Email review cards from chat

On an active invoice, explicit owner requests such as “draft a polite reminder”,
“send the formal demand” or “prepare the final notice” open the existing email
review card. Follow-ups such as “let's send it as a mail”, “show the send card”
or “use the chat email facility” can resolve an email from recent assistant
draft context. An ambiguous reference asks which email is intended. Summary,
research, quoted instructions and client-reply text do not activate this routing.

The API authorizes invoice access first, checks required details/current level,
and places the chosen draft tool in request-local context. The model request
requires that allowed tool; a provider returning no valid required action
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

Local verification passed 664 backend tests (13 environment-dependent skips),
178 frontend tests (6 existing skips), frontend lint/build and strict OpenSpec
validation. Independent review passed 194 focused tests and found no remaining
critical or important issues. An initial live Groq run passed all 14 original
new scenarios; the required GitHub evaluation runs the complete 36-case set,
including four further review regressions, against the final commit.

The [Vercel preview](https://invoice-chaser-470hhod7y-code0monkey1s-projects.vercel.app)
passed 24 checks on owned disposable fixtures: typed/contextual Legal requests,
current figures, conditional previous delivery, explicit resend disclosure,
attachment notes, hidden-history reopening, pending-card reuse and cross-owner
denial. No approval/send endpoint was invoked. Test invoices, communication
fixtures and their checkpoints are removed after verification.

Release requires the protected backend, frontend, golden-set and
summary-golden-set checks before merging; the summary prompt is unchanged.
Production follows the merged main commit and is verified against its canonical
alias, health and owned card fixtures. No schema migration or backfill is needed.
The preceding application commit is `6c34e0d3557f543a00b68bbf89cf963ba3ce1902`
and deployment is `dpl_7Zfb6rygUSqtXwUavMDD8zYxqK33`. For application rollback,
restore that deployment with `vercel rollback dpl_7Zfb6rygUSqtXwUavMDD8zYxqK33`;
retain invoice/communication/checkpoint data. A Vercel rollback disables automatic
domain assignment until a later `vercel promote` restores it.
