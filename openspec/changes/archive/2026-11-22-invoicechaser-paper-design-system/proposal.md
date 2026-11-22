# Proposal

## Why

InvoiceChaser's frontend has no token system. Styling lives in three layers that disagree: the landing page (hardcoded hex arbitrary classes, Schibsted Grotesk with Source Serif 4 as an accent), the app screens (Tailwind default greys/slates, Outfit and Plus Jakarta Sans, page `#FFF7F0`), and a legacy `index.css` (coral/teal/violet mesh, glows, shimmer). There is no shared reference to design against, so every new screen re-decides colour, type and radius.

## What Changes

- Create a new, separate Paper file named `InvoiceChaser — Design System` (one token set per Paper file; the chiranjeevthomas.com design-system file is not touched).
- Register tokens extracted from how the landing page is actually styled: colour, type, radius, spacing. The landing is the canonical look.
- Add a Foundations artboard (swatches with name and hex, type scale, radius, spacing, font-substitution note, and a record of known app-screen drift).
- Add a Components artboard: gradient demo button, secondary Google button, status badges (paid / overdue / escalated), invoice row, agent-step row in both an automatic state and a "needs your approval" state, and a draft-email approval card.
- Add a Page sample artboard composing the landing hero from those parts, keeping the freelancer face from `frontend/public/presenter/`.
- The system carries the product story: the agent runs the whole chase automatically; the human's only step is approving an email before it sends. The approval state is visually distinct from automatic steps.
- Out of scope: fixing app-screen drift (Tailwind greys, Outfit/Jakarta), CSS-to-Paper sync, code or token export, matching chiranjeevthomas.com, and any change under `frontend/src`.

## Capabilities

### New Capabilities
- `design-system-reference`: A Paper design file holding InvoiceChaser's tokens and core components so the visual system can be inspected and designed against without reading CSS.

### Modified Capabilities

None.

## Impact

- New Paper file only; no application code, API, or dependency changes.
- Source of truth for token values is `frontend/src` (landing components under `components/landing/`); the Paper file is built once and updated by hand, so it can drift from code over time.
- Uses the Paper MCP tools during the apply phase.
