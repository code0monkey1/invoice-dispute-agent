# Conversation Summary Spec Delta

## Purpose

Maintains a private, durable AI summary of each invoice's retained conversation so the freelancer can catch up when opening an invoice without repeated AI calls for unchanged communications.

## ADDED Requirements

### Requirement: Refresh once on invoice open only when communications changed
The frontend SHALL request summary refresh once per invoice opening. The system SHALL generate only if retained chat messages or email communications differ from the last successfully summarized source. Polling, prefetching, message writes, and inbound webhooks SHALL NOT generate summaries. New communication while an invoice stays open SHALL wait until the next opening.

#### Scenario: First opening with history
- **WHEN** an invoice with retained communications and no summary is opened
- **THEN** one refresh request generates and saves its cumulative summary

#### Scenario: Reopening unchanged history
- **WHEN** the invoice is reopened with the same saved communications
- **THEN** the saved summary is returned without an AI call

#### Scenario: New communication since the last summary
- **WHEN** the invoice is reopened after new chat messages or inbound/outbound email were saved
- **THEN** one refresh incorporates the new content and the earlier retained conversation

#### Scenario: Invoice remains open
- **WHEN** polling observes new communications or the owner sends a chat message while the invoice stays open
- **THEN** no additional AI summary generation occurs until another opening

#### Scenario: Prefetch or facts-only change
- **WHEN** history is prefetched or invoice facts change without a communication change
- **THEN** no AI summary generation occurs

### Requirement: Summary covers the retained conversation cumulatively
A summary SHALL account for all retained messages and communications through its source version, including material chronology, invoice/payment facts, objections, promises, decisions, and pending actions. It SHALL distinguish drafts, completed actions and unverified senders. Long histories SHALL NOT silently lose earlier material facts.

#### Scenario: Earlier promise and later objection
- **WHEN** the conversation contains an earlier promise to pay and a later amount dispute
- **THEN** the cumulative summary includes both in order with any retained dates

#### Scenario: Unsent draft and unverified reply
- **WHEN** a draft awaits approval and an unverified sender has replied
- **THEN** the summary identifies the draft as pending and attributes the reply as unverified

#### Scenario: Long history
- **WHEN** retained history exceeds one model context window
- **THEN** the summary still accounts for material facts from the beginning and end

### Requirement: Summary is persisted per invoice and returned with history
The system SHALL store one durable current summary row per invoice, with text, covered source version, generation time and refresh status. Invoice history SHALL include nullable `summary` and freshness metadata. Summary storage SHALL survive server restarts without modifying conversation state.

#### Scenario: Restart and reopen
- **WHEN** the backend restarts after saving a summary and history is read
- **THEN** it returns the saved summary and source metadata without a model call

#### Scenario: No successful summary
- **WHEN** history is read before a summary exists or when summary storage is unavailable
- **THEN** messages and approvals remain available with null summary and accurate metadata

### Requirement: Summary read and refresh API
POST `/api/invoices/{invoice_id}/summary` SHALL refresh from authoritative persisted sources, accepting no caller-authored summary or transcript. GET SHALL read without generating. A completed or empty result SHALL return 200; busy, failed or deferred generation SHALL return 202 with status. Empty conversations SHALL not invoke AI or invent history.

#### Scenario: Read and refresh
- **WHEN** an owner posts a refresh and then gets the saved summary
- **THEN** both return the invoice's summary text, source version, timestamp and status
- **AND** the GET performs no generation

#### Scenario: Empty invoice
- **WHEN** an invoice with no retained messages or communications is opened
- **THEN** summary is null with empty status and zero AI calls

### Requirement: Invoice ownership protects summaries
Summary reads and refresh SHALL enforce existing signed-in owner and guest invoice access rules before any summary read or AI call. Public database roles SHALL have no access to summary rows or refresh functions. Summary ownership SHALL follow the invoice when the guest signs in.

#### Scenario: Different owner or guest
- **WHEN** a different user or guest requests the invoice summary or history
- **THEN** access is denied without reading summary data or invoking AI

#### Scenario: Guest signs in
- **WHEN** a guest invoice is reassigned to their signed-in account
- **THEN** the same summary is available to that account under the invoice's current ownership

#### Scenario: Direct public database request
- **WHEN** anon or authenticated database roles request summary data or refresh functions
- **THEN** read/write access is denied

### Requirement: Concurrent opens deduplicate generation and preserve freshness
Concurrent refreshes SHALL coordinate across server instances. Unchanged sources SHALL reuse saved output. An outdated or expired worker SHALL NOT replace a newer saved summary. If communications change during generation, the result SHALL not claim to include them; new work SHALL wait for a later opening.

#### Scenario: Duplicate opening requests
- **WHEN** overlapping openings request a summary of the same source
- **THEN** at most one active generation runs and successful output is reused

#### Scenario: Communication arrives during generation
- **WHEN** a new message commits while an opening's summary runs
- **THEN** the system returns a stale/deferred result and does not launch a second generation for that opening

#### Scenario: Expired worker returns late
- **WHEN** a replacement worker has claimed or saved a summary after an old worker's lease expired
- **THEN** the expired worker cannot overwrite that result

### Requirement: Failure preserves existing summary and actions
Generation failure SHALL preserve the last successful summary, committed messages, and email/approval outcomes. It SHALL expose stale/failed status without leaking provider details. Expired work SHALL be retryable on a later opening without replaying any dispute action; no scheduled retry SHALL generate independently of opening.

#### Scenario: Timeout
- **WHEN** summary generation times out
- **THEN** the prior summary remains available as stale and chat remains usable
- **AND** a later opening can retry without resending chat or email

### Requirement: Summary generation cannot execute dispute actions
The summarizer SHALL treat all conversation text as untrusted data and SHALL have no dispute tools. It SHALL NOT send email, write agent messages or invoice business state, append summaries to chat, or consume a pending approval.

#### Scenario: Pending approval and injected instructions
- **WHEN** refresh runs with an approval pending and a reply containing instructions to send email or reveal other invoices
- **THEN** the approval remains actionable and no email or cross-invoice action occurs
