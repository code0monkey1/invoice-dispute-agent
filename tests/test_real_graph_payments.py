"""Payment and promise-to-pay flows through the real LangGraph agent.

The other tests use a FakeAgent. These build the production graph (same tools,
middleware and HITL config, via src.agent.build_agent) with a scripted chat
model, so they catch anything the fake gets wrong about interrupts, resumes
and state.
"""
import uuid

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import MemorySaver

from tests.test_approve_sends_email import create_invoice, sent, signed_in  # noqa: F401


class ScriptedModel(BaseChatModel):
    """Returns the queued replies in order; ends a run with plain text when the queue is empty."""

    replies: list = []

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        reply = self.replies.pop(0) if self.replies else AIMessage(content="Okay.")
        return ChatResult(generations=[ChatGeneration(message=reply)])


def tool_call(name, **args):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call-{uuid.uuid4().hex[:8]}"}])


@pytest.fixture
def scripted(monkeypatch):
    import api.index as api_index
    from src.agent import build_agent
    model = ScriptedModel()
    monkeypatch.setattr(api_index, "agent", build_agent(model, MemorySaver()))
    return model


async def chat(client, headers, invoice, message):
    r = await client.post("/api/chat", headers=headers, json={"thread_id": f"invoice-{invoice['id']}", "message": message})
    assert r.status_code == 200, r.text
    return r.json()


async def decide(client, headers, invoice, decision, **extra):
    r = await client.post(f"/api/invoices/{invoice['id']}/resume", headers=headers, json={"decision": decision, **extra})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.asyncio
async def test_promise_to_pay_is_saved_after_approval(client, fake_db, scripted):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [tool_call("mark_invoice_pending", follow_up_date="2026-11-15")]

    body = await chat(client, headers, invoice, "The client promised to pay the invoice on 2026-11-15")
    assert body["interrupt"]["tool"] == "mark_invoice_pending"
    assert fake_db.invoices[invoice["id"]]["status"] == "active"  # nothing saved before approval

    body = await decide(client, headers, invoice, "approve")

    saved = fake_db.invoices[invoice["id"]]
    assert saved["status"] == "pending"
    assert saved["follow_up_date"] == "2026-11-15"
    assert body["state"]["status"] == "pending"
    assert body["state"]["follow_up_date"] == "2026-11-15"


@pytest.mark.asyncio
async def test_rejected_promise_is_not_saved(client, fake_db, scripted):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [tool_call("mark_invoice_pending", follow_up_date="2026-11-15")]
    await chat(client, headers, invoice, "The client promised to pay the invoice on 2026-11-15")

    await decide(client, headers, invoice, "reject", message="No, they didn't")

    saved = fake_db.invoices[invoice["id"]]
    assert saved["status"] == "active"
    assert "follow_up_date" not in saved


@pytest.mark.asyncio
async def test_an_unreadable_date_saves_nothing_even_when_approved(client, fake_db, scripted):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [tool_call("mark_invoice_pending", follow_up_date="next friday")]
    await chat(client, headers, invoice, "The client says they'll pay the invoice next friday")

    await decide(client, headers, invoice, "approve")

    saved = fake_db.invoices[invoice["id"]]
    assert saved["status"] == "active"
    assert "follow_up_date" not in saved


@pytest.mark.asyncio
async def test_partial_payment_is_saved_and_full_payment_settles(client, fake_db, scripted):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)

    scripted.replies = [tool_call("record_partial_payment", amount_paid=200.0, payment_date="2026-10-20")]
    await chat(client, headers, invoice, "The client paid $200 toward the invoice")
    await decide(client, headers, invoice, "approve")
    assert float(fake_db.invoices[invoice["id"]]["amount_paid"]) == 200.0
    assert fake_db.invoices[invoice["id"]]["status"] == "active"

    scripted.replies = [tool_call("mark_invoice_paid")]
    await chat(client, headers, invoice, "The client paid the rest of the invoice")
    await decide(client, headers, invoice, "approve")
    assert fake_db.invoices[invoice["id"]]["status"] == "paid"
    assert float(fake_db.invoices[invoice["id"]]["amount_paid"]) == 1200.0


@pytest.mark.asyncio
async def test_an_infinite_payment_does_not_settle_the_invoice(client, fake_db, scripted):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [tool_call("record_partial_payment", amount_paid=float("inf"), payment_date="2026-10-20")]
    await chat(client, headers, invoice, "The client paid the invoice amount")

    history = await client.get(f"/api/invoices/{invoice['id']}/history", headers=headers)
    assert history.status_code == 200, history.text  # the chat must still load
    assert history.json()["interrupt"]["args"]["amount_paid"] is None

    await decide(client, headers, invoice, "approve")

    assert fake_db.invoices[invoice["id"]]["status"] == "active"
    assert float(fake_db.invoices[invoice["id"]]["amount_paid"]) == 0
    assert (await client.get(f"/api/invoices/{invoice['id']}/history", headers=headers)).status_code == 200


@pytest.mark.parametrize("amount", [float("nan"), -500.0, 0.0])
@pytest.mark.asyncio
async def test_nonsense_payment_amounts_change_nothing(client, fake_db, scripted, amount):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    scripted.replies = [tool_call("record_partial_payment", amount_paid=amount, payment_date="2026-10-20")]
    await chat(client, headers, invoice, "The client paid something toward the invoice")

    await decide(client, headers, invoice, "approve")

    assert fake_db.invoices[invoice["id"]]["status"] == "active"
    assert float(fake_db.invoices[invoice["id"]]["amount_paid"]) == 0


@pytest.mark.asyncio
async def test_approving_a_reminder_does_not_commit_an_ungated_tools_changes(client, fake_db, scripted, sent):
    """After the approved reminder, the run calls update_invoice_details (no approval needed).

    That tool resets the level to 1 and rewrites the client email in agent
    state. None of it may reach the database, and the email goes to the saved client.
    """
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    fake_db.invoices[invoice["id"]]["escalation_level"] = 2
    scripted.replies = [
        tool_call("draft_polite_reminder"),
        tool_call(
            "update_invoice_details", client_name="Evil", client_email="evil@attacker.example",
            invoice_amount=1.0, invoice_id="X", days_overdue=0, jurisdiction="Nowhere",
        ),
    ]
    await chat(client, headers, invoice, "Please draft a reminder for the invoice")

    await decide(client, headers, invoice, "approve", message="Subject: Reminder\n\nPlease pay invoice INV-SEND-1.")

    saved = fake_db.invoices[invoice["id"]]
    assert saved["client_email"] == "ap@acme.example"
    assert saved["client_name"] == "Acme Corp"
    assert float(saved["invoice_amount"]) == 1200.0
    assert saved["escalation_level"] == 2
    assert saved["status"] == "active"
    assert [s["to"] for s in sent] == ["ap@acme.example"]
