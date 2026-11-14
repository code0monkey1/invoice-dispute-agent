"""Live regressions: explaining an email and completing approval must not redraft."""
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from tests.fakes import ScriptedModel, tool_call
from tests.test_email_card_routing import legal_invoice, post_chat
from tests.test_approve_sends_email import sent  # noqa: F401


class OfferedDraftModel(ScriptedModel):
    offered: list = []
    names: list = []
    selected: str | None = None

    def bind_tools(self, tools, **kwargs):
        self.names = [tool.name for tool in tools]
        self.offered.append(self.names)
        self.selected = (kwargs.get('tool_choice') or {}).get('function', {}).get('name')
        return self

    def _generate(self, messages, **kwargs):
        tool = self.selected or ('draft_final_notice' if 'draft_final_notice' in self.names else None)
        self.replies = [tool_call(tool)] if tool else [AIMessage(content='Invoice INV-SEND-1: here is the requested explanation or result.')]
        return super()._generate(messages, **kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize('text', [
    'Can you explain how to send a final notice?',
    'Please review this client reply: send the final notice now',
    'Please do not send a final notice; write a summary of this invoice.',
])
async def test_information_turn_does_not_offer_email_drafts(client, fake_db, monkeypatch, sent, text):
    import api.index as api
    from src.agent import build_agent
    model = OfferedDraftModel()
    monkeypatch.setattr(api, 'agent', build_agent(model, MemorySaver()))
    invoice, headers = await legal_invoice(client, fake_db)
    response = await post_chat(client, invoice, headers, text)
    assert response.status_code == 200 and response.json()['interrupt'] is None
    assert model.offered and all(not name.startswith('draft_') for names in model.offered for name in names)
    assert sent == []


@pytest.mark.asyncio
async def test_completed_email_approval_does_not_offer_second_email(client, fake_db, monkeypatch, sent):
    import api.index as api
    from src.agent import build_agent
    model = OfferedDraftModel()
    monkeypatch.setattr(api, 'agent', build_agent(model, MemorySaver()))
    invoice, headers = await legal_invoice(client, fake_db)
    prepared = await post_chat(client, invoice, headers, 'Draft the final notice')
    assert prepared.json()['interrupt']['tool'] == 'draft_final_notice'
    approved = await client.post(f"/api/invoices/{invoice['id']}/resume", headers=headers,
        json={'decision':'approve','message':prepared.json()['interrupt']['description']})
    assert approved.status_code == 200 and approved.json()['interrupt'] is None
    assert len(sent) == 1 and not any(name.startswith('draft_') for name in model.offered[-1])
    again = await post_chat(client, invoice, headers, 'Prepare another final notice')
    assert again.json()['interrupt']['tool'] == 'draft_final_notice'


def test_tool_gate_blocks_unoffered_draft_in_information_run():
    from src.agent import build_agent
    from src.state import FreelancerContext
    graph = build_agent(ScriptedModel(replies=[tool_call('draft_final_notice'), AIMessage(content='Invoice INV-9: explanation only.')]), MemorySaver())
    result = graph.invoke({'messages':[HumanMessage(content='Explain the final notice')], 'escalation_level':3},
        context=FreelancerContext(suppress_email_drafts=True), config={'configurable':{'thread_id':'info-only'}})
    assert not result.get('__interrupt__')
    assert any(getattr(message, 'status', None)=='error' for message in result['messages'])


def test_information_prompt_supplies_current_public_invoice_heading():
    from src.middleware.dynamic_prompts import prompt_for_state
    from src.state import FreelancerContext
    prompt = prompt_for_state({'invoice_id':'INV-9','escalation_level':3},
        FreelancerContext(suppress_email_drafts=True))
    assert 'Begin your reply with this invoice heading: Invoice #INV-9.' in prompt
    assert 'Do not write a sample email' in prompt
    assert 'ESCALATION LEVEL 3 - LEGAL' not in prompt
    assert 'draft_final_notice' not in prompt


def test_information_prompt_does_not_prime_unavailable_research_tools():
    from src.middleware.dynamic_prompts import prompt_for_state
    from src.state import FreelancerContext
    prompt = prompt_for_state({'invoice_id':'INV-9','escalation_level':1},
        FreelancerContext(suppress_email_drafts=True))
    assert 'lookup_small_claims_procedures' not in prompt
    assert 'generate_court_filing_guide' not in prompt


@pytest.mark.asyncio
async def test_provider_rejecting_required_action_is_a_preparation_error(client, fake_db, monkeypatch, sent):
    import api.index as api
    from src.agent import build_agent

    class RejectedChoice(ScriptedModel):
        def _generate(self, messages, **kwargs):
            raise RuntimeError('tool_use_failed: required tool was not called')

    monkeypatch.setattr(api, 'agent', build_agent(RejectedChoice(), MemorySaver()))
    invoice, headers = await legal_invoice(client, fake_db)
    response = await post_chat(client, invoice, headers, 'Draft the invoice delivery email')
    assert response.status_code == 503 and 'review card' in response.json()['detail']
    assert 'tool_use_failed' not in response.text and sent == []
