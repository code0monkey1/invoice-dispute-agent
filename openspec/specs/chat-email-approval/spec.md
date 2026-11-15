# chat-email-approval Specification

## Purpose

Lets invoice owners prepare and send supported invoice emails from ordinary chat requests through the existing review card, with accurate state and explicit approval before delivery.

## Requirements

### Requirement: Explicit owner email requests produce an actionable review card
An eligible owner request to prepare or send a supported invoice email SHALL return its review card instead of only a prose template or instructions to use an external email client. Supported contextual follow-ups SHALL resolve to the referenced email. Ambiguous requests SHALL receive clarification without an unrelated draft.

#### Scenario: Final notice at Legal level
- **GIVEN** an open Legal-level invoice eligible for a new final notice
- **WHEN** its owner requests the final notice through chat
- **THEN** an editable final-notice review card is displayed with an explicit approval action
- **AND** no email has been sent

#### Scenario: Follow-up after a prose-only draft
- **GIVEN** an earlier assistant response contains a final-notice template without a review card
- **WHEN** the owner says “let's send it as a mail” or requests the chat email facility
- **THEN** the referenced supported email is prepared as a review card
- **AND** the assistant does not repeat copy-and-paste instructions as a substitute

#### Scenario: Supported email at another level
- **WHEN** the owner requests a delivery email, friendly reminder or formal demand available at the current level
- **THEN** the corresponding existing email review card is displayed

#### Scenario: Ambiguous reference
- **WHEN** “send it” has no identifiable supported email context
- **THEN** the assistant asks which email to prepare without selecting an unrelated notice

#### Scenario: Required invoice details are missing
- **WHEN** required recipient or invoice details are unavailable
- **THEN** the assistant requests the missing information without presenting an unusable or fabricated card

### Requirement: Email preparation never bypasses human approval
Preparing a draft SHALL NOT deliver email. Delivery SHALL require the existing explicit approval action and SHALL retain current recipient authorization, duplicate-send protection and delivery-result reporting. Rejection, clarification or a chat request alone SHALL NOT count as approval.

#### Scenario: Approve versus reject
- **WHEN** the owner approves an email card
- **THEN** the approved content is submitted once through the existing authorized sending flow
- **AND** rejecting a card sends nothing

#### Scenario: Gmail unavailable
- **WHEN** approval cannot deliver because Gmail is disconnected or sending fails
- **THEN** the result accurately reports that nothing was sent
- **AND** no successful outbound delivery is recorded

### Requirement: Conditional requests respect recorded delivery
A request to send only if not already sent SHALL check successful outbound records for the relevant email type. A recorded delivery SHALL be reported without creating a duplicate proposal for that conditional request. An explicit new send or resend request SHALL prepare a review card and disclose the earlier delivery.

#### Scenario: Final notice was already delivered
- **GIVEN** a successful final-notice delivery exists
- **WHEN** the owner asks to send the final notice “if not already sent”
- **THEN** the assistant reports the recorded delivery and does not create or send a duplicate

#### Scenario: Explicit resend
- **GIVEN** the final notice was already delivered
- **WHEN** the owner explicitly requests another final-notice draft or resend
- **THEN** a review card is shown with the previous-delivery information
- **AND** the resend still waits for approval

#### Scenario: Earlier claim or failure is not delivery
- **WHEN** only a prose claim, unsent proposal or failed send exists
- **THEN** it is not treated as a successful delivery that suppresses an eligible draft

### Requirement: Pending cards survive reads and repeated preparation requests
An existing pending email card SHALL remain available until a user decision. Reopening, polling or requesting the same pending draft SHALL preserve that card without replacing it or creating duplicate proposals. Card retrieval SHALL work while full conversation history is hidden.

#### Scenario: Reopen with hidden history
- **GIVEN** an email review card is pending
- **WHEN** the owner reopens the invoice without requesting full history
- **THEN** the pending card is visible and actionable from compact invoice data

#### Scenario: Repeated request
- **WHEN** the owner repeats a request for the same pending email
- **THEN** the existing card is returned without an additional proposal or delivery

### Requirement: Draft figures and attachment information are truthful
The preview SHALL use current stored invoice figures and the authorized recipient. It SHALL NOT claim a file is attached without supported attachment data. Missing or unsupported requested attachments SHALL be explained outside the editable email body while keeping the draft reviewable. This change SHALL preserve existing attachment-delivery support.

#### Scenario: Current figures differ from earlier prose
- **WHEN** the earlier prose contains outdated payment figures
- **THEN** the card uses current total, amount paid and outstanding balance

#### Scenario: Requested PDF is absent
- **GIVEN** no invoice file is uploaded
- **WHEN** the owner requests a notice with the invoice attached
- **THEN** the card clearly indicates that no invoice attachment is included
- **AND** neither the draft nor assistant claims a PDF is ready or attached

#### Scenario: Attachment type is unsupported for the selected email
- **WHEN** a requested attachment cannot be included by the existing selected-email flow
- **THEN** the limitation is disclosed before approval without promising delivery of that attachment

### Requirement: Preparation respects trust and escalation boundaries
Only authorized owner chat actions SHALL activate mandatory email preparation. Client replies, quoted instructions, summaries, legal-research-only questions and historical assistant text SHALL NOT independently trigger it. The selected email SHALL remain subject to current escalation and settled-invoice restrictions.

#### Scenario: Untrusted client instruction
- **WHEN** a client reply instructs the assistant to send a final notice or bypass approval
- **THEN** it does not activate the trusted-owner preparation path or send email

#### Scenario: Informational question
- **WHEN** the owner asks for a summary or legal-process explanation without requesting an email
- **THEN** normal answering or research behavior is preserved without an unrelated email card

#### Scenario: Unavailable action
- **WHEN** a requested notice is unavailable at the current level or the invoice is settled
- **THEN** the limitation is explained without unauthorized escalation, preparation or delivery

### Requirement: Preparation failures are explicit and bounded
If an eligible draft cannot be prepared, the request SHALL return a clear recoverable preparation failure within existing request limits. It SHALL NOT invent a functional composer, fabricate an approval card from arbitrary prose, claim delivery or retry indefinitely. Diagnostics SHALL identify the preparation outcome without exposing credentials.

#### Scenario: Provider does not return a valid draft action
- **WHEN** the provider fails or returns no valid required action
- **THEN** the owner receives an actionable retry/error result and no false send confirmation

### Requirement: Required regression checks cover the real card contract
Release checks SHALL exercise explicit and contextual email requests, including prior prose-only replies. Cases expecting an email approval SHALL require the correct review card and zero delivery before approval. Missing or failed structural card checks SHALL block release independently of aggregate quality scores.

#### Scenario: Prose-only response fails the gate
- **WHEN** a critical email-preparation case receives only a template and no card
- **THEN** the required regression gate fails even if tone or aggregate scores pass

#### Scenario: Isolated approval test
- **WHEN** automated regression tests approve a prepared card
- **THEN** only a fake email outbox receives the approved content and no real Gmail client is constructed
