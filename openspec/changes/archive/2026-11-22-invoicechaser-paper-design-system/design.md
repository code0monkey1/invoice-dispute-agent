# Design

## Context

The landing page (`frontend/src/components/landing/`) styles with hardcoded hex arbitrary classes; there are no named tokens in the CSS to copy. Token values therefore have to be extracted from usage and decided, not mirrored. See proposal.md for motivation and scope.

Hex counts across `frontend/src` (case-folded) that drive the token decisions: `#FF6B35` 64, `#6B7280` 54, `#F1E4D8` 46, `#111827` 43, `#1F7A55` 16, `#FF8F65` 11, `#374151` 10, `#B3261E` 8, `#FFFAF5` 6, `#FFF7F0` 6, `#FFF1E6` 6, `#F6EDE3` 5, then a long tail of 1-3 use colours. Radius: `rounded-xl` 40, `rounded-lg` 39, `rounded-full` 36, with `[10px]`, `2xl` and `[16px]` around 10 each. Common spacing: `px-4` 21, `px-5` 12, `gap-2` 13, `gap-4` 10, `gap-3` 8. The landing demo button is a left-to-right gradient from `#FF6B35` to `#FF8F65`, with `#F2551C` as the hover start. `components/landing/AgentRun.tsx` already models steps with a `who` of `you` or the agent and a `DraftCard` with an approve action, so the "automatic vs needs your approval" story has a real source.

## Goals / Non-Goals

**Goals:**
- A token set small enough to hold in your head, where every token has a clear role.
- Components that reference tokens only, so a token edit propagates through the file.
- An approval state that is recognisable at a glance.

**Non-Goals:**
- Reconciling app screens with the landing; they are listed as drift only.
- Keeping Paper and code in sync, or exporting tokens to CSS or Tailwind.
- Reproducing the legacy `index.css` mesh, glow and shimmer effects.

## Decisions

**Token inclusion rule.** Register a colour if it has 5 or more uses, or a semantic role. Anything else is a one-off. *Alternative:* register every hex seen (about 45); rejected because it reproduces the drift instead of resolving it.

**Colour tokens (confirm values against code at apply time):**
- Brand: `coral` #FF6B35, `coral-2` #FF8F65 (gradient partner), `coral-hover` #F2551C. The last has only 3 uses but is the hover end of the primary gradient, so it earns a token by role.
- Ink: `ink` #111827, `body` #374151, `muted` #6B7280.
- Surface: `page` #FFF7F0, `card` #FFFAF5, `tint` #FFF1E6.
- Line: `line` #F1E4D8, `line-2` #E9D9C8 (stronger border, 3 uses, kept as the second line tier).
- Status, kept as foreground/background pairs because the set has a role: green #1F7A55 on #E7F4EC, red #B3261E on #FBE8E6, amber #A35E00 on #FDF1DE. Each background has only 2 uses; the pair is registered together.
- Dropped as one-offs: #FDEBDD, #C9B8A6, #FFE9DF, #FFCFB8, #E55A2B, #B4410E, Google brand colours, and the 1-use tail. `#F6EDE3` (5 uses) is the one borderline value: check which surface it sits on during apply and either register it as `surface-2` or record it as drift.

**Type.** Schibsted Grotesk for UI, Source Serif 4 for accent only, matching the landing. Outfit and Plus Jakarta Sans appear only in app screens and go in the drift list. If Paper lacks either font, substitute and disclose on Foundations (spec requirement).

**Radius.** `lg` for buttons and inputs, `xl` for cards, `full` for pills. Confirm pixel values from Tailwind's defaults (8, 12, 9999) and note the `[10px]`/`[16px]` outliers as near-duplicates of lg/xl.

**Spacing.** Register a short scale from observed usage (4, 8, 12, 16, 20, 32) rather than the full Tailwind ladder.

**Approval treatment.** Automatic steps use `card` with a `line` border and `muted` text. The "needs your approval" step uses a coral-tinted fill (`tint`) with a `coral` border and the gradient button inside. Colour and weight, not just a label, mark it as the human's only action. The draft-email approval card reuses the same treatment.

**Build order.** Tokens first, then Foundations, Components, Page sample, so each later artboard can only use tokens that already exist. *Alternative:* build Components with raw hex and tokenise afterward; rejected because it risks hardcoded values surviving.

**Freelancer face.** Use one of `frontend/public/presenter/*.jpg` in the Page sample, as the landing does. Paper image fills need the file imported; fall back to a placeholder frame only if import fails, and say so.

## Risks / Trade-offs

- [Paper and code drift apart, since there is no sync] → State "built once, updated by hand" on Foundations with the date and source commit.
- [Low-count tokens may be accidental values] → Each is checked against its call site at apply time; a token with no real use is demoted to drift.
- [Font substitution changes the look] → Disclosed on Foundations; layout is built to tolerate similar-width fonts.
- [Treating the landing as canonical leaves app screens off-system] → Recorded as known drift, with a follow-up change as the place to fix it.
