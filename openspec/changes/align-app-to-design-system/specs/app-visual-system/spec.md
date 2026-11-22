# Spec Delta

## Purpose
Defines how the running InvoiceChaser app applies the design system: one set of tokens, one typeface, a coral approval treatment, readable contrast, a restricted accent palette, and consistent interaction states.

## ADDED Requirements

### Requirement: Tokens are defined once in code
The frontend SHALL define the design-system colour, type, radius and spacing tokens once as named theme tokens, with values equal to those in the `InvoiceChaser — Design System` Paper file, and app and landing styles SHALL use those tokens in place of repeated hex values.

#### Scenario: Token values match Paper
- **WHEN** a colour token such as coral, ink, line or coral-text is read from the frontend theme
- **THEN** its value equals the value of the token of the same name in the Paper file

#### Scenario: Changing a token
- **WHEN** a token value is changed in the theme
- **THEN** every surface that uses that role changes with it, with no per-component edit

### Requirement: One typeface across the app
Every app and landing screen SHALL render text in Schibsted Grotesk, with Source Serif 4 used only for accent phrases, and the application SHALL NOT load or reference Outfit or Plus Jakarta Sans.

#### Scenario: App heading and body text
- **WHEN** a heading or body text is rendered on any app screen
- **THEN** its computed font family is Schibsted Grotesk

#### Scenario: Font payload
- **WHEN** the page's font stylesheet is requested
- **THEN** it names only Schibsted Grotesk and Source Serif 4

### Requirement: Primary actions use ink text on coral
Primary buttons SHALL keep the coral gradient fill and SHALL render their label in the ink colour, with a contrast ratio of at least 4.5:1 against every colour in the gradient and against the hover fill.

#### Scenario: Primary button contrast
- **WHEN** a primary button is rendered in its default, hover and focus states
- **THEN** its label contrast against the fill is at least 4.5:1 in each state

#### Scenario: Disabled button
- **WHEN** a primary button is disabled
- **THEN** it is visibly distinct from the enabled state and is not reachable by keyboard activation

### Requirement: Coral text is readable
Coral used as text on a page, card or tint surface SHALL use the `coral-text` token, which has a contrast ratio of at least 4.5:1 against those surfaces, and the plain coral token SHALL be used only for fills, borders and icons.

#### Scenario: Approval label
- **WHEN** the "Needs your approval" label is rendered on the tint surface
- **THEN** its colour is `coral-text` and meets 4.5:1

### Requirement: Approval is the coral moment
Every control that approves or sends an agent-drafted email SHALL use the coral approval treatment, and green SHALL be used only for paid or success states.

#### Scenario: Approve and send button
- **WHEN** a pending draft is shown for approval in chat
- **THEN** its approve action uses the coral gradient with ink label and not a green fill

#### Scenario: Paid versus approval
- **WHEN** a paid status badge and an approve action are on the same screen
- **THEN** only the paid badge is green

### Requirement: Accent palette is restricted
App screens SHALL use only coral, ink, neutral, and the status pairs (green, red, amber) as colour, and SHALL NOT use violet, indigo, teal or blue accents.

#### Scenario: Client reply message
- **WHEN** an inbound client reply is shown in the chat
- **THEN** it is distinguished from agent messages by structure (rule, icon, label) in neutral or ink colours, not by a violet or indigo hue

#### Scenario: Tool-call chip
- **WHEN** a tool call is shown in the chat
- **THEN** it uses neutral surface and ink or muted text

### Requirement: Readable minimum text size
Body, label and chip text SHALL be at least 12px, and text below 12px SHALL NOT appear in app screens.

#### Scenario: Small labels
- **WHEN** a section label or chip is rendered
- **THEN** its computed font size is at least 12px

### Requirement: Interaction states are visible and respect motion preferences
Interactive elements SHALL show a visible keyboard focus ring, and continuous decorative animation SHALL be disabled when the user prefers reduced motion.

#### Scenario: Keyboard focus
- **WHEN** a button, link or input receives keyboard focus
- **THEN** a focus ring of at least 2px with contrast of at least 3:1 against its surroundings is visible

#### Scenario: Reduced motion
- **WHEN** the user's system requests reduced motion
- **THEN** the button shimmer, pulsing dots and fade-up entrance animations do not run
