# Proposal

## Why

Escalation is meant to be a strict ladder (Friendly → Formal → Legal): emails go out only at the invoice's current level, and the level rises one step at a time, only when the freelancer approves it. Today the agent can call `escalate_dispute` with no approval, and can do it twice in one run. That lets it go from Friendly to an approval card for a Legal final notice, and saves the new level even if the email is rejected. Nothing checks the level again when the email is sent, and the rules for changing levels live in four different places.

## What Changes

- Add one escalation policy that owns the rules. A mail tool is allowed only at its own level, except the invoice delivery email, which is allowed at every level. The level can only rise by exactly one step, and never falls.
- **BREAKING** (agent behaviour): the email tools no longer stack up across levels. At Formal the agent can no longer send a polite reminder. At Legal it can no longer send a polite reminder or a formal demand.
- `escalate_dispute` becomes a proposal that needs the freelancer's approval. The new level is saved only when the freelancer approves, through `invoice_service`, with a check that the level hasn't changed in the meantime. Rejecting it changes nothing.
- The chat route stops copying the agent's escalation level into the database.
- `send_approved_draft` checks the email against the invoice's level in the database right before sending. An email for any other level is refused and not sent.
- `set_escalation_level` accepts only a one-step rise. `update_invoice_details` stops resetting the level and moves it from 0 to 1 only.
- The chat UI shows an approval card for escalation proposals. It no longer approves unrecognised approval requests silently; it shows a generic card for them instead.
- A client's reply still can't lead to an escalation proposal.
- The prompts for levels 1–3 and the golden eval cases change to match.

## Capabilities

### New Capabilities
- `dispute-escalation`: the escalation levels, which emails are allowed at each level, how a level is raised (approved, one step at a time), and the check at send time.

### Modified Capabilities
<!-- None. chat-quick-actions' "Write next escalation email" keeps using the escalate action, which still raises the level by exactly one. -->

## Impact

- **Backend**: `src/middleware/dynamic_tools.py` (per-level tool sets, gate), `src/tools/escalation.py`, `src/agent.py` (`APPROVAL_REQUIRED`), `src/services/invoice_service.py` (new policy and escalation commit), `api/index.py` (chat persistence, `/escalate`, `/resume`, `send_approved_draft`, approval-card preview for escalation).
- **Frontend**: `frontend/src/components/ChatPanel.tsx` (no silent auto-approve), `frontend/src/components/DraftApproval.tsx` (escalation card).
- **Prompts**: `src/prompts/v1/escalation_level_{1,2,3}.txt`.
- **Tests and evals**: `tests/test_tool_gate.py` (progressive-unlocking assertions change), new policy, resume and send tests, `evals/golden/level_{1,2,3}.yaml`. A live eval run is needed because tools and prompts change.
- No database schema change.
