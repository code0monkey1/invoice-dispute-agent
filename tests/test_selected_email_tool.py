"""A resolved send request must not be diverted into an advisory status check."""
import pytest
from langgraph.checkpoint.memory import MemorySaver
from tests.fakes import ScriptedModel, tool_call
from tests.test_approve_sends_email import create_invoice, signed_in, sent  # noqa: F401


class StatusFirstModel(ScriptedModel):
    offered: list = []
    selected: str = ''
    settings: dict = {}

    def bind_tools(self, tools, **kwargs):
        self.offered = [tool.name for tool in tools]
        self.selected = (kwargs.get('tool_choice') or {}).get('function', {}).get('name','')
        self.settings = kwargs
        return self

    def _generate(self, messages, **kwargs):
        # The real provider trace picked this offered tool despite named choice.
        if 'check_invoice_status' in self.offered:
            self.replies = [tool_call('check_invoice_status')]
        else:
            self.replies = [tool_call(self.selected)]
        return super()._generate(messages, **kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize('level',[1,3])
async def test_preflighted_reminder_offers_only_selected_tool(client, fake_db, monkeypatch, sent, level):
    import api.index as api
    from src.agent import build_agent
    headers=signed_in(fake_db)
    invoice=await create_invoice(client,headers)
    fake_db.invoices[invoice['id']]['escalation_level']=level
    model=StatusFirstModel()
    monkeypatch.setattr(api.deps,'agent',build_agent(model,MemorySaver()))
    response=await client.post('/api/chat',headers=headers,json={
        'thread_id':'invoice-'+invoice['id'],'message':'Please draft a polite reminder for this invoice.'})
    assert response.status_code==200,response.text
    assert response.json()['interrupt']['tool']=='draft_polite_reminder'
    assert model.offered==['draft_polite_reminder']
    assert model.settings['parallel_tool_calls'] is False
    assert sent==[]


def test_required_email_prompt_does_not_instruct_a_status_check():
    from src.middleware.dynamic_prompts import prompt_for_state
    from src.state import FreelancerContext
    prompt=prompt_for_state({'invoice_id':'INV-9','escalation_level':1},
        FreelancerContext(required_draft_tool='draft_polite_reminder'))
    assert 'draft_polite_reminder' in prompt
    assert 'Start by checking the invoice status' not in prompt
    assert 'check_invoice_status' not in prompt
    assert 'owner approval' in prompt.lower()


def test_delivery_preparation_is_explicitly_before_approval():
    from src.middleware.dynamic_prompts import prompt_for_state
    from src.state import FreelancerContext
    from src.tools.drafting import draft_invoice_delivery_email
    prompt = prompt_for_state({'invoice_id':'INV-9','escalation_level':1},
        FreelancerContext(required_draft_tool='draft_invoice_delivery_email'))
    for instructions in (prompt, draft_invoice_delivery_email.description):
        assert 'before requesting approval' in instructions
        assert 'does not send' in instructions
