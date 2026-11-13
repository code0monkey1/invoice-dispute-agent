"""Opening is an explicit POST; history/polling and message writes never generate."""
from unittest.mock import Mock

import pytest
from langchain_core.messages import AIMessage

from tests.test_approve_sends_email import create_invoice as _create_invoice, sent, signed_in  # noqa: F401
from tests.test_real_graph_payments import scripted, tool_call  # noqa: F401


async def create_invoice(client, headers=None):
    inv = await _create_invoice(client, headers)
    result = await client.post('/api/chat', headers=headers or {}, json={
        'thread_id': f"invoice-{inv['id']}", 'message': 'What is the status of this invoice?',
    })
    assert result.status_code == 200
    return inv


@pytest.fixture
def summarizer(monkeypatch):
    from src.services import conversation_summary as s
    model = Mock(return_value='Acme has an unpaid invoice; next step is reviewing the pending action.')
    monkeypatch.setattr(s, '_call_model', model)
    return model


@pytest.mark.asyncio
async def test_post_persists_and_get_history_reads_without_ai(client, fake_db, scripted, summarizer):
    headers = signed_in(fake_db)
    inv = await create_invoice(client, headers)
    url = f"/api/invoices/{inv['id']}/summary"
    before = await client.get(f"/api/invoices/{inv['id']}/history", headers=headers)
    assert before.json()['summary'] is None
    assert summarizer.call_count == 0
    first = await client.post(url, headers=headers)
    assert first.status_code == 200, first.text
    body = first.json()
    assert body['summary'].startswith('Acme') and body['source_version'] and body['generated_at']
    assert body['status'] == 'current' and body['is_stale'] is False
    assert (await client.get(url, headers=headers)).json() == body
    assert (await client.post(url, headers=headers, json={})).json() == body
    history = (await client.get(f"/api/invoices/{inv['id']}/history", headers=headers)).json()
    assert history['summary'] == body['summary']
    assert history['summary_metadata']['source_version'] == body['source_version']
    assert summarizer.call_count == 1


@pytest.mark.asyncio
async def test_new_chat_does_not_generate_until_next_explicit_open(client, fake_db, scripted, summarizer):
    headers = signed_in(fake_db)
    inv = await create_invoice(client, headers)
    url = f"/api/invoices/{inv['id']}/summary"
    before = (await client.post(url, headers=headers)).json()
    scripted.replies = [AIMessage(content='I noted the new promise.')]
    response = await client.post('/api/chat', headers=headers, json={'thread_id': f"invoice-{inv['id']}", 'message': 'The client promised to pay this invoice tomorrow'})
    assert response.status_code == 200
    assert summarizer.call_count == 1
    for _ in range(2):
        history = (await client.get(f"/api/invoices/{inv['id']}/history", headers=headers)).json()
        assert history['summary'] == before['summary'] and history['summary_metadata']['is_stale']
        assert (await client.get(url, headers=headers)).json()['is_stale']
    assert summarizer.call_count == 1
    after = (await client.post(url, headers=headers)).json()
    assert after['source_version'] != before['source_version'] and not after['is_stale']
    assert summarizer.call_count == 2


@pytest.mark.asyncio
async def test_refresh_does_not_consume_approval_or_send_email(client, fake_db, scripted, summarizer, sent):
    headers = signed_in(fake_db)
    inv = await create_invoice(client, headers)
    scripted.replies = [tool_call('draft_polite_reminder')]
    await client.post('/api/chat', headers=headers, json={'thread_id': f"invoice-{inv['id']}", 'message': 'Draft a polite reminder for this invoice'})
    assert summarizer.call_count == 0
    assert (await client.post(f"/api/invoices/{inv['id']}/summary", headers=headers)).status_code == 200
    hist = (await client.get(f"/api/invoices/{inv['id']}/history", headers=headers)).json()
    assert hist['interrupt']['tool'] == 'draft_polite_reminder'
    assert sent == []
    result = await client.post(f"/api/invoices/{inv['id']}/resume", headers=headers, json={'decision': 'approve'})
    assert result.status_code == 200 and len(sent) == 1
    assert summarizer.call_count == 1  # approving/sending never refreshes


