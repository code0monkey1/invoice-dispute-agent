# landing-hero Specification

## Purpose

Defines what the landing hero shows next to the headline, so a visitor sees the agent working on an invoice without scrolling, and how that panel behaves across screen sizes and motion preferences.

## Requirements

### Requirement: Hero shows the animated agent run
The landing hero SHALL show the animated example agent run in its right-hand column on wide screens, beside the headline and calls to action, and SHALL NOT show a separate static illustration of the same story.

#### Scenario: Desktop hero
- **WHEN** a visitor opens the landing page on a screen at least 1024px wide
- **THEN** the headline and calls to action are on the left and the animated run, starting playback automatically, is on the right, with no static invoice-and-steps cards anywhere in the hero

#### Scenario: Run appears once
- **WHEN** a visitor scrolls the whole landing page
- **THEN** the example run appears exactly once, in the hero, and no second "See a full run on one invoice" section follows it

### Requirement: Hero run stacks on narrow screens
Below 1024px the hero SHALL stack the animated run under the headline and calls to action, and the run SHALL fit the viewport width with no horizontal scrolling.

#### Scenario: Phone hero
- **WHEN** a visitor opens the landing page on a 375px-wide screen
- **THEN** the run appears below the calls to action, every control and the draft's approve button is fully visible, and the page does not scroll sideways

### Requirement: Hero run stays an interactive, clearly labelled example
The hero run SHALL keep its existing behaviour: it can be paused, played and replayed, it waits at each email draft for the visitor to approve, and it states that it is an example and that nothing is actually sent.

#### Scenario: Approving a draft in the hero
- **WHEN** the run reaches an email draft and the visitor presses "Approve and send"
- **THEN** the draft shows "Approved by you" and the run continues to the next step

#### Scenario: Example label
- **WHEN** the hero run is shown at any step
- **THEN** its title includes "(example)" and its caption says nothing is actually sent

### Requirement: Hero run respects reduced motion
When the visitor's system requests reduced motion, the hero run SHALL NOT auto-play or animate between steps, and SHALL show the completed run.

#### Scenario: Reduced motion
- **WHEN** a visitor with "reduce motion" enabled opens the landing page
- **THEN** the hero run shows all steps at once with no entrance animations, and playback only advances if the visitor presses play
