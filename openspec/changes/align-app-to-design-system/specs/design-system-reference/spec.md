# Spec Delta

## MODIFIED Requirements

### Requirement: Tokens come from the landing page
The file SHALL register colour, type, radius and spacing tokens whose values are the ones the landing page uses in `frontend/src`, plus a `coral-text` colour token for coral used as text, and SHALL NOT include Paper's default gray and blue scales.

#### Scenario: Comparing a colour token
- **WHEN** a token such as coral, ink or line is read from the Paper file
- **THEN** its value equals the hex the landing page uses for that role

#### Scenario: Coral as text
- **WHEN** the `coral-text` token is read
- **THEN** it is a darker coral whose contrast against the page, card and tint surfaces is at least 4.5:1, and the Foundations artboard says it is for text only

#### Scenario: One-off colours
- **WHEN** a colour appears in the code only once or twice and has no semantic role
- **THEN** it is not registered as a token

### Requirement: Known app-screen drift is recorded
The Foundations artboard SHALL list any app-screen styling that still departs from the system after the app has been aligned, and SHALL label it as known drift and not as part of the system.

#### Scenario: Reading the drift note
- **WHEN** a viewer reads the Foundations artboard
- **THEN** the drift list names only styling the app still uses outside the system (such as generated invoice PDF templates), and none of its colours or fonts is registered as a token

#### Scenario: Resolved drift
- **WHEN** a drift item such as the Outfit and Plus Jakarta Sans fonts or the violet and indigo accents has been removed from the app
- **THEN** it no longer appears in the drift list

### Requirement: Components artboard shows the core components
A Components artboard SHALL show the gradient demo button with an ink label, the secondary Google button, paid, overdue and escalated status badges, an invoice row, an agent-step row, and a draft-email approval card, each built from registered tokens, and SHALL show the primary button in its default, hover, focus and disabled states.

#### Scenario: Components use tokens
- **WHEN** a component's fill, text or border colour is inspected
- **THEN** it references a registered token and is not a hardcoded hex value

#### Scenario: Status badges
- **WHEN** the three status badges are shown
- **THEN** paid uses the green pair, overdue uses the red pair, and escalated uses the amber pair, each a foreground colour on its tinted background

#### Scenario: Primary button label
- **WHEN** the primary button is inspected
- **THEN** its label uses the ink token on the coral gradient, and the contrast is at least 4.5:1

#### Scenario: Button states
- **WHEN** the button states are shown side by side
- **THEN** default, hover, focus and disabled are all present and visibly different from one another
