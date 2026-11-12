# Tasks

Write each group's tests first (TDD): see them fail, then implement until `pytest` / `npx vitest run` pass.

## 1. Escalation policy module

- [x] 1.1 Add `tests/test_escalation_policy.py` covering `can_draft` for every mail tool × levels 0–3 (delivery allowed everywhere, each escalation email only at its own level, non-mail tools always True), `next_level` (1→2, 2→3, 3→None) and `is_valid_step` (only +1, never skip/lower/exceed 3); verify the tests fail
- [x] 1.2 Create `src/services/escalation_policy.py` (`LEVEL_NAMES`, `MAIL_LEVEL`, `can_draft`, `next_level`, `is_valid_step`, no I/O) and verify `pytest tests/test_escalation_policy.py` passes

## 2. Per-level tool sets and gate

- [x] 2.1 Update `tests/test_tool_gate.py`: replace `test_tools_for_level_matches_progressive_unlocking` (and the `level 9 == ALL_NAMES` assertion) with per-level exact sets; add refusals for `draft_polite_reminder` at levels 2–3, `draft_formal_demand_letter` at 3, `escalate_dispute` at 0 and 3; verify they fail
- [x] 2.2 Rebuild `tools_for_level()` in `src/middleware/dynamic_tools.py` from the policy (non-mail tools + delivery + the level's own email; `escalate_dispute` only at 1–2), make the refusal message name the email allowed at this level, rename `UNAPPROVED_STATE_TOOLS` → `CLIENT_REPLY_BLOCKED`; verify `pytest tests/test_tool_gate.py` passes

## 3. Single writer of the saved level

- [x] 3.1 Add a conditional `db.move_escalation_level(invoice_id, from_level, to_level)` (the fake DB already filters PATCHes); verify with a test that a mismatched level leaves the row unchanged
- [x] 3.2 Replace the `set_escalation_level` tests in `tests/test_invoice_service.py` with tests for `escalate(invoice_id, from_level)` (one-step rise, returns None on level mismatch, settled invoice, at Legal) and `start_ladder` (0→1 only); verify they fail
- [x] 3.3 Implement `invoice_service.escalate` and `start_ladder`, delete `set_escalation_level`; verify `pytest tests/test_invoice_service.py` passes
- [x] 3.4 Change `update_invoice_details` (`src/tools/escalation.py`) to set level 1 only when the state level is 0; verify with a test that saving details at Formal keeps Formal
- [x] 3.5 Update the chat route in `api/index.py`: drop the post-run level persist, call `start_ladder` when the run took the invoice from 0 to 1; switch `/escalate` to `escalate()` with 409 on None; verify `tests/test_escalate_invoice.py` (plus a new test: a chat run cannot change the saved level) passes

## 4. Approval-gated escalation proposal

- [x] 4.1 Add real-graph tests (pattern of `tests/test_real_graph_payments.py`): a scripted `escalate_dispute` call raises an interrupt; reject leaves DB and state at Friendly and a formal draft is still refused; approve sets DB to Formal and a following formal draft is offered; two escalations in one run need two approvals; approval racing the `/escalate` button leaves the level at Formal; verify they fail
- [x] 4.2 Give `escalate_dispute` a `reason: str` argument, set `APPROVAL_REQUIRED["escalate_dispute"] = {"allowed_decisions": ["approve", "reject"]}` in `src/agent.py`
- [x] 4.3 In `/resume` (`_resume_run`), on an approved `escalate_dispute` call `invoice_service.escalate(invoice_id, pending level)` before `agent.invoke`, record a trace step, and remove the level persist from `record_resume_outcome` (DB sync wins); verify the 4.1 tests pass
- [x] 4.4 Add an `escalate_dispute` branch to `generate_draft_preview` / `extract_interrupt` returning the from→to levels and reason; verify with a test on the interrupt payload
- [x] 4.5 Verify the existing client-reply tests still pass: `escalate_dispute` is refused on untrusted runs (`pytest tests/test_tool_gate.py -k client_reply`)

## 5. Level check at send time

- [x] 5.1 Add tests to `tests/test_approve_sends_email.py`: a pending polite reminder approved after the invoice moved to Formal is not sent (outbox empty, status `level_mismatch`, decision turned into a reject, no "email sent" history entry); a formal demand at Formal is sent; delivery email at Legal is sent; verify they fail
- [x] 5.2 Implement the `can_draft` check in `send_approved_draft`, the reject conversion in `_resume_run`, and a `level_mismatch` entry in `EMAIL_STATUS_NOTES`; verify the 5.1 tests pass

## 6. Frontend approval cards

- [x] 6.1 Add Vitest tests in `frontend/src/components/__tests__/ChatPanel.test.tsx`: an `escalate_dispute` interrupt shows an escalation card (from→to, reason, Approve/Reject, no Edit) and calls no API until clicked; an unknown tool interrupt shows a generic card and is not auto-approved; verify they fail
- [x] 6.2 Remove the auto-approve `useEffect` in `ChatPanel.tsx`, add `escalate_dispute` to `APPROVAL_TOOLS`, add the escalation card and generic fallback in `DraftApproval.tsx`; verify `cd frontend && npx vitest run`, `npm run lint` and `npm run build` pass

## 7. Prompts and evals

- [ ] 7.1 Update `src/prompts/v1/escalation_level_{1,2,3}.txt` to list only that level's tools, describe `escalate_dispute` as a proposal needing approval (levels 1–2), and state that Legal is the top; verify `pytest tests/test_prompts.py` passes
- [ ] 7.2 Add golden cases: L1 "get tough" → `escalate_dispute` interrupt; L2 friendly-nudge request → `must_not_call: [draft_polite_reminder]`; L3 → `must_not_call: [draft_polite_reminder, draft_formal_demand_letter]`; fix any existing case relying on stacked tools; verify `pytest tests/test_eval_invariants.py` passes
- [ ] 7.3 Update the Escalation Levels section of `CLAUDE.md` (per-level emails, approval-gated escalation, single writer); verify it matches `tools_for_level`

## 8. Integration verification

- [ ] 8.1 Run the full suites (`pytest`, `cd frontend && npx vitest run`) and verify they are green
- [ ] 8.2 Run the live eval (`python -m evals.run`) and verify `evals/results/latest.md` shows no new failures
- [ ] 8.3 Manual check with `uvicorn` and the dev frontend: at Friendly ask the agent to "get tough", approve the escalation card, approve the formal letter; reject a second proposal and confirm the level stays Formal
