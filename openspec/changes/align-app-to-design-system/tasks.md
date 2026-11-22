# Tasks

## 1. Tokens in code (no visual change)

- [x] 1.1 Add a contrast test (`frontend/src/__tests__/`) that parses the theme tokens from `index.css` and asserts the 4.5:1 floors for ink on coral, coral-2 and coral-hover and for coral-text on page, card and tint; verify it fails first because the tokens do not exist
- [x] 1.2 Add the 38 Paper tokens plus `--color-coral-text: #C2410C` to `@theme` in `frontend/src/index.css`, using the exported Paper names; verify the contrast test passes and `npm run build` succeeds
- [x] 1.3 Replace exact-match hex arbitrary classes in `components/landing/` with token utilities; verify with `grep` that no registered hex remains there and `npx vitest run` passes
- [x] 1.4 Replace exact-match hex arbitrary classes in the app components (`Layout`, `Dashboard`, `InvoiceTable`, `InvoiceForm`, `StatsCards`, `chat/*`, `TracePanel`, `Markdown`); verify `grep -rE '#[0-9A-Fa-f]{6}' frontend/src` lists only unregistered one-offs and the PDF templates, and tests pass

## 2. Contrast and approval

- [x] 2.1 Change primary buttons (landing demo button, `InvoiceForm`, chat send, approve actions) to ink label on the coral gradient and replace the infinite shimmer with a static gradient and hover shift; verify the contrast test covers the button states and a browser check shows readable labels
- [x] 2.2 Switch every coral-as-text use (such as the approval label and serif accent) to `coral-text` and leave plain `coral` for fills, borders and icons; verify with `grep` that no `text-coral` remains and the contrast test passes
- [x] 2.3 Extract one shared approval treatment and use it in both approve buttons in `DraftApproval.tsx` and the landing demo; update `DraftApproval` tests, and verify no emerald or green gradient remains on an approve action (`grep -n emerald components/DraftApproval.tsx`)
- [x] 2.4 Replace the per-level gradients in `DraftApproval.tsx` and `EscalationBadge.tsx` with the neutral, amber and red status pairs; verify a render test for Levels 1 to 3 and that green appears only for paid

## 3. One typeface

- [x] 3.1 Set Schibsted Grotesk as the global sans and Source Serif 4 as the serif accent in `@theme`; remove the `*` and `h1..h6` font rules and the `.lp` font scoping; verify the landing page still renders the same faces
- [x] 3.2 Remove all `font-[family-name:var(--font-heading)]` usages and the Outfit and Plus Jakarta Sans entries from `index.html`; verify `grep -rE "Outfit|Jakarta|font-heading" frontend` returns nothing and a test asserts the font stylesheet link names only the two kept families
- [x] 3.3 Review every screen in the browser (dashboard, chat, sidebar, stat cards, invoice generator) for heading wrap or overflow caused by the font change and fix with size or truncation; verify with screenshots of each screen

## 4. App palette collapse

- [x] 4.1 Restyle tool-call chips and the thinking/summary blocks in `MessageBubble.tsx` to neutral surface and muted text; verify the component test and that `grep -E "violet|indigo|purple" frontend/src` returns nothing
- [ ] 4.2 Restyle client-reply bubbles with an ink left rule, mail icon and "Client reply" label; verify a render test finds the label and rule and a browser check with a long conversation shows replies stay distinguishable
- [x] 4.3 Replace the teal and emerald agent avatar and any remaining teal or blue accents in `chat/*`, `TracePanel.tsx` and `Layout.tsx`; verify `grep -rE "teal|blue-|sky-" frontend/src` returns nothing outside the PDF templates

## 5. Scales and states

- [x] 5.1 Map `rounded-[10px]`, `rounded-[16px]`, `rounded-[12px]` and `rounded-2xl` onto the `lg` and `xl` radius tokens; verify `grep` finds no radius arbitrary values and tests pass
- [x] 5.2 Define `shadow-card` and `shadow-pop` tokens and replace the tinted orange and emerald shadows; verify no `shadow-orange` or `shadow-emerald` classes remain
- [x] 5.3 Raise every text size under 12px to `text-xs` and verify `grep -rE 'text-\[(9|10|11)px\]' frontend/src` returns nothing
- [x] 5.4 Add one app-wide `:focus-visible` ring (2px ink, 2px offset), disabled styling, and a `prefers-reduced-motion` block covering shimmer, pulse-dot, fade-up and middleware pulse; verify with a test that the reduced-motion rule exists and a keyboard tab-through shows the ring on buttons, links and inputs

## 6. Paper file

- [x] 6.1 Register the `coral-text` token in the Paper file and change primary button labels on Components and Page sample to ink; verify with `get_computed_styles` that the labels reference `--color-ink`
- [x] 6.2 Add default, hover, focus and disabled button states to the Components artboard and update the Foundations drift note and date/commit line; verify with screenshots and that no hardcoded colours were introduced

## 7. Integration

- [x] 7.1 Run `cd frontend && npm run lint && npx vitest run && npm run build` and the backend `pytest`; verify all pass
- [x] 7.2 Walk the live flow end to end (landing, sign in, create invoice, chat, approve a draft, view trace) in a browser and compare with the Paper artboards; verify no screen shows a removed font, hue or white-on-coral label

## Workflow follow-up

- Run `/opsx:archive` once the tasks are complete and the Paper file matches the shipped site.
- Sync the delta specs into `openspec/specs/` at archive.
