# Tasks

## 1. Isolation and regression evidence

- [x] 1.1 Create a clean worktree from current main, copy only this scaffolded change into it and preserve the original workspace edits. Verify Git status and record the backend/frontend baseline results before implementation.
- [x] 1.2 Add failing deterministic regressions using the real graph/API and sanitized prose-only history for the observed Legal follow-ups. Verify the current code lacks the expected approval card, add the already-delivered conditional case separately, and keep real production invoice data read-only.

## 2. Owner intent and required draft routing

- [x] 2.1 Implement bounded owner email-intent/context resolution with required-detail, ambiguity, informational-question and quoted/client-text guards. Verify positive direct/follow-up phrases and negative cases with unit tests; document supported behavior and clarification rules.
- [x] 2.2 Carry the resolved intent only in the current chat context, validate the existing level/tool allowlist and bind the selected draft tool as required. Update escalation email instructions. Verify the provider-bound request, real graph approval interrupt, missing-action/provider-error behavior and absence of inherited forcing on resume/inbound/summary paths with focused tests.
- [x] 2.3 Read and reuse pending cards before state synchronization; check successful outbound records for conditional requests and disclose earlier delivery on explicit new drafts/resends. Verify no duplicate proposal, accurate conditional no-op, failure to verify delivery, paid/above-level restrictions and no interrupt-clearing writes. Document these decisions.

## 3. Card and API integration

- [x] 3.1 Centralize card decoration using current invoice figures, recipient and truthful previous-delivery/attachment notes across chat, compact data and explicit history. Verify authorized owner/guest access, cross-owner denial, existing response compatibility, no private storage paths and missing/unsupported attachment behavior with API tests; document additive metadata.
- [x] 3.2 Display optional notes outside the editable subject/body in the existing DraftApproval component. Verify card visibility with history hidden, edit/approve/reject, polling/reopen/navigation, missing attachments and recoverable errors using component/hook tests; run lint and document the user-visible flow without adding a new composer.

## 4. Multi-turn golden regression gate

- [x] 4.1 Extend the golden case loader/harness with optional prior conversation and successful-delivery fixtures while preserving existing defaults. Verify fixture validation, actual API/graph replay, zero pre-approval outbox entries and refusal to construct a real Gmail client with deterministic tests.
- [x] 4.2 Add a hard structural gate for cases expecting email approval: correct draft interrupt and no delivery before approval must pass independently of aggregate quality. Verify prose-only, missing/error/skipped cases cannot pass; preserve existing thresholds and required GitHub gate behavior with runner/workflow regression tests.
- [x] 4.3 Add direct and contextual email cases across supported levels, including the observed Legal phrases after prose-only replies, conditional already-sent behavior, explicit resend and trust-boundary negatives. Run the isolated live Groq golden set, require every critical card assertion to pass, preserve failed/provider-error results and document exact tools/cards/outbox evidence without real email sending.

## 5. Integrated verification and release

- [x] 5.1 Run full backend/frontend suites, lint/build and strict OpenSpec validation, review the actual diff and obtain an independent review. Verify no unrelated changes, approval bypass, fictitious card parsing or summary/history regressions remain, and record results and existing skips/warnings.
- [x] 5.2 Deploy preview and verify typed Legal draft preparation, contextual follow-up, pending-card reuse and reopening with history hidden on owned disposable fixtures. Verify conditional/prior-delivery and attachment notes, and leave live approval/send untriggered; record the preview URL and observations.
- [x] 5.3 Open a focused PR, require successful protected CI, merge and deploy the merged SHA through the established production flow. Verify alias/SHA/health, owned card creation/reuse and cross-owner denial without approving real delivery or changing the referenced real invoice; record release evidence and application rollback instructions.

## Workflow follow-up

- Sync and archive this change after implementation and release verification are complete.
