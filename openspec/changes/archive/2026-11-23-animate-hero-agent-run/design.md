# Design

## Context

`LandingPage.tsx` renders a two-column hero grid (`lg:grid-cols-[1.1fr_0.9fr]`, container max 1180px) with copy on the left and `<HeroCards />` (static, `aria-hidden`) on the right. `AgentRun` is a self-contained component in its own section further down, capped at `max-w-[760px]`. In the right column (about 500 to 540px wide at 1180px) it is narrower than it was designed for. See proposal.md for motivation.

Constraints observed in `AgentRun.tsx`: the progress bar has 13 `flex-1` segments, the log is a fixed `h-[420px] sm:h-[440px]` scroller, and the avatar header uses an `sm:` legend that sits beside the thought bubble. The component has no props and no external dependencies, and no existing test references it.

## Goals / Non-Goals

**Goals:**
- Hero right column hosts `AgentRun`; the static cards and the duplicate section are gone.
- The run stays legible at 375px, about 540px (hero column) and 760px widths.
- Hero height stays reasonable so the headline and the top of the run are both visible on a 1440x800 laptop viewport.

**Non-Goals:**
- No change to the run's script, timings, copy or approve logic.
- No new animation library; existing CSS keyframes and `setTimeout` stepping stay.
- No Paper file edits.

## Decisions

**Reuse `AgentRun` as is, adjust only its layout.** Drop it into the grid cell in place of `HeroCards` and delete the wrapper section. *Alternative:* a new compact "HeroRun" variant; rejected because it would duplicate the script and drift from the real demo.

**Container-driven sizing, not breakpoint guesses.** The component currently switches layout on viewport `sm:`, but in the hero it is narrower than the viewport suggests. Where a layout choice depends on the component's own width (legend beside the bubble, 2-column field grid, date column width), use Tailwind 4 container queries (`@container` on the root, `@md:` variants) so it adapts to the column. *Alternative:* keep viewport breakpoints and tolerate cramped text at 1024 to 1200px; rejected after considering the draft card and fields grid at about 480px.

**Cap the log height with the viewport.** Replace the fixed 420/440px with `h-[clamp(320px,52vh,440px)]` so the run fits beside the headline on short laptop screens while the scroller still auto-follows the newest step.

**Grid proportions.** Change the hero columns to `minmax(0,1fr)_minmax(0,1fr)` (or `1fr 1.05fr`) so the run gets roughly 560px. Align it to the top with the headline (`items-start`), keeping the existing mobile stack order (copy first, run second) so the CTAs stay above the fold on phones.

**Accessibility.** Remove `aria-hidden` (it was only on the static cards). The run already has `role="region"` and `aria-labelledby`; it contains an `h2`, which in the hero follows the page `h1`, so keep it an `h2`. Its auto-advancing live region (`aria-live` on the step counter and thought bubble) will now be announced at page load, so set the thought bubble and step counter to `aria-live="off"` while auto-playing and keep `polite` only after the visitor interacts, to avoid a screen reader reading the demo continuously. Auto-play also needs the existing pause control reachable before the copy's CTAs in tab order only if it comes first in the DOM; keep DOM order copy then run.

**Test.** Add `LandingPage.test.tsx` using Testing Library (as in `ChatPanel.test.tsx`) with a router and a stubbed auth context. It asserts that exactly one region labelled "Agent run for INV-042" renders, that no "Approve and send" static card exists outside it, and, with `matchMedia` mocked for reduced motion, that all 13 steps are shown. `HeroCards.tsx` is deleted; the architecture test must still pass.

## Risks / Trade-offs

- [Hero becomes taller and heavier on mobile, pushing content below] → The run is under the CTAs on mobile; cap the log height and verify at 375px that CTAs stay above the fold.
- [Auto-playing motion competes with the headline for attention] → Keep the existing pause control, the reduced-motion behaviour, and the unchanged slow step timing.
- [Container-query utilities may not behave as expected with the project's Tailwind setup] → Verify in a browser at three widths; fall back to viewport breakpoints for any single rule that misbehaves.
- [Paper "Page sample" now differs from the shipped hero] → Called out as out of scope; update the Paper artboard in a follow-up if the design file should stay the reference.
- [Live-region change alters the demo's screen-reader experience] → Covered by a test on the `aria-live` attribute while playing.