@pytest.mark.asyncio
async def test_inbound_reply_waits_for_open_even_on_settled_invoice(client, fake_db, scripted, summarizer):
    import api.index as api
    headers = signed_in(fake_db)
    inv = await create_invoice(client, headers)
    fake_db.invoices[inv['id']]['status'] = 'paid'
    api.handle_client_reply(fake_db.invoices[inv['id']], 'ap@acme.example', 'Re: invoice', 'Paid yesterday.')
    assert summarizer.call_count == 0
    result = await client.post(f"/api/invoices/{inv['id']}/summary", headers=headers)
    assert result.status_code == 200
    assert 'Paid yesterday.' in summarizer.call_args.args[0]['communications']


@pytest.mark.asyncio
async def test_other_owners_cannot_read_or_refresh(client, fake_db, scripted, summarizer):
    mine = signed_in(fake_db)
    inv = await create_invoice(client, mine)
    other = signed_in(fake_db, 'other-user')
    for method in ('get', 'post'):
        result = await getattr(client, method)(f"/api/invoices/{inv['id']}/summary", headers=other)
        assert result.status_code == 404
    assert summarizer.call_count == 0
    assert fake_db.summaries == {}


@pytest.mark.asyncio
async def test_guest_ownership_follows_invoice_after_signin(client, fake_db, scripted, summarizer):
    from src.db import migrate_guest_to_user
    inv = await create_invoice(client)
    url = f"/api/invoices/{inv['id']}/summary"
    before = await client.post(url)
    assert before.status_code == 200
    headers = signed_in(fake_db)
    guest_id = fake_db.invoices[inv['id']]['user_id']
    migrate_guest_to_user(guest_id, 'user-1')
    assert (await client.get(url, headers=headers)).json()['summary'] == before.json()['summary']
    assert (await client.get(url)).status_code == 404
    assert summarizer.call_count == 1


@pytest.mark.asyncio
async def test_no_transcript_returns_empty_without_model(client, fake_db, scripted, summarizer, monkeypatch):
    import api.index as api
    from types import SimpleNamespace
    headers = signed_in(fake_db)
    inv = await create_invoice(client, headers)
    monkeypatch.setattr(api.agent, 'get_state', lambda config: SimpleNamespace(values={}, tasks=[]))
    r = await client.post(f"/api/invoices/{inv['id']}/summary", headers=headers)
    assert r.status_code == 200 and r.json()['status'] == 'empty'
    assert r.json()['summary'] is None and summarizer.call_count == 0
    hist = (await client.get(f"/api/invoices/{inv['id']}/history", headers=headers)).json()
    assert hist['summary'] is None and hist['summary_metadata']['status'] == 'empty'


@pytest.mark.asyncio
async def test_model_failure_is_deferred_and_history_stays_usable(client, fake_db, scripted, summarizer):
    headers = signed_in(fake_db)
    inv = await create_invoice(client, headers)
    summarizer.side_effect = TimeoutError('secret detail')
    r = await client.post(f"/api/invoices/{inv['id']}/summary", headers=headers)
    assert r.status_code == 202 and r.json()['status'] == 'failed'
    assert 'secret detail' not in r.text
    history = await client.get(f"/api/invoices/{inv['id']}/history", headers=headers)
    assert history.status_code == 200 and history.json()['messages']
    assert history.json()['summary_metadata']['status'] == 'failed'


@pytest.mark.asyncio
async def test_missing_store_does_not_hide_history(client, fake_db, scripted, summarizer):
    headers = signed_in(fake_db)
    inv = await create_invoice(client, headers)
    fake_db.down_tables.add('invoice_conversation_summaries')
    hist = await client.get(f"/api/invoices/{inv['id']}/history", headers=headers)
    assert hist.status_code == 200 and hist.json()['messages']
    assert hist.json()['summary_metadata']['status'] == 'unavailable'
    assert (await client.post(f"/api/invoices/{inv['id']}/summary", headers=headers)).status_code == 202
    assert summarizer.call_count == 0


