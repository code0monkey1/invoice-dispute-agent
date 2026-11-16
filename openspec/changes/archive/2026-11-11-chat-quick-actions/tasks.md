# Tasks

Tests go in `frontend/src/components/__tests__/ChatPanel.test.tsx`, using the existing `mocks.hookState` / `renderChat()` setup. The default `beforeEach` state is a first-open invoice (no messages), so quick-action tests must seed `messages` (or an outbound communication) to get past first open. Write each test first, watch it fail, then implement it.

## 1. Bar visibility

- [x] 1.1 Add failing tests in a new `describe('ChatPanel quick actions')`: the bar shows its three buttons once there's an earlier message; it is hidden on first open (default state); it is hidden when `status: 'paid'`. Verify with `cd frontend && npx vitest run src/components/__tests__/ChatPanel.test.tsx` (all three fail for the right reason).
- [x] 1.2 Render the quick-action bar above the input row in `ChatPanel.tsx`, shown when `agentState && !showFirstOpenActions && status !== 'paid'`, using pill buttons in a scrollable row as described in design.md §5. Verify that the 1.1 tests pass.

## 2. Summary action

- [x] 2.1 Add a failing test: clicking "Give me a summary" calls `sendMessage` once with the summary prompt (assert it contains "summary" and "invoice") and does not call `escalate`/`settle`. Verify it fails.
- [x] 2.2 Add the `SUMMARY_PROMPT` constant next to `INVOICE_DELIVERY_PROMPT` with the text from design.md §3, and wire up the button. Verify the 2.1 test passes.

## 3. Next escalation email action

- [x] 3.1 Add failing tests: clicking "Write next escalation email" calls `escalate` once and never `sendMessage`; at `escalation_level: 3` the button is disabled and its title mentions the highest level. Verify they fail.
- [x] 3.2 Wire the button to the existing `handleEscalate`, turned off when `escalation_level >= 3` with an explanatory `title`. Verify the 3.1 tests pass, and that the existing "offers no escalation once the invoice is at Legal" test still passes.

## 4. End dispute action

- [x] 4.1 Add failing tests: clicking "End dispute" does not settle on its own; confirming calls `settle` once; cancelling leaves `settle` uncalled. Verify they fail.
- [x] 4.2 Change `confirmingSettle` from a boolean to a `'sidebar' | 'bar' | null` source, show the existing confirmation next to whichever control opened it, and wire "End dispute" to it. Verify the 4.1 tests pass and the existing "marks the invoice as settled after confirming" sidebar test still passes.

## 5. Busy and waiting-draft state

- [x] 5.1 Add failing tests: with `loading: true`, and separately with a waiting draft interrupt (e.g. `tool: 'draft_polite_reminder'`) plus an earlier message, all three quick-action buttons are disabled. Verify they fail.
- [x] 5.2 Disable all quick actions when `loading || (interrupt && APPROVAL_TOOLS.includes(interrupt.tool))`. Verify the 5.1 tests pass.

## 6. Integration checks

- [x] 6.1 Run the full frontend checks: `cd frontend && npx vitest run && npm run lint && npm run build`. All must pass.
- [x] 6.2 Check it by hand in the running app (`uvicorn api.index:app --reload` + `cd frontend && npm run dev`): on an invoice that has history, try Summary (agent replies), Write next escalation email (the level moves up and an approval card appears; nothing is sent until approved), and End dispute (confirm → shows as settled, bar disappears). Also check the bar fits at phone width without the page scrolling sideways.

## Workflow follow-up

- Update CLAUDE.md's ChatPanel line to mention the quick-action bar if reviewers want it documented.
- Archive the change with `/opsx:archive` after it is merged.
