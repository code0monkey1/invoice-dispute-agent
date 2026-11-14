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