@pytest.mark.asyncio
async def test_rejects_caller_content_and_malformed_missing_invoice(client, fake_db, scripted, summarizer):
    headers = signed_in(fake_db)
    inv = await create_invoice(client, headers)
    for body in ({'summary': 'fake'}, {'invoice_id': 'another'}, {'messages': []}):
        assert (await client.post(f"/api/invoices/{inv['id']}/summary", headers=headers, json=body)).status_code == 422
    assert (await client.post('/api/invoices/not-an-invoice/summary', headers=headers)).status_code == 404
    assert summarizer.call_count == 0


@pytest.mark.asyncio
async def test_summary_posts_have_their_own_rate_limit(client, fake_db, scripted, summarizer):
    import api.index as api
    headers = signed_in(fake_db)
    inv = await create_invoice(client, headers)
    for _ in range(api.SUMMARY_LIMIT_PER_MINUTE):
        assert (await client.post(f"/api/invoices/{inv['id']}/summary", headers=headers)).status_code == 200
    assert (await client.post(f"/api/invoices/{inv['id']}/summary", headers=headers)).status_code == 429
    assert (await client.get(f"/api/invoices/{inv['id']}/summary", headers=headers)).status_code == 200
    assert summarizer.call_count == 1


@pytest.mark.asyncio
async def test_summary_response_is_compact_but_keeps_pending_action(client, fake_db, scripted, summarizer):
    headers = signed_in(fake_db)
    inv = await create_invoice(client, headers)
    scripted.replies = [tool_call('draft_polite_reminder')]
    await client.post('/api/chat', headers=headers, json={'thread_id': f"invoice-{inv['id']}", 'message': 'Draft a polite reminder for this invoice'})
    result = (await client.get(f"/api/invoices/{inv['id']}/summary", headers=headers)).json()
    assert result['state']['client_name'] == 'Acme Corp'
    assert result['interrupt']['tool'] == 'draft_polite_reminder'
    assert result['has_history'] is True
    assert 'messages' not in result and 'communications' not in result
    assert result['state'].get('communication_history', []) == []
    assert summarizer.call_count == 0


@pytest.mark.asyncio
async def test_delta_chat_response_excludes_earlier_conversation(client, fake_db, scripted, summarizer):
    headers = signed_in(fake_db)
    inv = await create_invoice(client, headers)
    scripted.replies = [AIMessage(content='New answer only')]
    result = await client.post('/api/chat?include_history=false', headers=headers, json={'thread_id': f"invoice-{inv['id']}", 'message': 'Any new update on this invoice?'})
    assert result.status_code == 200
    contents = [m['content'] for m in result.json()['messages']]
    assert contents == ['Any new update on this invoice?', 'New answer only']
    assert summarizer.call_count == 0


@pytest.mark.asyncio
async def test_delta_escalation_and_resume_do_not_include_prior_messages(client, fake_db, scripted, summarizer, sent):
    headers = signed_in(fake_db)
    inv = await create_invoice(client, headers)
    scripted.replies = [tool_call('draft_formal_demand_letter')]
    escalated = await client.post(f"/api/invoices/{inv['id']}/escalate?include_history=false", headers=headers)
    assert escalated.status_code == 200, escalated.text
    assert all(m['content'] != 'What is the status of this invoice?' for m in escalated.json()['messages'])
    assert escalated.json()['interrupt']['tool'] == 'draft_formal_demand_letter'
    scripted.replies = [AIMessage(content='Approved outcome')]
    result = await client.post(f"/api/invoices/{inv['id']}/resume?include_history=false", headers=headers, json={'decision':'approve'})
    assert result.status_code == 200, result.text
    assert all(m['content'] != 'What is the status of this invoice?' for m in result.json()['messages'])
    assert result.json()['state']['communication_history'] == []
    assert len(sent) == 1 and summarizer.call_count == 0


@pytest.mark.asyncio
async def test_dashboard_never_returns_communication_bodies(client, fake_db, scripted):
    from src.db import add_communication
    headers = signed_in(fake_db)
    inv = await create_invoice(client, headers)
    add_communication(inv['id'], 'client_reply', 'Sensitive subject', 'Sensitive client reply', direction='inbound')
    result = await client.get('/api/invoices', headers=headers)
    assert 'Sensitive client reply' not in result.text and 'Sensitive subject' not in result.text
    row = result.json()[0]
    assert row['communication_history'] == []
    assert row['communication_count'] == 1 and row['last_communication_direction'] == 'inbound'
