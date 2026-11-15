"""An owner email action must reach real HITL, never a prose-only fake composer."""
from tests.fakes import Overrides
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from tests.fakes import ScriptedModel, tool_call
from tests.test_approve_sends_email import create_invoice, signed_in, sent  # noqa: F401


class ChoiceModel(ScriptedModel):
    choices: list = []
    selected: str | None = None
    ignore_choice: bool = False

    def bind_tools(self, tools, **kwargs):
        choice = kwargs.get('tool_choice')
        self.selected = choice.get('function', {}).get('name') if isinstance(choice, dict) else choice
        self.choices.append(self.selected)
        return self

    def _generate(self, messages, **kwargs):
        if self.selected and not self.ignore_choice:
            args = {'subject': 'Invoice', 'body': 'Please review the invoice details.'} if self.selected == 'draft_invoice_delivery_email' else {}
            self.replies = [tool_call(self.selected, **args)]
        else:
            self.replies = [AIMessage(content='Copy the template into your email client and press Send.')]
        return super()._generate(messages, **kwargs)


@pytest.fixture
def choice_model(monkeypatch):
    import api.index as api
    from src.agent import build_agent
    model = ChoiceModel()
    monkeypatch.setattr(api.deps, 'agent', build_agent(model, MemorySaver()))
    return model


async def legal_invoice(client, fake_db, history=True):
    import api.index as api
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    fake_db.invoices[invoice['id']].update(escalation_level=3, amount_paid=100)
    if history:
        api.deps.agent.update_state({'configurable': {'thread_id': 'invoice-' + invoice['id']}}, {'messages': [
            HumanMessage(content='Please prepare the final notice.'),
            AIMessage(content='Subject: FINAL NOTICE BEFORE LEGAL ACTION\n\nDear Acme, please pay. Copy this into your email client.'),
        ]})
    return invoice, headers


async def post_chat(client, invoice, headers, text):
    return await client.post('/api/chat?include_history=false', headers=headers,
        json={'thread_id': 'invoice-' + invoice['id'], 'message': text})


@pytest.mark.asyncio
@pytest.mark.parametrize('text', [
    'Send the Final Notice (if not already sent) with the invoice attached.',
    "let's send it as a mail",
    "ok, I need to send this via mail, but you're not showing the email template which can be sent",
    'no, I want to send it via the chat email facility',
])
async def test_legal_requests_after_prose_reach_real_approval(client, fake_db, choice_model, sent, text):
    invoice, headers = await legal_invoice(client, fake_db)
    r = await post_chat(client, invoice, headers, text)
    assert r.status_code == 200, r.text
    card = r.json()['interrupt']
    assert card and card['tool'] == 'draft_final_notice'
    assert choice_model.choices == ['draft_final_notice']
    assert '$1,100.00' in card['description'] and '$100.00' in card['description']
    assert any('no invoice file' in note.lower() for note in card['notes'])
    assert 'attached' not in card['description'].lower()
    assert sent == []


@pytest.mark.asyncio
async def test_required_action_ignored_by_provider_is_bounded_error(client, fake_db, choice_model, sent):
    invoice, headers = await legal_invoice(client, fake_db)
    choice_model.ignore_choice = True
    r = await post_chat(client, invoice, headers, 'Please draft the final notice')
    assert r.status_code == 503 and 'review card' in r.json()['detail'].lower()
    assert choice_model.choices == ['draft_final_notice'] and sent == []
    await post_chat(client, invoice, headers, 'What is the invoice balance?')
    assert choice_model.choices[-1] is None  # request intent cannot leak


def previous_delivery(fake_db, invoice):
    fake_db.communications.append(dict(id=1, invoice_id=invoice['id'], type='Final Notice',
        direction='outbound', timestamp='2026-11-13 12:00:00', subject='Final notice', content='Previously sent.'))


@pytest.mark.asyncio
async def test_conditional_already_delivered_is_truthful_without_model_or_card(client, fake_db, choice_model, sent):
    invoice, headers = await legal_invoice(client, fake_db)
    previous_delivery(fake_db, invoice)
    r = await post_chat(client, invoice, headers, 'Send the final notice if not already sent')
    assert r.status_code == 200 and r.json()['interrupt'] is None
    assert 'already' in r.json()['messages'][-1]['content'].lower()
    assert '2026-11-13' in r.json()['messages'][-1]['content']
    assert choice_model.choices == [] and sent == []
    h = await client.get(f"/api/invoices/{invoice['id']}/history", headers=headers)
    assert 'already' in h.json()['messages'][-1]['content'].lower()


