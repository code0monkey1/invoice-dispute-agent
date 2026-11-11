# Design

## Context

See proposal.md for the motivation and specs/dispute-escalation/spec.md for the required behaviour. These facts about the current code shape the approach:

- **Tool sets.** `tools_for_level()` in `src/middleware/dynamic_tools.py` builds stacking tool lists, `LEVEL_n = LEVEL_(n-1) + [...]`. Both the tool list offered to the model and `enforce_tool_gate` read it. The gate checks the level in the *live* agent state, so a level raised earlier in the same run counts.
- **Escalation tool.** `escalate_dispute` is not approval-gated (`APPROVAL_REQUIRED` in `src/agent.py`). It writes `escalation_level + 1` into agent state when it runs.
- **Writes to the saved level.** `invoice_service.set_escalation_level()` raises the level by any amount. It is called after every chat run, after every resume (`record_resume_outcome`) and by the `/escalate` route.
- **Sending.** `send_approved_draft()` in `api/index.py` sends whatever approved email tool it is given, with no level check.
- **Frontend auto-approve.** `ChatPanel.tsx` approves any interrupt whose tool isn't in `APPROVAL_TOOLS` silently. If `escalate_dispute` were only gated on the backend, the UI would approve it with no human decision.
- **Database helper.** `db.update_invoice()` supports one conditional filter (`only_if_unpaid`). It returns the row afterwards whether or not the PATCH matched.
- **Level 0.** `invoice_state_from_db()` already reads a saved level of 0 as 1 (`or 1`). Generated invoices are created at 0.

## Goals / Non-Goals

**Goals:**
- One pure module holds the ladder rules, and every enforcement point calls it.
- The database is the only place a level change is saved. Agent state follows it and never writes back.
- A level check right before Gmail, so a stale or wrong-level draft can never go out.

**Non-Goals:**
- Lowering a level (de-escalation). Not supported. The ladder only goes up.
- Changing what each email says, or the tone of each level's prompt beyond its tool list.
- Rate limits or cooldowns between emails at the same level.
- Changes to the database schema.

## Decisions

### D1. A pure policy module: `src/services/escalation_policy.py`

It has no I/O:

```python
FRIENDLY, FORMAL, LEGAL = 1, 2, 3
LEVEL_NAMES = {1: "Friendly", 2: "Formal", 3: "Legal"}
MAIL_LEVEL = {                       # None = allowed at every level
    "draft_invoice_delivery_email": None,
    "draft_polite_reminder": FRIENDLY,
    "draft_formal_demand_letter": FORMAL,
    "draft_final_notice": LEGAL,
}
def can_draft(tool: str, level: int) -> bool      # non-mail tools: True
def next_level(level: int) -> int | None           # level+1, None at LEGAL
def is_valid_step(current: int, target: int) -> bool  # target == current+1 <= LEGAL
```

`tools_for_level()` is rebuilt on top of it. Each level gets its non-mail tools, plus the delivery email, plus the one email for that level. `escalate_dispute` is offered at levels 1–2 only. The gate's `_refusal` already reads `tools_for_level`, so the gate and the offered list stay one rule.

*Alternative:* keep the stacking lists and add a "same level" check inside each draft tool. Rejected: the rule would live in four tools plus the gate, which is the scatter this change removes.

### D2. `escalate_dispute` becomes an approval-gated proposal

- New signature: `escalate_dispute(reason: str)`.
- In `APPROVAL_REQUIRED` it becomes `{"allowed_decisions": ["approve", "reject"]}`. There is no edit: the only thing to decide is yes or no.
- When it runs, which happens only after approval, it still returns `Command(update={"escalation_level": n+1})`, so the rest of that run sees the new level. The database stays the record (D3).
- `extract_interrupt` / `generate_draft_preview` get a branch for this tool. The card receives `{from_level, to_level, reason}` as a readable preview: "Move from Friendly to Formal. Reason: …".

Several steps in one run work naturally. After the move to Formal is approved, the model may propose Legal, which raises a new interrupt that needs its own approval. No "once per run" counter is needed.

*Alternative:* remove the tool and keep only the Escalate button. Rejected by the user: the agent should be able to propose.

### D3. The database is written in exactly one place: `invoice_service.escalate()`

```python
def escalate(invoice_id, from_level) -> int | None:
    # Conditional update: SET escalation_level = from_level+1
    #   WHERE id = .. AND escalation_level = from_level AND status != 'paid'
    # Returns the new level, or None if the row didn't match (raced or settled).
def start_ladder(invoice_id) -> None:  # 0 -> 1 only, conditional on level = 0
```

