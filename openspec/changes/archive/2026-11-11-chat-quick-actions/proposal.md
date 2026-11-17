# Proposal

## Why

The three things a freelancer most often wants on an open dispute are to catch up on where it stands, send the next, firmer email, and close it out. Right now these mean typing a prompt or finding the escalate and settle buttons in the sidebar, away from the conversation. A row of one-click actions right above the chat input puts them where the freelancer is already looking.

## What Changes

- Add a quick-action bar directly above the chat input in `ChatPanel` with three buttons:
  - **Give me a summary**: sends a fixed summary prompt to the agent through the existing chat flow.
  - **Write next escalation email**: calls the existing `escalate()` hook (the server raises the level, then the agent drafts an email that goes to the normal approval card). It does not send an "escalate" chat message, because escalating is the user's decision and the server makes that change directly.
  - **End dispute**: calls the existing `settle()` hook after the same confirmation step the sidebar uses ("Mark as settled").
- The bar responds to invoice state: it is hidden on first open (the delivery-email actions are shown then) and once the invoice is settled; its buttons are turned off while the agent is working or a draft is waiting for approval; and "Write next escalation email" is turned off at the Legal level.
- The sidebar escalate and settle buttons stay as they are, since they also show the level ladder.
- No backend, schema, tool, prompt-template or eval changes.

Out of scope (discussed, deferred): drafting another email at the current level without escalating, recording *how* a dispute ended (paid / reduced amount / written off), and new prompts that would need new tools (reply to client, payment plan, late fee).

## Capabilities

### New Capabilities
- `chat-quick-actions`: the one-click actions shown with the invoice chat, when each is offered, and what each one does.

### Modified Capabilities
<!-- None: no existing specs in openspec/specs/. -->

## Impact

- `frontend/src/components/ChatPanel.tsx`: new bar above the input, a shared settle confirmation, and visibility/turned-off logic.
- `frontend/src/components/__tests__/ChatPanel.test.tsx`: new tests for the bar.
- Reuses the existing `useChat` hooks (`sendMessage`, `escalate`, `settle`), with no change to their signatures.
- APIs: none changed. The summary goes through `POST /api/chat`. It passes the chat topic check because the prompt mentions "invoice".
