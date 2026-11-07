# TODOs

Deferred from the agent observability and evals work (Nov 2026). Each item says why it matters and where to start.

## P1

### Put `escalate_dispute` behind an approval card
- **Why:** an injected client reply stays in the thread's history. Runs started by the reply can't escalate (`enforce_tool_gate`, reason `untrusted_input`), but a later chat turn could still follow the injected text. `/api/chat` then persists the higher level through `invoice_service.set_escalation_level`. Escalating is meant to always be the user's call.
- **Start:** set `APPROVAL_REQUIRED["escalate_dispute"] = True` in `src/agent.py`. Add it to `APPROVAL_TOOLS` in `frontend/src/components/ChatPanel.tsx`: non-listed interrupts are auto-approved silently today. Give it a card ("Move to Formal?"). Add a golden case where a later trusted turn follows injected history.
- **Same question for `update_invoice_details`:** its state changes are reverted by the next DB sync, and the recipient always comes from the invoice row, so the risk is lower.

### Fix the empty reply on small-claims questions
- **Why:** in every live run, `l3-small-claims-help` ("How do I file in small claims court for this invoice?") gets a model call with **no content and no tool call**. The trace shows an empty response, so the user sees nothing. It's the one golden case failing in `evals/results/baseline.json`.
- **Start:** reproduce the single case with the harness, and compare `openai/gpt-oss-120b` reasoning settings (for example `reasoning_effort` or a larger `max_tokens`) or another model via `GROQ_MODEL`. Accept the fix with `python -m evals.run --write-baseline`.

## P2

- **Partial trace flush on timeouts:** a run killed by Vercel's 60 s limit never writes its trace (the recorder flushes in `finally`). Flush incrementally, or write the run row first and the steps as they come.
- **Cursor ties:** `/traces` pages on `started_at` only, so two runs started in the same millisecond at a page boundary could skip one. Use `(started_at, id)` as the cursor.
- **Frontend lint:** `npm run lint` has 4 errors that predate this work (`DraftApproval.tsx`, `GoogleCallback.tsx`, `AuthContext.tsx`). Fix them, then add lint to `.github/workflows/tests.yml`.
- **Upstream serializer warning:** every agent call logs a Pydantic "Expected `none`… field_name='context'" warning, from LangGraph serializing the `FreelancerContext` dataclass. That is thousands of lines per eval-heavy test run. Check whether a newer `langgraph` fixes it before filtering it.
- **Duplicate `/api/health` route:** `api/index.py` defines it twice, and the first (diagnostic) one wins. Remove the second.

## P3

- **Export traces to OpenTelemetry or LangSmith** behind an env flag, if a hosted trace UI becomes useful. The Supabase tables stay the source of truth.
- **Score production runs online:** sample real (redacted) runs nightly through the tone judge and alert on drift.
- **Real `edit` decisions:** the app sends an edited draft as an approval plus text, so the agent never learns a human changed its draft (traces label it `approved_with_edits`). Sending `{"type": "edit"}` would let the model learn from the edits.
