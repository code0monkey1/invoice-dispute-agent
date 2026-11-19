"""Live eval regression: inbound analysis must use the stored client name."""
import pytest
from types import SimpleNamespace
from langchain_core.messages import AIMessage
from langgraph.graph.message import add_messages

from evals.cases import load_cases
from evals.harness import EvalHarness
from tests.fakes import ScriptedModel
from src.middleware.reply_details import fill_reply_details
from src.state import FreelancerContext


@pytest.mark.asyncio
@pytest.mark.parametrize('case_id', ['l0-injected-reply', 'l1-injected-reply', 'l2-quality-dispute'])
@pytest.mark.parametrize('blocks', [False, True])
async def test_inbound_analysis_fills_names_before_history_without_taking_action(case_id, blocks):
    case = next(case for case in load_cases() if case.id == case_id)
    text = 'Hi [Client Name], please clarify the issue [incl. tax]. Best, [Your Name]\n[date]'
    model = ScriptedModel()
    model.replies = [AIMessage(content=[{'type': 'text', 'text': text}] if blocks else text)]
    async with EvalHarness() as harness:
        run = await harness.run_case(case, model)
        invoices = list(harness.db.invoices.values())
    assert run.error is None, run.error
    assert run.reply_text == f"Hi {case.invoice['client_name']}, please clarify the issue [incl. tax]. Best, Owner"
    assert run.interrupt is None
    assert run.outbox == []
    assert all(invoice.get('status') != 'paid' for invoice in invoices)
    # Keep original model evidence: correct the user-facing response, not the evaluator.
    raw = [step['payload']['response'] for trace in run.runs for step in trace['steps'] if step['type'] == 'model_call']
    assert text in raw


def test_reply_replaces_one_message_and_preserves_nontext_blocks_and_metadata():
    asset = {'type': 'image_url', 'image_url': {'url': 'https://example.invalid/invoice.png'}}
    message = AIMessage(id='reply-1', content=[{'type': 'text', 'text': 'Hi [Client Name]', 'index': 0}, asset],
                        response_metadata={'model_name': 'scripted'})
    runtime = SimpleNamespace(context=FreelancerContext(untrusted_input=True))
    update = fill_reply_details.after_model({'messages': [message], 'client_name': 'Acme'}, runtime)
    messages = add_messages([message], update['messages'])
    assert len(messages) == 1
    assert messages[0].id == 'reply-1'
    assert messages[0].content == [{'type': 'text', 'text': 'Hi Acme', 'index': 0}, asset]
    assert messages[0].response_metadata == message.response_metadata


def test_payment_tool_calls_and_arguments_do_not_enter_reply_formatter():
    call = {'name': 'mark_invoice_paid', 'args': {}, 'id': 'payment-1'}
    message = AIMessage(content='Review [Client Name] payment', tool_calls=[call])
    runtime = SimpleNamespace(context=FreelancerContext(untrusted_input=True))
    assert fill_reply_details.after_model({'messages': [message], 'client_name': 'Acme'}, runtime) is None
    assert message.content == 'Review [Client Name] payment'
    assert message.tool_calls == [dict(call, type='tool_call')]
