# Release verification

All 13 implementation and release tasks are complete. [PR #31](https://github.com/code0monkey1/invoice-dispute-agent/pull/31)
merged on November 15, 2026 as `2008a7c886bf6f29492f0cfa79dcf1261fa94247`.
The exact tested feature head was `372e72f439a78924a872f67c077a64f960ac56bd`;
its application files match the merge commit.

## Deterministic evidence

- Local backend: 761 passed, 13 environment-dependent skips.
- CI backend: 751 passed, 23 skips (static frontend assets are absent in that job).
- Frontend: 178 passed, 6 existing skips; lint and production build passed.
- Strict OpenSpec validation and Git diff checks passed.
- Independent reviews covered routing, authorization, pending-card persistence,
  attachment/financial truth, request-scoped restrictions, owner assistance,
  inbound trust boundaries and fail-closed evaluation. The final two reviews
  passed 64 and 35 focused tests with no critical or important findings.
- The competing-status regression passes at Friendly and Legal levels, retaining
  the ability to prepare an earlier-stage reminder without changing escalation.
- Both final prompt regressions failed before repair and pass afterward:
  card preparation must precede approval, and public tool instructions must not
  demonstrate name placeholders that the model can copy.

## Live evaluation

The [protected final run](https://github.com/code0monkey1/invoice-dispute-agent/actions/runs/43678832470)
completed the unchanged 36-case cohort: 35/36 passed (97.2%), tool accuracy 97%,
100% approval and tone checks, every expected email card correct, zero deliveries
before approval, judge mean 4.71/5. Agent `openai/gpt-oss-120b` was judged by the
separate `openai/gpt-oss-20b` model. The remaining `l3-client-pays` miss was a
payment-review proposal, within the existing noncritical tolerance; it did not
violate the email card or approval gate. No fixtures or quality thresholds were
weakened. Backend/frontend and both required golden gate checks passed before merge.
The summary prompt and its 85% gate remain unchanged.

Earlier failed reports remain in GitHub artifacts:

- [43600531478](https://github.com/code0monkey1/invoice-dispute-agent/actions/runs/43600531478):
  31/36. Fixed attachment-related refusal, informational turns becoming drafts,
  owner-answer formatting and redrafting after completed approval.
- [43628514018](https://github.com/code0monkey1/invoice-dispute-agent/actions/runs/43628514018):
  34/36. Removed ungated recipient/escalation mutations from untrusted provider
  requests, retaining owner tool availability and existing payment approvals.
- [43630776945](https://github.com/code0monkey1/invoice-dispute-agent/actions/runs/43630776945):
  34/36. Provider tracing identified advisory status-check instructions conflicting
  with required draft selection. Selected turns now expose only that validated
  draft tool, disable parallel calls and use a preparation-specific prompt.
- [43635315545](https://github.com/code0monkey1/invoice-dispute-agent/actions/runs/43635315545):
  stopped at 20/36 at the replacement organization's daily quota. A contextual
  delivery request also asked for approval before creating the card, and two
  replies copied a literal name placeholder from the delivery tool description.
  The final wording corrects this order and removes the example. Those same three
  cases passed unchanged afterward, judge mean 5/5.
- [43626578276](https://github.com/code0monkey1/invoice-dispute-agent/actions/runs/43626578276):
  earlier daily-quota abort at 15/36. Quota-aborted and missing-card reports fail
  closed even if partial aggregate scores would otherwise pass.

The user's supplied alternate credentials were validated without printing values,
saved locally with mode 0600, and configured in GitHub and Vercel production.
The final cohort used an account with fresh capacity. All golden Gmail delivery
went to the fake outbox; constructing a real Gmail client is refused by the harness.

## Deployed verification

The broad refreshed preview passed 25 checks. The [final preview](https://invoice-chaser-6rcrqfa8l-code0monkey1s-projects.vercel.app)
passed all 13 focused checks on the tested revision.

Production deployment `dpl_CPR2FcDeo3ihGiGWUEQ5VsR1iD2K` is READY at
`invoice-chaser-oamrw0sc0-code0monkey1s-projects.vercel.app`.
The canonical alias [invoice-chaser-chi.vercel.app](https://invoice-chaser-chi.vercel.app)
was verified against that deployment and functional merge SHA. All 13 production
checks passed: healthy PostgreSQL checkpointer, typed Legal review card, current
figures, missing-attachment disclosure, hidden-history reopening, pending reuse,
explicit history, cross-owner denial, zero outbound delivery, truthful conditional
previous delivery and persistence without a duplicate card. Both disposable
invoices/communications/checkpoints were removed. No approval/send endpoint was
invoked and the referenced real invoice remained read-only. The deployment's
error/fatal log scan returned zero records.

## Isolation and rollback

Work occurred in `/Users/chiranjeev/Documents/invoice-dispute-agent-email-card`.
Original user-file fingerprints remained unchanged. No database migration or
conversation backfill was required. For rollback, redeploy preceding application
commit `6c34e0d3557f543a00b68bbf89cf963ba3ce1902` from a clean checkout with current
production secrets; retain invoice/communication/checkpoint data. Reusing the old
deployment would restore its obsolete credential snapshot.
