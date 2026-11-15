# Proposal

## Why

Typed requests to prepare/send an invoice email can return copy-and-paste text instead of the review-and-send card. Read-only production traces confirm four Legal-level requests offered `draft_final_notice` but produced zero tool calls, leaving the frontend without an approval interrupt.

## What Changes

- Route explicit, trusted owner email-preparation requests through the appropriate existing draft tool and human-approval flow. Resolve supported follow-ups such as “send it” from recent email context; ambiguous requests receive clarification.
- Require the selected allowed draft tool for an eligible request instead of relying on an optional model tool call. Preserve existing pending drafts and show a clear recoverable error if a draft cannot be prepared.
- Check successful outbound records for “if not already sent”; report an existing delivery accurately. A new send/resend request produces an approval card, never an automatic email.
- Use current invoice figures in the preview and truthful attachment information. The referenced invoice has no uploaded file; the app must not claim a PDF is attached. Extending attachment delivery beyond currently supported email types is outside this change.
- Add multi-turn regressions for the observed copy/paste loop, card propagation through compact chat/history, approval-only sending, duplicate conditions, trust boundaries and missing attachments. Include required structural golden checks that cannot be hidden by aggregate scores.

## Capabilities

### New Capabilities

- `chat-email-approval`: Owner chat requests reliably prepare existing invoice email drafts for review, with accurate delivery/attachment state and explicit approval before sending.

### Modified Capabilities

None. Durable conversation memory, summary-first history and existing quick-action requirements are preserved.

## Impact

- Request-scoped context and tool selection in `api/index.py`, `src/state.py` and `src/middleware/dynamic_tools.py`; email instructions in the escalation prompts.
- Existing `extract_interrupt`/draft preview and `DraftApproval` contract, with additive attachment-status information only where required. No new email composer, public send endpoint or database schema.
- Agent/API/frontend tests and the chasing-agent golden harness/cases, including realistic prior prose-only replies and current invoice figures.
- No live email sending or production writes during proposal creation. Implementation, CI, preview and production verification are separate apply tasks, using synthetic recipients and fake Gmail for automated tests.
