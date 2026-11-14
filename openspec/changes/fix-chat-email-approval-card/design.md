# Design

## Context

See proposal.md for motivation. Read-only inspection on 2026-11-14 found:

- Four production chat runs between 08:52 and 08:55 UTC used `openai/gpt-oss-120b` at level 3. Every model call was offered `draft_final_notice`; every `tool_calls` list was empty. No tool-gate refusal or approval interrupt was recorded for those runs.
- `src/agent.py` already registers that tool and requires human approval. `api/index.py` exposes an interrupt only when the graph returns one; `ChatPanel` already renders `DraftApproval` for that tool. The observed break occurs before card creation.
- The referenced invoice is active at Legal level, has a successful outbound Final Notice from November 13, and has no stored invoice file. The quoted reply's payment figures also differ from current stored figures. Existing successful outbound records must drive conditional-send decisions.
- Attachment sending currently calls `build_invoice_attachment` only for `draft_invoice_delivery_email`. Other draft types cannot honestly promise an attachment merely because their prose mentions one.
- The installed LangChain request supports `tool_choice`; the installed Groq binding supports named-function selection. [Groq's API reference](https://console.groq.com/docs/api-reference) documents requiring a specific function. Provider behavior still needs verification through the isolated live regression harness.
- Existing approval tests cover sending after an interrupt, while the Legal golden case starts with a fresh “Draft the final notice” request. It does not reproduce repeated follow-ups after assistant-written copy/paste instructions. The aggregate tool-accuracy gate permits some misses.

## Goals / Non-Goals

**Goals:** Make a supported explicit owner request reach the existing approval boundary; recover from the observed prose-only history; preserve current invoice truth, pending cards and owner trust boundaries; prove the card contract directly.

**Non-Goals:** Sending the referenced invoice's real email during testing; automatic approval from “send it”; a new composer or send endpoint; bypassing escalation; PDF generation or expanding attachment delivery to additional email types; rewriting legal templates; changing saved-summary generation or history-loading behavior.

## Decisions

### 1. Make eligible draft preparation request-scoped and mandatory

At the authorized `/api/chat` boundary, resolve clear owner actions from the latest message and bounded recent email context. Recognize supported preparation/send phrases and contextual corrections such as requesting the chat email facility after a prose-only draft. An informational question or a quoted command does not qualify. If a pronoun has no identifiable email referent, ask for clarification.

Carry the resolved draft type in per-request `FreelancerContext`, not persisted graph/business state or a caller-supplied tool-name field. Validate required invoice/recipient details, `tools_for_level` and settled-invoice rules; ask for missing information before forcing a draft. In `dynamic_tool_middleware`, retain the current allowed tools and set named `tool_choice` for the eligible draft request. Update escalation prompts to explain the actual card workflow and forbid imaginary copy/paste composers.

This uses the existing graph's HumanInTheLoopMiddleware to stage the proposal. It does not execute tools directly, synthesize an interrupt from prose, or bypass the existing tool gate. Resume/inbound/summary requests do not inherit the preparation intent. Provider failure or a missing/invalid required action yields a bounded preparation error using the existing API error display; do not loop until a card appears.

**Alternatives:** Prompt-only instructions leave this observed action optional. Parsing assistant Markdown into an email card invents an approval state the graph cannot safely resume. A second generic intent-classification model adds latency and another failure surface; use bounded supported owner actions with conservative clarification instead.

### 2. Reuse pending actions and evaluate conditional delivery first

Read any pending graph interrupt before state synchronization can clear it. Reuse the existing same-type card through shared preview/metadata helpers, using current invoice facts in a local preview dictionary without mutating the graph. A conflicting pending draft receives clarification instead of replacement.

For “if not already sent”, inspect successful outbound communications for the selected type. Return the recorded delivery when present; an assistant claim, failed send or unsent draft is insufficient. If this read fails, report that delivery could not be verified rather than assuming unsent. A clearly requested new draft/resend remains eligible but shows the prior-delivery information outside the editable body. Existing approval and recent-send deduplication remain authoritative at delivery time.

### 3. Keep one card and one approved-send path

Keep the existing draft tool signatures and template previews unless a regression proves a necessary change. Preview current amount/paid/balance and the invoice's authorized recipient. The card remains editable through `DraftApproval`; `send_approved_draft` and `/resume` remain the only delivery path. Chat requests alone cannot approve, and research questions retain their existing tools.

Use shared interrupt decoration for chat, compact summary metadata and history. Add optional previous-delivery/attachment notes if needed, updating frontend types and the card without changing existing required fields. Missing files or unsupported attachment delivery must be visible outside subject/body, so the note is never accidentally emailed. Do not silently add new attachment behavior or claim an attachment is included.

### 4. Test the missing handoff, not only the sender

Use the real graph with scripted models for deterministic routing, trust-boundary, pending-card and API tests. Capture the provider-bound tool choice; a fake model returning ordinary prose must expose a bounded failure, not a fabricated card. Verify no fake-outbox entry exists before approval, and approve/reject through the existing endpoint to check the actual send contract.

Extend the golden case/harness with optional sanitized prior conversation and prior successful-delivery fixtures, retaining default behavior for existing cases. Replay the original follow-up phrases after prose-only assistant replies on synthetic unsent invoices. Separately test conditional already-sent behavior and explicit resends. Enforce correct interrupts for expected-email-approval cases as a hard structural gate, independent of average tool accuracy or tone scores. Keep existing quality thresholds intact; use fake Gmail and canned legal search even during live Groq evaluation.

## Risks / Trade-offs

- [False intent recognition] -> Restrict mandatory routing to clear current owner actions, resolve supported recent references and clarify genuine ambiguity; test summary/research/quoted-text negatives.
- [Draft repeated after approval] -> Keep intent in the chat request context only, never reconstruct it automatically during resume or from old assistant messages.
- [Pending interrupt erased] -> Inspect before sync and reuse read-only preview construction; test reload/polling and concurrent repeated requests.
- [Provider rejects a required call] -> Verify the current production model in live isolated cases and fail explicitly within existing request limits; never fall back to fake composer instructions.
- [Attachment expectation exceeds current capability] -> Show actual missing/unsupported state before approval. Attachment expansion requires a separate scoped change.
- [Provider quotas or a fresh-context-only test masks failure] -> Preserve failed/error evaluations and require multi-turn card assertions; do not lower gates or test against the real recipient.

## Migration Plan

Implement in an isolated worktree preserving current local edits. No database migration or conversation backfill is planned. Run deterministic backend/frontend suites and the isolated live golden set, review the diff, then verify preview card creation/reopening on an owned disposable invoice without approving real delivery. After protected CI succeeds, merge and deploy the merged SHA using the established release flow. Verify production alias/SHA, owned card creation/reuse and access control, leaving the referenced real invoice untouched. Roll back by redeploying the preceding application commit; retain invoice, communication and checkpoint data.