- `db.update_invoice` gains an `only_if_level: int | None` filter, next to `only_if_unpaid`. The caller confirms the change by checking the returned row's level.
- `set_escalation_level()` is deleted, and every caller moves:
  - **Chat route.** The call that saves the level after a run is removed. If the run took the invoice from 0 to 1 (setup through `update_invoice_details`), it calls `start_ladder` instead.
  - **`record_resume_outcome`.** The call is removed. The state sync that follows reads the level from the database.
  - **`/escalate` route.** It calls `escalate(invoice_id, current)`. If that returns None, the route returns 409 ("the level changed, refresh").
  - **`/resume`, when `escalate_dispute` is approved.** It calls `escalate(invoice_id, pending_state level)` *before* `agent.invoke`, in the same place the email send happens today. If it returns None, the resume carries on anyway: the tool updates agent state, then `record_resume_outcome` syncs from the database and overwrites it, so the database wins. A race therefore never moves the level two steps.
- `update_invoice_details` sets `escalation_level: 1` only when the current state level is 0. Otherwise it leaves the level out of its update.

*Alternative:* commit the escalation inside `apply_approved_outcome` after the run. Rejected: the run may already have produced a next-level draft interrupt by then, and calling `update_state` empties a pending interrupt (a known LangGraph gotcha noted in `record_resume_outcome`). Committing before `invoke` avoids it.

### D4. Client-reply block unchanged in effect, renamed

`UNAPPROVED_STATE_TOOLS` becomes `CLIENT_REPLY_BLOCKED = {"update_invoice_details", "escalate_dispute"}`. Approval-gated payment tools stay proposable from a reply. Escalation does not, because it isn't a fact the client can report (spec: "Client replies cannot lead to escalation").

### D5. Level check at send time

At the top of `send_approved_draft`, after loading the invoice from the database, the function checks `can_draft(tool_name, db_level)`. Level 0 counts as 1, the same as `invoice_state_from_db`. On a mismatch it returns status `"level_mismatch"` before any Gmail call.

In `_resume_run`, a `level_mismatch` turns the decision into `reject` with the message: "The invoice is now at <Level>; this <email> no longer fits. Draft a new email at <Level>." The agent then neither logs the email as sent nor goes on as if it had gone out. `EMAIL_STATUS_NOTES` gets a matching note for the UI.

The freelancer's edited text is still sent as written. The check is on the tool's level, not the wording.

### D6. Frontend: approval is never implicit

- `ChatPanel.tsx`: the auto-approve `useEffect` is deleted. Any interrupt that isn't null shows a card.
- `DraftApproval.tsx`: a new `escalate_dispute` entry in a card-config map (label "Escalate to <Level>", the from→to levels, the reason, Approve/Reject, no Edit). There is also a generic fallback card for any other tool (the tool name and its preview text, Approve/Reject).
- `APPROVAL_TOOLS` gets `escalate_dispute`. The quick-action "turn off while a draft is waiting" rule already keys off `interrupt`, so it covers escalation cards too.

### D7. Prompts and evals

- **Prompts.** `escalation_level_{1,2,3}.txt` list only that level's tools. Level 1 and 2 say that `escalate_dispute` *proposes* a move the freelancer must approve. Level 3 says escalation has reached its top.
- **Golden cases.** New cases:
  - L1: "get tough with them" → `must_call: [escalate_dispute]`, `interrupt_tool: escalate_dispute`.
  - L2: "send a friendly nudge" → `must_not_call: [draft_polite_reminder]`.
  - L3: `must_not_call: [draft_polite_reminder, draft_formal_demand_letter]`.
- The existing `l1-injected-reply` case stays as it is.
- The live eval is rerun (`python -m evals.run`) before merging.

## Risks / Trade-offs

- **More clicks.** Escalation now takes an approval, and possibly a second card for the email. → This is intended. The escalation card and the draft card come in the same run, so it's two clicks with no extra typing.
- **The model keeps reaching for a removed lower-level email** (for example a reminder at Legal) and loops on gate refusals. → The prompts list only the allowed tools, the refusal message names the email allowed at this level, and the L2/L3 golden cases cover it.
- **Drafts waiting at deploy time.** A lower-level draft waiting in a checkpoint is refused at send (D5) instead of being sent. → This is acceptable and matches the spec. The freelancer is told to ask for a new draft.
- **Conditional update not confirmed.** PostgREST PATCH returns no row count here. → Confirm by reading the returned row's level. Treat "not equal to `from_level+1`" as not applied.
- **Hidden frontend dependencies on auto-approve.** Today every gated tool except `escalate_dispute` is in `APPROVAL_TOOLS`, so removing auto-approve changes nothing else. → A Vitest test pins the generic card.

## Migration Plan

- No schema or data migration. Existing saved levels are already valid (raised one step at a time by the button, or by the old chat-path persist, which never lowered).
- Deploy the backend and frontend together, since Vercel deploys the whole repo in one go. A frontend left on the old version would auto-approve the new escalation interrupt, so the two must not be split.
- Rollback: revert the merge commit. There is no data to undo.
