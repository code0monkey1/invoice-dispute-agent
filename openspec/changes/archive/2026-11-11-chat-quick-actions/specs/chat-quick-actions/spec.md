# Spec Delta

## Purpose

Gives freelancers one-click actions in the invoice chat for what they do most on an open dispute: get a summary, send the next escalation email, and end the dispute.

## ADDED Requirements

### Requirement: Quick-action bar above the chat input
The invoice chat SHALL show a bar of quick actions directly above the message input, labelled "Give me a summary", "Write next escalation email" and "End dispute", while the invoice is open and past its first-open state.

#### Scenario: Bar shown on an active invoice
- **GIVEN** an invoice that is not settled and has an earlier chat message or a sent email
- **WHEN** the freelancer opens its chat
- **THEN** the three quick actions are shown above the message input

#### Scenario: Bar hidden on first open
- **GIVEN** an invoice with no chat messages, no sent email and no waiting draft
- **WHEN** the freelancer opens its chat
- **THEN** the first-open actions are shown and the quick-action bar is not

#### Scenario: Bar hidden once settled
- **GIVEN** an invoice marked as settled
- **WHEN** the freelancer views its chat
- **THEN** the quick-action bar is not shown

### Requirement: Summary action asks the agent for a summary
"Give me a summary" SHALL send a fixed summary request to the agent as a chat message from the freelancer. The reply SHALL appear in the conversation like any other.

#### Scenario: Requesting a summary
- **WHEN** the freelancer clicks "Give me a summary"
- **THEN** a message asking for a summary of this invoice appears in the chat as sent by the freelancer
- **AND** the agent's reply appears in the conversation

### Requirement: Next escalation email escalates through the escalation action
"Write next escalation email" SHALL do exactly what the existing escalate action does: move the invoice up one escalation level, then have the agent draft the next email for approval. It SHALL NOT send a chat message asking the agent to escalate.

#### Scenario: Escalating from Friendly
- **GIVEN** an active invoice at the Friendly level
- **WHEN** the freelancer clicks "Write next escalation email"
- **THEN** the invoice moves to the Formal level
- **AND** the drafted email waits for the freelancer's approval and is not sent automatically
- **AND** no "escalate" chat message is sent on the freelancer's behalf

#### Scenario: Already at Legal
- **GIVEN** an invoice at the Legal level
- **WHEN** the freelancer views the quick-action bar
- **THEN** "Write next escalation email" is shown but can't be clicked, and says the invoice is already at the highest level

### Requirement: End dispute settles the invoice after confirmation
"End dispute" SHALL ask the freelancer to confirm before doing anything. On confirm it SHALL mark the invoice as settled, the same as the existing settle action. On cancel, nothing SHALL change.

#### Scenario: Confirming end dispute
- **WHEN** the freelancer clicks "End dispute" and then confirms
- **THEN** the invoice is marked as settled and the agent stops work on it

#### Scenario: Cancelling end dispute
- **WHEN** the freelancer clicks "End dispute" and then cancels
- **THEN** the invoice stays unsettled and nothing is sent

### Requirement: Quick actions are turned off while the agent is busy or a draft is waiting
All quick actions SHALL be turned off while the agent is working on a request and while an email draft is waiting for the freelancer's approval.

#### Scenario: Draft waiting for approval
- **GIVEN** an email draft waiting for approval
- **WHEN** the freelancer views the quick-action bar
- **THEN** none of the quick actions can be clicked

#### Scenario: Agent working
- **GIVEN** the agent is still working on a request
- **WHEN** the freelancer views the quick-action bar
- **THEN** none of the quick actions can be clicked

### Requirement: Sidebar escalation and settle controls are kept
The existing sidebar escalate and settle controls SHALL keep working as they do today, alongside the quick-action bar.

#### Scenario: Both controls present
- **GIVEN** an active invoice below the Legal level
- **WHEN** the freelancer views the chat page
- **THEN** both the sidebar "Escalate to …" control and the quick-action "Write next escalation email" are available
