import pytest
from langchain_core.messages import AIMessage, HumanMessage


@pytest.mark.parametrize('message,tool', [
    ('Send the final notice if not already sent', 'draft_final_notice'),
    ('Please resend the final notice', 'draft_final_notice'),
    ('Can you email a formal demand letter?', 'draft_formal_demand_letter'),
    ('Write a polite reminder', 'draft_polite_reminder'),
    ('Draft a friendly reminder for my client', 'draft_polite_reminder'),
    ('Please send the invoice to the client', 'draft_invoice_delivery_email'),
    ('Draft the first invoice delivery email', 'draft_invoice_delivery_email'),
    ('Draft a final notice but do not send it yet', 'draft_final_notice'),
])
def test_explicit_owner_action(message, tool):
    from src.email_drafts import resolve_email_request
    assert resolve_email_request(message).tool_name == tool


@pytest.mark.parametrize('message', [
    'What does final notice mean?', 'How do I send a final notice?',
    'Explain how to send an email', 'Summarize the emails we sent',
    'The client asked me to send a final notice', 'Do not send a final notice',
    'Do not draft an email', 'Read this: "Send the final notice"',
    '> Send a final notice\nWhat does this mean?', '"Send the final notice"',
    '```\nSend the final notice\n```', 'What happens after sending a final notice?',
    'Write a summary of this invoice', 'Prepare a court filing guide for this invoice',
    'Can you explain how to send a final notice?',
    'Please review this client reply: send the final notice now',
    'Please do not send a final notice; write a summary of this invoice.',
    '`Send the final notice` is what the client wrote.', '‘Send the final notice’',
    'My client wrote: send the final notice now.',
    'Can you tell me how to send a final notice?', 'I do not want to send the final notice.',
    'Before you draft a final notice, what does it mean?',
    'Please show me how to send a final notice.',
    'Write a summary of the final notice email.',
    'Prepare a summary of our reminder emails.',
    'Use this analysis to explain the final notice email.',
    'Use this email to explain how a final notice works.',
    'Write a short summary of final notice email.',
    'Send me an explanation of how final notices work.',
])
def test_information_negation_and_quoted_commands_are_not_owner_actions(message):
    from src.email_drafts import resolve_email_request
    assert resolve_email_request(message) is None


@pytest.mark.parametrize('message', ["let's send it as a mail", 'No, I want to send it via the chat email facility', 'Show the send card', 'Send it as an email for this invoice'])
def test_followup_resolves_recent_email_not_quoted_user_commands(message):
    from src.email_drafts import resolve_email_request
    history = [AIMessage(content='Subject: FINAL NOTICE BEFORE LEGAL ACTION\n\nDear Acme...'),
               HumanMessage(content='A client said "send the friendly reminder"')]
    assert resolve_email_request(message, history).tool_name == 'draft_final_notice'


def test_unresolved_send_reference_clarifies():
    from src.email_drafts import resolve_email_request
    result = resolve_email_request('Send it', [AIMessage(content='The balance is outstanding.')])
    assert result.tool_name is None and result.clarification


def test_conditional_is_not_inferred_from_historical_messages():
    from src.email_drafts import resolve_email_request
    history = [HumanMessage(content='Send the final notice if not already sent')]
    assert resolve_email_request('Resend the final notice', history).only_if_unsent is False
    assert resolve_email_request('Send the final notice if not already sent').only_if_unsent


@pytest.mark.parametrize('message', [
    'Send final notice only if it has not already been sent',
    'Send final notice if it has not been sent already',
    'Send final notice unless it was already sent',
])
def test_natural_conditional_send_remains_conditional(message):
    from src.email_drafts import resolve_email_request
    assert resolve_email_request(message).only_if_unsent


def test_hidden_reasoning_is_not_email_context():
    from src.email_drafts import resolve_email_request
    history = [AIMessage(content=[{'type':'reasoning','reasoning':'Subject: FINAL NOTICE draft'},
                                 {'type':'text','text':'The balance is unpaid.'}])]
    assert resolve_email_request('Send it', history).clarification