@pytest.mark.asyncio
async def test_explicit_resend_requires_card_with_previous_delivery_note(client, fake_db, choice_model, sent):
    invoice, headers = await legal_invoice(client, fake_db)
    previous_delivery(fake_db, invoice)
    r = await post_chat(client, invoice, headers, 'Please resend the final notice')
    card = r.json()['interrupt']
    assert card['tool'] == 'draft_final_notice' and any('2026-11-13' in n for n in card['notes'])
    assert sent == []


@pytest.mark.asyncio
async def test_pending_card_reused_before_sync_and_visible_without_full_history(client, fake_db, choice_model, sent):
    invoice, headers = await legal_invoice(client, fake_db)
    first = (await post_chat(client, invoice, headers, 'Draft the final notice')).json()['interrupt']
    assert first is not None
    fake_db.invoices[invoice['id']]['amount_paid'] = 200
    again = await post_chat(client, invoice, headers, 'Send the final notice')
    assert again.json()['interrupt']['tool'] == first['tool'] and len(choice_model.choices) == 1
    for suffix in ['summary', 'history', 'summary']:
        r = await client.get(f"/api/invoices/{invoice['id']}/{suffix}", headers=headers)
        assert r.json()['interrupt']['tool'] == first['tool']
        assert '$1,000.00' in r.json()['interrupt']['description']
        assert r.json()['interrupt']['notes'] == first['notes']
    approved = await client.post(f"/api/invoices/{invoice['id']}/resume", headers=headers,
        json={'decision':'approve', 'message':again.json()['interrupt']['description']})
    assert approved.status_code == 200 and len(sent) == 1
    assert choice_model.choices[-1] is None


@pytest.mark.asyncio
@pytest.mark.parametrize('field,value,expected', [('escalation_level',1,'legal'),('escalation_level',0,'legal'),('client_email','','email'),('status','paid','paid')])
async def test_ineligible_request_does_not_force_or_send(client, fake_db, choice_model, sent, field, value, expected):
    invoice, headers = await legal_invoice(client, fake_db)
    fake_db.invoices[invoice['id']][field] = value
    r = await post_chat(client, invoice, headers, 'Send the final notice')
    assert r.status_code == 200 and r.json()['interrupt'] is None
    assert expected in r.json()['messages'][-1]['content'].lower()
    assert choice_model.choices == [] and sent == []


@pytest.mark.asyncio
async def test_owner_check_precedes_preparation(client, fake_db, choice_model, sent):
    invoice, _ = await legal_invoice(client, fake_db)
    other = signed_in(fake_db, 'different-owner')
    r = await post_chat(client, invoice, other, 'Send the final notice')
    assert r.status_code in (403,404) and choice_model.choices == [] and sent == []


@pytest.mark.asyncio
async def test_legacy_level_zero_uses_same_canonical_level_as_graph(client, fake_db, choice_model, sent):
    invoice, headers = await legal_invoice(client, fake_db)
    fake_db.invoices[invoice['id']]['escalation_level'] = 0
    r = await post_chat(client, invoice, headers, 'Draft a polite reminder')
    assert r.status_code == 200 and r.json()['interrupt']['tool'] == 'draft_polite_reminder'
    assert choice_model.choices == ['draft_polite_reminder'] and sent == []


@pytest.mark.asyncio
@pytest.mark.parametrize('args', [{}, {'subject':'Invoice'}, {'subject':False,'body':[]}])
async def test_malformed_required_draft_is_bounded_failure(client, fake_db, monkeypatch, sent, args):
    import api.index as api
    from src.agent import build_agent
    invoice, headers = await legal_invoice(client, fake_db)
    monkeypatch.setattr(api.deps, 'agent', build_agent(ScriptedModel(replies=[
        tool_call('draft_invoice_delivery_email', **args)]), MemorySaver()))
    r = await post_chat(client, invoice, headers, 'Send the invoice')
    assert r.status_code == 503 and 'review card' in r.json()['detail']
    assert sent == []


def test_delivery_preview_uses_current_facts_instead_of_model_claims():
    import api.index as api
    from src.state import FreelancerContext
    state = dict(invoice_id='INV-9', client_name='Acme', invoice_amount=1200, amount_paid=100,
                 invoice_file_path=None)
    draft = api.generate_draft_preview('draft_invoice_delivery_email', state, FreelancerContext(),
        {'subject':'Invoice', 'body':'The invoice is attached. Pay $9,999.'})
    assert 'attached' not in draft.lower() and '9,999' not in draft
    assert '$1,200.00' in draft and '$100.00' in draft and '$1,100.00' in draft


