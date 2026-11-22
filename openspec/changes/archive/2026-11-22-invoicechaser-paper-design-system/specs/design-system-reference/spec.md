# Spec Delta

## Purpose

A Paper design file that holds InvoiceChaser's design tokens and core components, so the visual system can be inspected and designed against without reading frontend CSS.

## ADDED Requirements

### Requirement: A dedicated Paper file holds the design system
The design system SHALL live in its own Paper file named `InvoiceChaser — Design System`, separate from every other Paper file.

#### Scenario: Finding the file
- **WHEN** the Paper files are listed
- **THEN** the list contains `InvoiceChaser — Design System`, and the `chiranjeevthomas.com — Design System` file has no new or changed artboards or tokens

### Requirement: Tokens come from the landing page
The file SHALL register colour, type, radius and spacing tokens whose values are the ones the landing page uses in `frontend/src`, and SHALL NOT include Paper's default gray and blue scales.

#### Scenario: Comparing a colour token
- **WHEN** a token such as coral, ink or line is read from the Paper file
- **THEN** its value equals the hex the landing page uses for that role

#### Scenario: One-off colours
- **WHEN** a colour appears in the code only once or twice and has no semantic role
- **THEN** it is not registered as a token

### Requirement: Foundations artboard shows the primitives
A Foundations artboard SHALL show every colour token as a swatch labelled with its name and hex, the type scale in the UI and accent faces, the radius values, and the spacing scale.

#### Scenario: Reading the palette
- **WHEN** a viewer opens the Foundations artboard
- **THEN** each colour token appears once with its name and hex, grouped as brand, ink, surface, line and status

### Requirement: Known app-screen drift is recorded
The Foundations artboard SHALL list the app-screen styling that departs from the landing page, naming Tailwind default greys and the Outfit and Plus Jakarta Sans fonts, and SHALL label it as known drift and not as part of the system.

#### Scenario: Reading the drift note
- **WHEN** a viewer reads the Foundations artboard
- **THEN** the drift list is present and none of its colours or fonts is registered as a token

### Requirement: Components artboard shows the core components
A Components artboard SHALL show the gradient demo button, the secondary Google button, paid, overdue and escalated status badges, an invoice row, an agent-step row, and a draft-email approval card, each built from registered tokens.

#### Scenario: Components use tokens
- **WHEN** a component's fill, text or border colour is inspected
- **THEN** it references a registered token and is not a hardcoded hex value

#### Scenario: Status badges
- **WHEN** the three status badges are shown
- **THEN** paid uses the green pair, overdue uses the red pair, and escalated uses the amber pair, each a foreground colour on its tinted background

### Requirement: Approval is visually distinct from automatic steps
The agent-step row SHALL be shown in an automatic state and in a "needs your approval" state, and the approval state SHALL differ from the automatic state in more than text.

#### Scenario: Comparing the two states
- **WHEN** both agent-step rows are shown side by side
- **THEN** the approval row has a distinct fill, border or accent from the automatic row, and a viewer can tell which one needs action without reading its label

#### Scenario: Approval card
- **WHEN** the draft-email approval card is shown
- **THEN** it presents the draft with an approve action, using the same approval treatment as the approval step row

### Requirement: Page sample proves the parts compose
A Page sample artboard SHALL compose the landing hero from the Components artboard's parts using only registered tokens, and SHALL include the freelancer face from `frontend/public/presenter/`.

#### Scenario: Landing hero
- **WHEN** a viewer opens the Page sample artboard
- **THEN** it shows the hero with the freelancer image, the gradient demo button and the agent steps, with no hardcoded colours

#### Scenario: Product story
- **WHEN** the Page sample is read top to bottom
- **THEN** it conveys that the agent runs the chase automatically and the user's only step is approving an email

### Requirement: Substituted fonts are disclosed
If Schibsted Grotesk or Source Serif 4 is not available to Paper, the file SHALL use substitute fonts and say so on the Foundations artboard.

#### Scenario: Font unavailable
- **WHEN** Paper cannot load Schibsted Grotesk or Source Serif 4
- **THEN** the Foundations artboard carries a note naming each substituted font and its replacement
