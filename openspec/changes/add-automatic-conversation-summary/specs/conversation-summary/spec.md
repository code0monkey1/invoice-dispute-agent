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

### Requirement: Summary first and conversation history on demand
Opening an invoice SHALL display its locally cached summary and retrieve only summary/compact invoice and approval data initially. The UI SHALL NOT request full conversation history on opening, hover, focus, or prefetch. Full history SHALL be retrieved only when the owner selects View conversation history. Active chat SHALL support delta responses without exposing earlier history implicitly.

#### Scenario: Opening with cached summary
- **WHEN** an invoice is opened with a locally cached summary
- **THEN** that summary appears immediately while the server checks its communication version
- **AND** unchanged communications cause no LLM call and no full history request

#### Scenario: Explicit history request
- **WHEN** the owner selects View conversation history
- **THEN** the complete retained chat and communications are retrieved and displayed
- **AND** loading or failure can be retried without invoking the summary model

#### Scenario: New chat while history is hidden
- **WHEN** the owner sends a message without requesting prior history
- **THEN** the current exchange and approvals are shown without retrieving or displaying earlier conversation history

### Requirement: Independently judged summary quality gate
The release SHALL include a repeatable synthetic summary golden set judged by an LLM from a different model family than the generator. At least 85% of cases SHALL receive a positive verdict with acceptable factual grounding, coverage, attribution and safety. Generation/judge failures SHALL count as failures; results and model identities SHALL be saved.

#### Scenario: Passing release evaluation
- **WHEN** the complete golden set is generated and independently judged
- **THEN** release passes only if at least 85% of all cases are positive and the models belong to different families

#### Scenario: Missing or unsafe judgment
- **WHEN** a judge response is missing, malformed or rates a material criterion below acceptable
- **THEN** the case fails even if a positive flag was supplied

### Requirement: Sequential summary evaluation preserves cumulative facts
The evaluation SHALL test update sequences using actual prior generated summaries and new communications. A different-family LLM judge SHALL assess checkpoints against cumulative authoritative history. A sequence SHALL pass only if every checkpoint passes. Complete single-summary, sequence and checkpoint cohorts SHALL each achieve at least 85%. Production refresh behavior SHALL remain unchanged.

#### Scenario: Withdrawn promises and corrected dates
- **WHEN** later updates withdraw a payment promise or correct its date
- **THEN** evaluation requires the summary to retain the earlier event while accurately identifying the current position and date

#### Scenario: Partial payments and older objections
- **WHEN** a sequence adds partial payments and successive unrelated updates
- **THEN** evaluation requires current paid/outstanding totals and retention of unresolved earlier objections through eight refreshes

#### Scenario: An intermediate checkpoint fails
- **WHEN** generation or judging fails at any checkpoint
- **THEN** that checkpoint and its sequence fail, and missing checkpoints cannot produce a passing run
- **AND** subsequent generation uses actual prior generated text and any uncovered source delta, without judge-authored repairs
