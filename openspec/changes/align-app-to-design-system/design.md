# Design

## Context

Tailwind 4 is already in use (`@import "tailwindcss"` plus an `@theme` block in `frontend/src/index.css`), so named tokens become utilities (`bg-coral`, `text-ink`) with no extra tooling. Today the theme holds only two font variables, and `* { font-family }` plus `h1..h6` rules apply Plus Jakarta Sans and Outfit to every screen; the landing opts back into Schibsted Grotesk through the `.lp` scope. Landing components use hex arbitrary classes (`#FF6B35` appears about 57 times); app components use Tailwind greys, emerald, violet, indigo and teal. See proposal.md for motivation and scope, and `openspec/changes/archive/2026-11-22-invoicechaser-paper-design-system/design.md` for how the token values were chosen.

## Goals / Non-Goals

**Goals:**
- One source of token values in code, equal to Paper, usable as Tailwind utilities.
- Every user-visible change is traceable to a decision recorded here.
- Work lands in small, independently shippable steps with the existing tests green after each.

**Non-Goals:**
- Automatic Paper-to-code sync or export tooling; tokens are copied by hand and the Foundations note says so.
- Dark mode.
- Restyling the generated invoice PDF templates.
- Layout or information-architecture changes to any screen.

## Decisions

**Tokens go into `@theme`, landing and app migrate together.** Add the 38 Paper tokens plus `coral-text` to `@theme` using Paper's exported names (`--color-coral`, `--color-ink`, ...). Then replace hex arbitrary classes mechanically (`text-[#111827]` to `text-ink`). *Alternative:* a separate CSS-variables file; rejected because Tailwind utilities would not exist for it.

**Remove `.lp` font scoping, make Schibsted global.** Set `--font-sans` to Schibsted Grotesk in `@theme` and drop the `* { font-family }` and `h1..h6` overrides, along with the `.lp` and `.lp-serif` special-casing (keep the serif accent through a `font-serif` utility). Remove the two Google font families from `index.html` and every `font-[family-name:var(--font-heading)]`. *Alternative:* keep Outfit for headings only; rejected by the user's decision to use one typeface.

**Ink label on coral.** Primary button = coral gradient with `text-ink`. Hover uses `coral-hover` as the gradient start; ink on `#F2551C` is 5.15:1, which clears 4.5 with little room, so the hover must not darken further. Measured: ink on `coral` 6.26, on `coral-2` 7.91, on `coral-hover` 5.15. The infinite `btn-gradient` shimmer is replaced by a static gradient with a hover shift. *Alternative:* darken the coral fill and keep white text; rejected by the user's decision.

**`coral-text` = `#C2410C`.** Used wherever coral is text on `page`, `card` or `tint`. Plain `coral` remains for fills, borders, icons and the focus ring. Measured: 4.89 on `page`, 4.99 on `card`, 4.68 on `tint`, so it clears 4.5 on all three but is tightest on `tint`. This is a default proposed by the exploration and is the one value the user has not yet confirmed; it can change without touching the specs because they state only the 4.5:1 floor.

**Approval treatment is a shared piece.** Extract the approval styles into one reusable class or small component used by `DraftApproval.tsx` (both approve buttons at the two call sites) and by the landing demo, so chat and landing cannot drift apart again. Green is left only on `paid`.

**Escalation levels use existing status pairs.** The per-level gradients in `DraftApproval.tsx` (emerald, blue/indigo, teal) are replaced by the status pairs: Level 1 neutral (`tint` and `muted`), Level 2 amber pair, Level 3 red pair. Intensity rises with the level, and no new hue is introduced. *Alternative:* a coral ramp; rejected because coral already means "needs your action".

**Distinguishing client replies without a hue.** Agent messages sit on `card` with a `line` border; client replies add a 4px `ink` left rule, a mail icon and the "Client reply" label. Tool-call chips are `tint` surface with `muted` text and a neutral icon.

**Radius, shadow, size scales.** Radius: map `[10px]` to `lg` and `[16px]` to `xl`, and `2xl` to `xl` unless a call site is a modal. Shadow: two tokens, `shadow-card` (subtle neutral) and `shadow-pop` (menus, modals); remove the tinted orange and emerald shadows. Text: no size below 12px; the 21 sub-12px uses go to `text-xs`.

**States.** One focus ring for the whole app: 2px `ink` outline with 2px offset on light surfaces (matching the landing's existing `.lp :focus-visible`), extended to the app. Disabled uses reduced opacity plus `cursor-not-allowed`. A single `@media (prefers-reduced-motion: reduce)` block disables the shimmer, pulse-dot, fade-up and middleware pulse animations.

**Order and testing.** Tokens in code first with no visual change; contrast and approval next (the user-visible fixes); then typeface, palette collapse, scales and states. Each phase keeps `npx vitest run` and `npm run lint` green and ends with a visual check in the browser against the Paper file. Where existing tests assert on removed class names or fonts, they are updated in the same phase as the code.

## Risks / Trade-offs

- [Ink-on-coral hover has only 0.65 of headroom over 4.5, and `coral-text` on `tint` only 0.18] → Hover keeps `coral-hover` as the gradient start and is not darkened further; a unit test computes contrast for the button states and for `coral-text` on all three surfaces.
- [Dropping Outfit changes heading width and may wrap titles in tight layouts such as the sidebar and stat cards] → Review each screen in the browser after the type phase; adjust size or `truncate` rather than reintroducing a second font.
- [Collapsing violet and indigo may make tool calls and client replies harder to scan in long chats] → The structural cues (left rule, icon, label) carry the distinction; check with a long real conversation before finishing the phase.
- [Mechanical hex-to-token replacement can touch the wrong shade] → Replace only exact matches of registered values, then grep for any remaining `#[0-9A-Fa-f]{6}` in `frontend/src` outside the allow-listed PDF templates.
- [Paper and code drift again] → Foundations carries "built by hand" with the date and commit, and the drift list is the place to record anything left behind.

## Migration Plan

Ship in the phases above as separate commits on one branch, each deployable on its own. Rollback is a normal revert of the phase commit, since there are no data or API changes. The font removal ships with its phase so a rollback restores the previous `index.html` and CSS together.
