# Spec Delta

## Purpose

Keeps each invoice's agent conversation (messages, agent state and any approval waiting on the freelancer) durable across server restarts and shared across server instances, while keeping that stored conversation private and its health observable.

## ADDED Requirements

### Requirement: Conversation survives server restarts
When the persistent store is configured, the system SHALL persist each invoice's agent conversation after every agent step and SHALL restore it on any later request, regardless of which server instance handles that request or whether the instance has restarted since.

#### Scenario: History is shown after a redeploy
- **GIVEN** an invoice whose chat has at least one user message and one agent reply
- **WHEN** the backend is redeployed and the freelancer reopens that invoice's chat
- **THEN** the history endpoint returns the same messages in the same order

#### Scenario: Conversation continues on a different instance
- **GIVEN** a chat turn handled by one server instance
- **WHEN** the next chat message for the same invoice is handled by a different instance
- **THEN** the agent responds with the earlier messages in its context

### Requirement: Pending approvals survive server restarts
An approval request (a draft or payment change awaiting the freelancer's decision) SHALL remain pending and actionable after a server restart until the freelancer approves, edits or rejects it.

#### Scenario: Approving a draft after a restart
- **GIVEN** an invoice with a draft email awaiting approval
- **WHEN** the backend restarts and the freelancer then approves the draft
- **THEN** the approval is applied to that same draft and the email is sent once

### Requirement: Conversations are isolated per invoice
Stored conversation state SHALL be keyed by invoice, so that one invoice's conversation is never returned for, or mixed into, another invoice's conversation.

#### Scenario: Two invoices chatted concurrently
- **WHEN** two different invoices receive chat messages at the same time on the same instance
- **THEN** each invoice's history contains only its own messages

### Requirement: Stored conversations are not publicly readable
Stored conversation data SHALL be readable and writable only by the backend's privileged database role. Requests made with the public (anon) or signed-in (authenticated) database roles SHALL NOT be able to read, list or modify it.

#### Scenario: Anon key cannot read conversations
- **WHEN** a client queries the conversation storage through the public database API using the anon key
- **THEN** the request returns no conversation data

### Requirement: Recovery from dropped database connections
The system SHALL recover from database connections that were closed while idle (for example by the connection pooler) without requiring a restart. A request arriving after such a drop SHALL be served using a fresh connection.

#### Scenario: First request after a long idle period
- **GIVEN** a warm server instance whose database connection was closed during idle time
- **WHEN** a chat request arrives
- **THEN** the request succeeds and the conversation is read and written normally

### Requirement: Degraded memory is reported, not silent
If the persistent store is not configured or cannot be reached at startup, the system SHALL continue serving with non-durable, in-process memory and SHALL report this on the health endpoint. In production the health status SHALL be degraded rather than ok.

#### Scenario: Store missing in production
- **GIVEN** a production deployment without a persistent store configured
- **WHEN** the health endpoint is called
- **THEN** it reports the in-memory store, the reason, and a degraded status

#### Scenario: Store unreachable at startup
- **GIVEN** a persistent store is configured but the database rejects the connection at startup
- **WHEN** the health endpoint is called
- **THEN** it reports the in-memory store and the connection error, with no secrets in the message

#### Scenario: Store healthy
- **GIVEN** the persistent store is configured and reachable
- **WHEN** the health endpoint is called
- **THEN** it reports the persistent store and an ok status
