# Proposal

## Why

The Paper design system was built from the landing page, but the app screens (chat, dashboard, approval, trace) use a different palette and typefaces, and the system's own primary button and coral text fail WCAG contrast. The most important action in the product, approving an email, is green in the app and coral in the system. Tokens exist only in Paper, so nothing stops drift from recurring.

## What Changes

- Register the Paper tokens in code as named theme tokens in `frontend/src/index.css` (`@theme`), and replace repeated hex values with them.
- **Primary buttons**: keep the coral gradient, switch label colour from white to `ink` (about 6.3:1, up from 2.84:1 on coral).
- Add a `coral-text` token (default `#C2410C`) for coral used as text on page, card and tint surfaces; coral stays a fill and accent only.
- **Approval is coral**: the "Approve and send" actions in `DraftApproval.tsx` move from the emerald gradient to the system approval treatment. Green remains only for `paid`.
- **One typeface**: Schibsted Grotesk across the whole app; Source Serif 4 stays accent-only. Remove Outfit and Plus Jakarta Sans from `index.css`, `index.html` and all `font-[family-name:var(--font-heading)]` usages.
- **Collapse the app palette**: violet, indigo, teal and blue accents (tool-call chips, client replies, avatars, level colours) move to coral, ink and neutral. The client-reply distinction comes from structure (left rule, icon, label), not hue.
- Add radius and shadow scales (retire `[10px]`/`[16px]` outliers and tinted ad hoc shadows), a 12px minimum text size, and focus, hover, disabled and reduced-motion states.
- Update the Paper file to match (ink-on-coral buttons, `coral-text`, states) and shorten its drift list.
- **BREAKING (visual only)**: approve buttons change colour, all app text changes typeface, and tool-call and client-reply styling changes. No API or data changes.

## Capabilities

### New Capabilities
- `app-visual-system`: how the running app consumes the design system: tokens defined once in code, one typeface, coral approval treatment, contrast minimums, a restricted accent palette, state styles, and reduced motion.

### Modified Capabilities
- `design-system-reference`: primary button label is ink on coral; a `coral-text` token is registered; focus and disabled states are shown; the known-drift list covers only what this change leaves behind.

## Impact

- Frontend: `frontend/index.html`, `frontend/src/index.css`, and components using the drifted styles (`DraftApproval.tsx`, `MessageBubble.tsx`, `chat/*`, `TracePanel.tsx`, `Layout.tsx`, `Dashboard.tsx`, `InvoiceForm.tsx`, `InvoiceTable.tsx`, `Markdown.tsx`, `invoice-generator/*`, `landing/*`).
- Tests: existing vitest suites assert on some class names and text; the frontend architecture test must still pass.
- Paper: `InvoiceChaser — Design System` file (Foundations and Components artboards, one new token).
- Out of scope: the generated invoice PDF templates (`invoice-generator/pdf/`), which are customer-facing documents with their own template styling; backend; dark mode.
