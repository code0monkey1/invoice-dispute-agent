"""Agent-proposed escalation through the real LangGraph agent.

escalate_dispute only proposes: the freelancer approves each step, and the
level is saved by invoice_service.escalate() when they do. Rejecting changes
nothing, and the gate keeps the next level's email locked until then.
"""
import pytest
from langchain_core.messages import ToolMessage

from tests.test_real_graph_payments import chat, create_invoice, decide, scripted, sent, signed_in, tool_call  # noqa: F401


def level(fake_db, invoice):
    return fake_db.invoices[invoice["id"]]["escalation_level"]


@pytest.mark.asyncio
async def test_an_escalation_proposal_waits_for_approval(client, fake_db, scripted):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [tool_call("escalate_dispute", reason="Three reminders, no reply.")]

    body = await chat(client, headers, invoice, "They're ignoring the invoice, get tough")

    assert body["interrupt"]["tool"] == "escalate_dispute"
    assert "Friendly" in body["interrupt"]["description"] and "Formal" in body["interrupt"]["description"]
    assert "Three reminders, no reply." in body["interrupt"]["description"]
    assert body["state"]["escalation_level"] == 1
    assert level(fake_db, invoice) == 1


@pytest.mark.asyncio
async def test_a_rejected_proposal_changes_nothing(client, fake_db, scripted):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [tool_call("escalate_dispute", reason="No reply.")]
    await chat(client, headers, invoice, "Get tough on this invoice")

    scripted.replies = [tool_call("draft_formal_demand_letter")]  # the model tries anyway
    body = await decide(client, headers, invoice, "reject", message="Not yet")

    assert level(fake_db, invoice) == 1
    assert body["state"]["escalation_level"] == 1
    assert body["interrupt"] is None  # the formal draft was refused by the gate


@pytest.mark.asyncio
async def test_an_approved_proposal_raises_the_level_and_unlocks_its_email(client, fake_db, scripted, sent):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [tool_call("escalate_dispute", reason="No reply.")]
    await chat(client, headers, invoice, "Get tough on this invoice")

    scripted.replies = [tool_call("draft_formal_demand_letter")]
    body = await decide(client, headers, invoice, "approve")

    assert level(fake_db, invoice) == 2
    assert body["state"]["escalation_level"] == 2
    assert body["interrupt"]["tool"] == "draft_formal_demand_letter"  # its own approval card
    assert sent == []  # approving an escalation sends nothing


@pytest.mark.asyncio
async def test_each_step_needs_its_own_approval(client, fake_db, scripted):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [tool_call("escalate_dispute", reason="No reply.")]
    await chat(client, headers, invoice, "Go straight to legal on this invoice")

    scripted.replies = [tool_call("escalate_dispute", reason="Still nothing.")]
    body = await decide(client, headers, invoice, "approve")
    assert level(fake_db, invoice) == 2
    assert body["interrupt"]["tool"] == "escalate_dispute"  # Formal -> Legal waits too
    assert "Formal" in body["interrupt"]["description"] and "Legal" in body["interrupt"]["description"]

    scripted.replies = [tool_call("draft_final_notice")]
    body = await decide(client, headers, invoice, "approve")
    assert level(fake_db, invoice) == 3
    assert body["interrupt"]["tool"] == "draft_final_notice"


@pytest.mark.asyncio
async def test_an_approval_racing_the_escalate_button_moves_only_once(client, fake_db, scripted):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [tool_call("escalate_dispute", reason="No reply.")]
    await chat(client, headers, invoice, "Get tough on this invoice")

    fake_db.invoices[invoice["id"]]["escalation_level"] = 2  # the button got there first
    body = await decide(client, headers, invoice, "approve")

    assert level(fake_db, invoice) == 2
    assert body["state"]["escalation_level"] == 2


@pytest.mark.asyncio
async def test_approving_an_escalation_is_traced(client, fake_db, scripted):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [tool_call("escalate_dispute", reason="No reply.")]
    await chat(client, headers, invoice, "Get tough on this invoice")
    await decide(client, headers, invoice, "approve")

    steps = [s for s in fake_db.trace_steps if s["type"] == "escalation"]
    assert steps and steps[-1]["payload"]["from_level"] == 1 and steps[-1]["payload"]["to_level"] == 2