@pytest.mark.asyncio
async def test_conditional_delivery_lookup_failure_is_not_assumed_unsent(client, fake_db, choice_model, monkeypatch):
    import api.index as api
    invoice, headers = await legal_invoice(client, fake_db)
    monkeypatch.setattr(api.deps, "db", Overrides(api.deps.db, get_last_outbound_delivery=lambda *a: (_ for _ in ()).throw(RuntimeError('private database error'))))
    r = await post_chat(client, invoice, headers, 'Send the final notice if not already sent')
    assert r.status_code == 503 and choice_model.choices == []
    assert 'private database error' not in r.text


@pytest.mark.asyncio
@pytest.mark.parametrize('level,message,tool', [
    (0,'Draft the invoice delivery email','draft_invoice_delivery_email'),
    (1,'Draft a polite reminder','draft_polite_reminder'),
    (2,'Please send a formal demand letter','draft_formal_demand_letter'),
])
async def test_other_supported_levels_use_same_review_boundary(client, fake_db, choice_model, sent, level, message, tool):
    headers = signed_in(fake_db)
    invoice = await create_invoice(client, headers)
    fake_db.invoices[invoice['id']]['escalation_level'] = level
    r = await post_chat(client, invoice, headers, message)
    assert r.status_code == 200 and r.json()['interrupt']['tool'] == tool
    assert choice_model.choices == [tool] and sent == []


@pytest.mark.asyncio
async def test_ambiguous_followup_clarifies_without_model(client, fake_db, choice_model):
    invoice, headers = await legal_invoice(client, fake_db, history=False)
    r = await post_chat(client, invoice, headers, 'Send it')
    assert r.status_code == 200 and r.json()['interrupt'] is None
    assert 'which' in r.json()['messages'][-1]['content'].lower()
    assert choice_model.choices == []


def test_client_run_cannot_activate_owner_tool_choice():
    from src.agent import build_agent
    from src.state import FreelancerContext
    model = ChoiceModel()
    graph = build_agent(model, MemorySaver())
    graph.invoke({'messages':[HumanMessage(content='Send the final notice')], 'escalation_level':3},
        context=FreelancerContext(untrusted_input=True, required_draft_tool='draft_final_notice'),
        config={'configurable':{'thread_id':'untrusted-card'}})
    assert model.choices == [None]


def test_above_level_required_choice_is_refused_before_model():
    from src.agent import build_agent
    from src.state import FreelancerContext
    from src.email_drafts import DraftPreparationError
    model = ChoiceModel()
    graph = build_agent(model, MemorySaver())
    with pytest.raises(DraftPreparationError):
        graph.invoke({'messages':[HumanMessage(content='Send final notice')], 'escalation_level':1},
            context=FreelancerContext(required_draft_tool='draft_final_notice'),
            config={'configurable':{'thread_id':'above-card'}})
    assert model.choices == []


@pytest.mark.asyncio
async def test_only_successful_matching_outbound_suppresses_conditional(client, fake_db, choice_model):
    invoice, headers = await legal_invoice(client, fake_db)
    fake_db.communications.append(dict(id=1,invoice_id=invoice['id'],type='Final Notice',direction='inbound',content='Claimed sent',timestamp='2026-11-13'))
    r = await post_chat(client, invoice, headers, 'Send final notice if not already sent')
    assert r.status_code == 200 and r.json()['interrupt']['tool'] == 'draft_final_notice'


@pytest.mark.asyncio
async def test_card_notes_do_not_expose_uploaded_storage_paths(client, fake_db, choice_model):
    invoice, headers = await legal_invoice(client, fake_db)
    fake_db.invoices[invoice['id']].update(invoice_file_path='private/tenant-secret/invoice.pdf',invoice_file_name='invoice.pdf')
    r = await post_chat(client, invoice, headers, 'Draft the final notice')
    card = r.json()['interrupt']
    assert any('not attached' in n for n in card['notes'])
    assert 'tenant-secret' not in str(card)


@pytest.mark.asyncio
async def test_guest_can_prepare_but_not_deliver_real_email(client, fake_db, choice_model, sent):
    invoice = await create_invoice(client)
    fake_db.invoices[invoice['id']]['escalation_level'] = 1
    r = await post_chat(client, invoice, {}, 'Draft a polite reminder')
    assert r.status_code == 200 and r.json()['interrupt']['tool'] == 'draft_polite_reminder'
    approved = await client.post(f"/api/invoices/{invoice['id']}/resume",json={'decision':'approve','message':r.json()['interrupt']['description']})
    assert approved.json()['email_status'] == 'demo' and sent == []