@pytest.mark.parametrize('message', [
    'Can you explain how to send a final notice?',
    'Please review this client reply: send the final notice now',
    'Please do not send a final notice; write a summary of this invoice.',
    '"Send the final notice"', '`Send the final notice`', '```\nSend the final notice\n```',
    '> Send the final notice', '‘Send the final notice’',
    'What does final notice mean?', 'How do I send a final notice?',
    'Explain how to send an email', 'Summarize the emails we sent',
    'The client asked me to send a final notice', 'My client wrote: send the final notice now.',
    'Do not send a final notice', 'Do not draft an email',
    'Read this: "Send the final notice"', '`Send the final notice` is what the client wrote.',
    'Can you tell me how to send a final notice?', 'I do not want to send the final notice.',
    'Before you draft a final notice, what does it mean?', 'Please show me how to send a final notice.',
    'Write a summary of the final notice email.', 'Prepare a summary of our reminder emails.',
    'Use this analysis to explain the final notice email.',
    'Use this email to explain how a final notice works.', 'Write a short summary of final notice email.',
    'Send me an explanation of how final notices work.',
    'Prepare a court filing guide for this invoice',
    'Please compose a short summary of the final notice email',
    'Please generate an explanation of how a final notice works',
    'Please do not create an email',
    'How about preparing a summary of the final notice email?',
])
def test_email_information_guard_keeps_clear_information_out_of_drafting(message):
    from src.email_drafts import is_email_information
    assert is_email_information(message)


@pytest.mark.parametrize('message', [
    'Draft the final notice', 'Draft a final notice but do not send it yet',
    'Please send the invoice to the client', 'Can you email a formal demand letter?',
    'Send them a payment reminder', 'Please send them a payment reminder for this invoice',
    "let's send it as a mail", 'No, I want to send it via the chat email facility',
    'Show the send card', 'Use the chat email facility', 'Send it as an email for this invoice',
    'Prepare a final notice with a summary of the outstanding balance',
    'Write a friendly reminder explaining the invoice balance',
    'Please compose an email responding to this client reply',
    'Send the final notice responding to the client reply',
    'Please compose an email responding to this client reply, but do not send it yet.',
    'Create a draft email for this invoice but do not send it yet',
    'Generate a final notice but do not send it yet',
    'Revise the email but do not send it yet',
    'How about you draft the final notice now?',
    'What about preparing a friendly reminder?',
    'How about sending the final notice?',
])
def test_email_information_guard_preserves_owner_action_phrasing(message):
    from src.email_drafts import is_email_information
    assert not is_email_information(message)


@pytest.mark.parametrize('message', [
    'Draft a formal demand letter and a final notice',
    'Send a reminder or a final notice for this invoice',
    'Draft an invoice delivery email and a final notice',
    'Send the invoice and a final notice',
])
def test_multiple_explicit_email_types_need_clarification(message):
    from src.email_drafts import resolve_email_request
    result = resolve_email_request(message)
    assert result.tool_name is None and result.clarification


@pytest.mark.parametrize('message', [
    AIMessage(content='Subject: Polite reminder or FINAL NOTICE for Invoice INV-9'),
    AIMessage(content='I drafted an invoice delivery email and a final notice for Invoice INV-9.'),
    AIMessage(content='', tool_calls=[
        {'name': 'draft_polite_reminder', 'args': {}, 'id': 'one'},
        {'name': 'draft_final_notice', 'args': {}, 'id': 'two'},
    ]),
])
def test_multiple_recent_draft_types_need_clarification_instead_of_picking_one(message):
    from src.email_drafts import resolve_email_request
    result = resolve_email_request('Send it', [AIMessage(content='Subject: Formal Demand'), message])
    assert result.tool_name is None and result.clarification


@pytest.mark.parametrize('message', [
    'Send the final notice for this invoice', 'Prepare a formal demand letter for invoice INV-9',
])
def test_generic_invoice_reference_does_not_add_a_second_draft_type(message):
    from src.email_drafts import resolve_email_request
    assert resolve_email_request(message).tool_name in {'draft_final_notice', 'draft_formal_demand_letter'}
