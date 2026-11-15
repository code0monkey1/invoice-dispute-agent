# Verification status

Implementation is complete in `fix/chat-email-approval-card` / PR #31. Release
verification is pending; do not merge or deploy until
the complete required golden evaluation passes.

## Deterministic evidence

- Backend: 761 passed, 13 environment-dependent skips.
- Frontend: 178 passed, 6 existing skips; lint and production build passed.
- Strict OpenSpec validation and Git diff checks passed.
- Independent reviews covered routing, authorization, pending-card persistence,
  attachment/financial truth, request-scoped restrictions and owner-mode prompts.
- The final quota-abort regression reproduces 95.45% tool accuracy after all
  required cards passed, with an incomplete non-card cohort. The explicit abort
  flag and retained error diagnostic now force failure in that case.

## Live evidence and remaining work

An initial isolated live run passed all 14 original added scenarios. The
[first full GitHub evaluation](https://github.com/code0monkey1/invoice-dispute-agent/actions/runs/43600531478)
passed 31/36 cases and correctly blocked the merge. Its failed scorecard remains
in that run's `eval-results` artifact.

The follow-up changes keep all 36 cases and thresholds unchanged. They prevent
informational turns and completed approvals from proposing emails, separate
owner assistance from legal client-letter prompts, and make missing attachments
nonblocking while retaining truthful card notes. Targeted reruns verified the
card-routing repairs. With the alternate credential, all five previously failing
scenarios passed unchanged: judge mean 4.6/5 and zero pre-approval deliveries.
Final full live quality verification is still required.

The [replacement-key full CI run](https://github.com/code0monkey1/invoice-dispute-agent/actions/runs/43628514018)
completed all 36 cases: 34 passed, with 100% required email cards, approval checks
and tone rules. It correctly failed the per-level regression gate because a
client reply attempted a recipient edit; a separate payment report also missed
its review proposal. The follow-up removes ungated mutation tools from untrusted
provider requests and clarifies factual payment reports as owner-reviewed
proposals. Both failed cases and the adversarial payment-command control then
passed unchanged (3/3). Existing owner behavior and all thresholds are retained.

The [subsequent full run](https://github.com/code0monkey1/invoice-dispute-agent/actions/runs/43630776945)
passed 34/36 but correctly blocked a missing Friendly email card. Provider traces
showed `check_invoice_status` conflicting with required `draft_polite_reminder`:
the advisory prompt still said to check status first. The narrow repair exposes
only the validated selected draft tool, disables parallel calls and uses an email
preparation prompt. A real graph/API regression reproduces the competing tool
choice at Friendly and Legal levels; both now return the correct card without
sending. The unchanged live reminder case then produced real cards twice (2/2).
Stage progression and the per-level allowlists remain unchanged. A complete CI
run on this final repair is still required.

The [selected-tool CI run](https://github.com/code0monkey1/invoice-dispute-agent/actions/runs/43635315545)
stopped at 20/36 when the replacement organization exhausted its daily token
quota; it correctly failed closed. Before that, contextual invoice delivery
returned a provider tool-use error and two client-reply answers copied a name
placeholder. Local tracing reproduced the delivery error: the model asked for
approval before calling the tool that creates the approval card. The delivery
tool description also supplied a literal placeholder as a negative example.
The final wording makes preparation explicitly non-sending and before approval,
and removes that copyable example. No stage, payment or threshold rules changed.
Both new deterministic prompt regressions failed before this repair and now pass.
The same three live cases then passed unchanged, with judge mean 5/5 and no
pre-approval deliveries. Another supplied account with fresh capacity was validated
and configured locally, in GitHub and in Vercel production on November 15 IST.
The complete protected cohort remains required.

The local Groq organization reached its 200,000-token daily allowance for
`openai/gpt-oss-120b`. The user supplied a replacement credential. It was validated
for the production model and different judge model, saved locally, and configured
in the repository's `GROQ_API_KEY` secret and linked Vercel production Secret on
2026-11-14 at 18:34 UTC. Credential values were not echoed or placed in command
arguments. The [old-organization CI rerun](https://github.com/code0monkey1/invoice-dispute-agent/actions/runs/43626578276)
stopped after 15/36 cases at its daily quota and correctly failed closed.

The initial preview passed 24 checks. The refreshed preview at
`https://invoice-chaser-jqakb5z3k-code0monkey1s-projects.vercel.app` passed all 25
checks, including an informational answer without a draft. All three disposable
invoices, communication fixtures and their checkpoints were removed; no approval
or send endpoint was invoked.
The subsequent inbound-only change is covered by the targeted live cases and
15 graph regressions, including unchanged owner tool availability.

After the full gate passes, merge only the tested
head, verify production alias/merged SHA/health and owned disposable card flows,
then complete tasks 4.3 and 5.3. No real email approval/send is authorized by
this verification. The referenced real invoice has remained read-only.

## Isolation

Worktree: `/Users/chiranjeev/Documents/invoice-dispute-agent-email-card`.
Original workspace edits are preserved; fingerprints for its `.gitignore`,
existing eval outputs and earlier summary task file remain unchanged. No database
migration is required. The saved-summary prompt and its 85% gate are unchanged.
