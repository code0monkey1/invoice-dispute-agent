"""A client's promise to pay must survive approval.

mark_invoice_pending used to return a message and nothing else, so the
promise and its follow-up date vanished. Now the tool proposes status
"pending" plus the date, and approving it saves both to the invoice.
"""
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from src.tools.payment_tools import mark_invoice_pending
from tests.test_approve_sends_email import create_invoice, fake_agent, signed_in  # noqa: F401


def run_tool(follow_up_date, state=None):
    runtime = SimpleNamespace(state=state or {"invoice_id": "INV-1"}, tool_call_id="call-1", context=None)
    return mark_invoice_pending.func(follow_up_date=follow_up_date, runtime=runtime)


def test_the_tool_proposes_pending_with_the_date():
    command = run_tool("2026-11-15")
    assert command.update["status"] == "pending"
    assert command.update["follow_up_date"] == "2026-11-15"


@pytest.mark.parametrize("bad", ["next friday", "15/11/2026", "2026-02-30", ""])
def test_the_tool_rejects_a_date_it_cannot_read(bad):
    command = run_tool(bad)
    assert "status" not in command.update
    assert "follow_up_date" not in command.update
    assert "YYYY-MM-DD" in command.update["messages"][0].content


def agent_that_runs_mark_pending(fake_agent, date="2026-11-15"):
    fake_agent.ask_for_approval("mark_invoice_pending")
    fake_agent.pending["args"] = {"follow_up_date": date}

    def invoke(payload, context=None, config=None):
        fake_agent.resumed_with = getattr(payload, "resume", payload)
        fake_agent.pending = None
        fake_agent.state.update({"status": "pending", "follow_up_date": date})
        return dict(fake_agent.state, messages=[AIMessage(content="Marked pending.")])

    fake_agent.invoke = invoke


@pytest.mark.asyncio
async def test_approving_the_promise_saves_it_on_the_invoice(client, fake_db, fake_agent):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    agent_that_runs_mark_pending(fake_agent)

    r = await client.post(f"/api/invoices/{invoice['id']}/resume", headers=headers, json={"decision": "approve"})

    assert r.status_code == 200, r.text
    saved = fake_db.invoices[invoice["id"]]
    assert saved["status"] == "pending"
    assert saved["follow_up_date"] == "2026-11-15"
    assert r.json()["state"]["follow_up_date"] == "2026-11-15"

    listed = {i["id"]: i for i in (await client.get("/api/invoices", headers=headers)).json()}
    assert listed[invoice["id"]]["follow_up_date"] == "2026-11-15"


@pytest.mark.asyncio
async def test_rejecting_the_promise_saves_nothing(client, fake_db, fake_agent):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    fake_agent.ask_for_approval("mark_invoice_pending")

    r = await client.post(f"/api/invoices/{invoice['id']}/resume", headers=headers, json={"decision": "reject"})

    assert r.status_code == 200, r.text
    assert fake_db.invoices[invoice["id"]]["status"] == "active"
    assert "follow_up_date" not in fake_db.invoices[invoice["id"]]


@pytest.mark.asyncio
async def test_the_agent_sees_the_promise_in_its_context(client, fake_db, fake_agent):
    import api.index as api_index
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    fake_db.invoices[invoice["id"]].update({"status": "pending", "follow_up_date": "2026-11-15"})

    summary = api_index.build_user_invoice_context(invoice["id"], "user-1")

    assert "2026-11-15" in summary


@pytest.mark.asyncio
async def test_resume_does_not_lower_the_escalation_level(client, fake_db, fake_agent):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    fake_db.invoices[invoice["id"]]["escalation_level"] = 3
    fake_agent.ask_for_approval("mark_invoice_pending")

    def invoke(payload, context=None, config=None):
        fake_agent.pending = None
        state = dict(fake_agent.state, messages=[AIMessage(content="ok")])
        state.pop("escalation_level", None)  # a run that doesn't report the level
        return state

    fake_agent.invoke = invoke
    r = await client.post(f"/api/invoices/{invoice['id']}/resume", headers=headers, json={"decision": "approve"})

    assert r.status_code == 200, r.text
    assert fake_db.invoices[invoice["id"]]["escalation_level"] == 3


def test_a_partial_payment_keeps_the_promise_open():
    from src.tools.payment_tools import record_partial_payment
    runtime = SimpleNamespace(
        state={"invoice_id": "INV-1", "invoice_amount": 1200.0, "amount_paid": 0, "status": "pending"},
        tool_call_id="call-1", context=None,
    )
    command = record_partial_payment.func(amount_paid=200.0, payment_date="2026-10-20", runtime=runtime)
    assert command.update["status"] == "pending"
    assert command.update["amount_paid"] == 200.0


def test_paying_the_rest_settles_a_pending_invoice():
    from src.tools.payment_tools import record_partial_payment
    runtime = SimpleNamespace(
        state={"invoice_id": "INV-1", "invoice_amount": 1200.0, "amount_paid": 200.0, "status": "pending"},
        tool_call_id="call-1", context=None,
    )
    command = record_partial_payment.func(amount_paid=1000.0, payment_date="2026-10-20", runtime=runtime)
    assert command.update["status"] == "paid"
