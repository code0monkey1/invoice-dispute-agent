# Design

## Context

See proposal.md for the motivation. Relevant parts of the current state:

- `ChatPanel.tsx` already has `handleEscalate` → `escalate()` and a `confirmingSettle` flag that drives an inline confirmation before `settle()`, both shown in the sidebar.
- `showFirstOpenActions` already decides when the first-open (delivery email / chat) actions are shown.
- `APPROVAL_TOOLS.includes(interrupt.tool)` is already how the input decides that a draft is waiting.
- `POST /api/chat` answers paid invoices with a canned "resolved" reply, and `POST /api/invoices/{id}/escalate` returns 400 at Legal or when paid. The bar's visibility follows these limits, so it never offers an action the server will refuse.
- `check_invoice_status` returns figures plus a *count* of communications, not what they said. The agent only knows the content of its own chat thread.

## Goals / Non-Goals

**Goals:**
- Reuse the existing hooks and the existing confirmation state, so the sidebar and the bar can't fall out of step.
- The bar's state follows the rules the server already enforces.

**Non-Goals:**
- Pulling the bar out into a reusable component library, or adding a set of prompts that changes by level.
- Improving what the agent can see for the summary (for example, showing it reply contents).

## Decisions

1. **Inline in `ChatPanel`, not a new component file.** The bar needs `loading`, `interrupt`, `agentState`, `showFirstOpenActions`, `confirmingSettle` and three handlers, which all already live in `ChatPanel`. A separate component would just pass all of them through. *Alternative:* a `QuickActions.tsx` component. Reconsider if a fourth or fifth action is added.

2. **One `confirmingSettle` state for both places.** "End dispute" sets the same flag the sidebar "Mark as settled" does. The confirmation shows next to whichever control was clicked (track the source with a `'sidebar' | 'bar' | null` value instead of a boolean). Confirming calls the same `settle()`. *Alternative:* a second, separate confirmation, which would mean the warning text lives in two places.

3. **Summary prompt is a module constant** next to `INVOICE_DELIVERY_PROMPT`:
   > "Give me a summary of this invoice: client, amount and balance due, status, days overdue, escalation level, how many emails have been sent, what has happened so far in this chat, and what you'd suggest doing next."
   It asks only for what the agent can actually see (the count of emails sent, its own thread), so it won't invent reply contents. It includes "invoice", so it passes `is_invoice_chat_message`.

4. **Visibility and turned-off rules** (in terms of existing values):
   ```
   showBar      = agentState && !showFirstOpenActions && agentState.status !== 'paid'
   busy         = loading || (interrupt && APPROVAL_TOOLS.includes(interrupt.tool))
   summary      : disabled = busy
   nextEmail    : disabled = busy || escalation_level >= 3   (title explains Legal)
   endDispute   : disabled = busy
   ```
   Hiding the bar on paid matches the server's canned reply. Turning it off rather than hiding it at Legal and while busy keeps the layout steady.

5. **Look:** small pill buttons (`text-xs`, rounded-full, light outline, brand-orange hover) in a horizontally scrollable row (`overflow-x-auto`, no wrap) so it fits on a phone. Each has a lucide icon: `FileText` / `ArrowUpCircle` / `Check` (all already imported).

## Risks / Trade-offs

- [Escalate and End dispute appear twice on the page] → Agreed on purpose: the sidebar shows the level ladder, the bar is quick access. Shared hooks and shared confirmation state keep them in sync.
- [Summary can't quote client replies] → The prompt is worded within what the agent can see. Richer summaries are follow-up work (they need tool or state changes, plus evals).
- [Clicking End dispute by mistake] → Same confirmation as the sidebar, and it is turned off while a draft is waiting, so a pending draft is never silently dropped from the bar.

## Migration Plan

Frontend-only change: deploy as usual. Roll back by reverting the commit. No data or API changes.
