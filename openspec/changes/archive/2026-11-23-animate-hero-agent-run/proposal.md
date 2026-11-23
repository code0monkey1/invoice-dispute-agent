# Proposal

## Why

The landing hero shows a static three-card illustration (`HeroCards`) on the right, while the real animated agent run sits in a separate section below the fold. Visitors see the promise first and the proof only after scrolling, and the two panels tell the same story twice. Putting the animated run in the hero shows the product working at first glance.

## What Changes

- Render the animated agent run (`AgentRun`: the freelancer avatar with thought bubble, step progress bar, scrolling event log, pause and replay controls, and the approve-the-draft checkpoints) in the right column of the hero.
- Remove the static `HeroCards` component and its file.
- Remove the separate "See a full run on one invoice" section, since the run now lives in the hero; its caption ("You do 4 of the 13 steps. Nothing here is actually sent.") stays with the run.
- Fit the run to the hero's right column: on desktop it sits beside the headline and calls to action; on mobile it stacks below them. Its log height is tuned so the hero does not grow taller than the viewport on common laptop sizes.
- Behaviour of the run itself (script, timing, approve button, reduced-motion handling) is unchanged.

Out of scope: editing the Paper "Page sample" artboard (it still shows the static cards; update it separately if the design file should match), and any change to the run's script or copy.

## Capabilities

### New Capabilities
- `landing-hero`: what the landing hero shows beside the headline and how it behaves across breakpoints and motion preferences.

### Modified Capabilities
<!-- None. `design-system-reference` describes the Paper file's Page sample, not the shipped page. -->

## Impact

- `frontend/src/components/LandingPage.tsx`: hero grid, removal of the "Live example" section and the `HeroCards` import.
- `frontend/src/components/landing/HeroCards.tsx`: deleted.
- `frontend/src/components/landing/AgentRun.tsx`: sizing and layout tweaks so it fits the narrower column (the 13-segment progress bar, draft card and the 2-column field grid need checking at about 540px wide).
- Tests: add a frontend test for the hero; no backend, API or dependency changes.
