# Tasks

## 1. Hero swap

- [x] 1.1 Write `frontend/src/components/__tests__/LandingPage.test.tsx` (router plus stubbed auth) asserting one "Agent run for INV-042" region, no second "See a full run" section, and, with reduced motion mocked, all 13 steps shown; run `cd frontend && npx vitest run LandingPage` and see it fail
- [x] 1.2 In `LandingPage.tsx`, render `<AgentRun />` in the hero's right column, remove the `HeroCards` import and the "Live example" section, and rebalance the grid columns; verify the 1.1 test passes
- [x] 1.3 Delete `frontend/src/components/landing/HeroCards.tsx`; verify `grep -rn HeroCards frontend/src` returns nothing and `npx vitest run` (including `architecture.test.ts`) passes

## 2. Fit the run to the column

- [x] 2.1 In `AgentRun.tsx`, mark the root as a container and switch width-dependent rules (legend, fields grid, date column, draft padding) to container-query variants; verify in a browser at 375px, 540px and 760px that nothing clips and the page has no horizontal scroll
- [x] 2.2 Replace the fixed log height with a viewport-clamped height; verify at 1440x800 that the headline, CTAs and the run header are all visible without scrolling, and that the log still auto-scrolls to the newest step
- [x] 2.3 Set `aria-live` to `off` on the step counter and thought bubble while auto-playing, `polite` once the visitor pauses, approves or replays; add a test asserting both states and verify it passes

## 3. Verify

- [x] 3.1 Run `cd frontend && npm run lint && npm run build && npx vitest run`; verify all pass with no new warnings
- [x] 3.2 Start the dev server (`npm run dev`) and walk the hero in a browser: auto-play, pause, replay, approve both drafts, then enable reduced motion and reload; compare against the Paper Page sample and the screenshot of the run, and confirm no static cards remain
