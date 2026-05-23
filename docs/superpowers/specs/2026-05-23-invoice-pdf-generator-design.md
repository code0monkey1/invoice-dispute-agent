# Invoice PDF Generator Design

**Date:** 2026-05-23
**Status:** Approved

## Overview

Add an **Invoice Generator** module to InvoiceChaser that lets a freelancer create a polished PDF invoice from a form, pick one of three visual templates, preview it live, embed a payment link (Stripe / LemonSqueezy / PayPal / any URL), and download the PDF. The generated invoice is persisted to the existing `invoices` table so it flows straight into the chase pipeline if the client doesn't pay.

The feature is **client-side first**: PDF rendering happens in the browser with `@react-pdf/renderer`, the rendered blob is uploaded to Supabase Storage, and the invoice record is created via the existing backend API. No new server-side PDF rendering is introduced.

## Goals

1. **Form-driven invoice creation** — sender info, client, line items, totals, payment link, notes — all in one flow.
2. **Three distinct templates** — Modern, Classic, Minimal — selectable via a thumbnail picker with live preview.
3. **Payment link support** — any `https://` URL (Stripe / LemonSqueezy / PayPal / Wise / etc.), rendered per-template (button / hyperlink / underlined link).
4. **Download the PDF** — direct browser download via Blob URL.
5. **Persist to the chase pipeline** — saved invoices appear in the Dashboard alongside uploaded ones, ready to be chased.
6. **Per-user sender profile** — business name, logo, address, tax ID persist across invoices so the second invoice takes 30 seconds, not 5 minutes.
7. **TDD discipline** — every unit lands with tests written first, covering happy path and edge cases. The feature is not "done" until tests pass and verification commands confirm it.
8. **Landing page coverage** — add the new capability to the marketing copy so prospects know it exists.

## Non-Goals (YAGNI)

- **Word / DOCX output.** Invoices are final documents; clients pay them, they don't redline them. Future work.
- **Multi-currency math / FX conversion.** One currency per invoice.
- **Per-line tax rates.** One tax rate for the whole invoice.
- **Recurring / scheduled invoices.** Out of scope.
- **In-app payment processing.** We don't integrate with Stripe/LemonSqueezy APIs — the user pastes their own checkout URL.
- **Server-side PDF rendering.** No WeasyPrint, no headless Chrome. All rendering is in the browser.
- **Editing a previously generated invoice.** v1 supports create-and-download; if you want to change something, generate a new one. (We do, however, store the source data so edit-and-regenerate is straightforward to add later.)
- **Custom templates / theme editor.** Three fixed templates with an accent-color picker on Modern only.

## User Flow

```
Dashboard
    │
    ├── [Create invoice ▼]  ← split button on the existing "+ New" CTA
    │       ├── Chase an existing invoice  → current upload flow
    │       └── Generate a new invoice     → /generate-invoice  ★ NEW
    │
    └── /generate-invoice  (new page)
            │
            ├── Step 1 — Pick a template (3 thumbnails: Modern / Classic / Minimal)
            ├── Step 2 — Fill the form (sender pre-filled from profile, client, items, totals, payment link, notes)
            │            ↕ live PDF preview on the right (or below on mobile)
            └── Step 3 — Actions
                  ├── [Download PDF]          → triggers Blob download, no persistence
                  ├── [Save & Download]       → uploads PDF to Supabase Storage,
                  │                             creates `invoices` row,
                  │                             downloads the file,
                  │                             redirects to /invoice/<new-id>
                  └── [Cancel]                → back to dashboard
```

The chase agent is **not** triggered automatically on generation. The invoice lands in the dashboard at `escalation_level: 0` and starts the chase only when the user opens it and chats with the agent — same as upload today.

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                          Frontend                               │
│  React 19 + Vite + Tailwind 4                                  │
│                                                                 │
│  components/invoice-generator/                                  │
│    ├── InvoiceGeneratorPage.tsx        (route container)        │
│    ├── TemplatePicker.tsx              (3-thumbnail selector)   │
│    ├── InvoiceGeneratorForm.tsx        (the form)               │
│    ├── LineItemsEditor.tsx             (add/remove rows)        │
│    ├── PDFPreview.tsx                  (<PDFViewer> wrapper)    │
│    ├── SenderProfileSection.tsx        (sender fields)          │
│    ├── pdf/                            (PDF document tree)      │
│    │     ├── ModernTemplate.tsx                                 │
│    │     ├── ClassicTemplate.tsx                                │
│    │     ├── MinimalTemplate.tsx                                │
│    │     ├── shared/                                            │
│    │     │     ├── formatCurrency.ts                            │
│    │     │     ├── formatDate.ts                                │
│    │     │     └── computeTotals.ts                             │
│    │     └── index.ts                  (template registry)      │
│    └── __tests__/                      (Vitest test files)      │
│                                                                 │
│  hooks/                                                         │
│    ├── useInvoiceGeneratorForm.ts      (form state machine)     │
│    └── useSenderProfile.ts             (fetch/update profile)   │
│                                                                 │
│  api.ts (extended)                                              │
│    ├── api.getSenderProfile()                                   │
│    ├── api.updateSenderProfile()                                │
│    ├── api.uploadGeneratedInvoice()                             │
│    └── api.createGeneratedInvoice()                             │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                       FastAPI Backend                            │
│  api/index.py (extended — no new files)                          │
│    ├── GET    /api/users/me/sender-profile                       │
│    ├── PATCH  /api/users/me/sender-profile                       │
│    ├── POST   /api/invoices/generated      ← create-from-form    │
│    │           accepts JSON + pre-signed Supabase Storage path   │
│    │           creates invoices row with invoice_file_path set   │
│    └── (existing endpoints unchanged)                            │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                          Supabase                                │
│                                                                  │
│  Tables:                                                         │
│    ├── users          (extended with sender_profile JSONB)       │
│    ├── invoices       (existing — used as-is)                    │
│    └── communication_history (existing — unused for v1)          │
│                                                                  │
│  Storage:                                                        │
│    └── invoice-files/  (bucket — already exists for uploads;      │
│                        new "generated/" prefix for our outputs)  │
└──────────────────────────────────────────────────────────────────┘
```

### Why client-side PDF rendering

- **Live preview is the UX feature.** Without it, a template picker is guesswork.
- **One rendering path.** No HTML-preview / PDF-output drift.
- **No serverless cold-start pain.** WeasyPrint on Vercel needs system fonts and a chunky binary; we avoid it entirely.
- **Backend stays focused.** Backend never renders PDFs — it only stores rows and serves files from Supabase Storage.

## Data Model

### Database changes

**One additive migration** (`supabase/schema.sql`):

```sql
-- Add per-user sender profile (re-used across all invoices the user generates).
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS sender_profile JSONB DEFAULT '{}'::jsonb;
```

Shape of `sender_profile` (validated by Pydantic on PATCH):

```json
{
  "business_name": "string",
  "your_name": "string",
  "your_email": "string",
  "address": "string (multi-line)",
  "logo_url": "string (Supabase Storage URL, optional)",
  "tax_id": "string (optional)"
}
```

The existing `invoices` table requires **no schema change** — generated invoices reuse:
- `invoice_id`, `client_name`, `client_email`, `invoice_amount` (= total)
- `days_overdue` (computed from due date on create, recomputed nightly is already a TODO elsewhere)
- `jurisdiction` (defaulted to user's country from profile; user can edit)
- `invoice_file_path`, `invoice_file_name`, `invoice_file_mime`, `invoice_file_size` (the generated PDF in Supabase Storage)
- `escalation_level: 0` (default)
- `status: "outstanding"` (default)

We do **not** persist the line-items / tax / payment-link breakdown in v1 — the PDF is the source of truth for those. If the user wants to regenerate from the same data later, that's future work and would land in a new `generated_invoice_source` table.

### Storage layout

```
invoice-files/
  ├── <existing layout for uploaded invoices — unchanged>
  └── generated/<user_id>/<invoice_id>-<uuid>.pdf      (new generator output)
```

Filename is `<slugified-invoice_id>-<uuid>.pdf`. The UUID suffix makes collisions impossible without a probe-before-write round-trip.

## Templates Specification

All three templates render from the same data shape (`InvoiceData`). They differ only in typography, spacing, color, and the payment-link treatment.

### Shared data shape

```ts
type InvoiceData = {
  sender: SenderProfile;
  client: { name: string; email: string; address?: string };
  meta: {
    invoice_number: string;
    issue_date: string;     // ISO yyyy-mm-dd
    due_date: string;       // ISO yyyy-mm-dd
    currency: 'USD' | 'EUR' | 'GBP' | 'INR' | 'CAD' | 'AUD';
  };
  line_items: Array<{ description: string; quantity: number; unit_price: number }>;
  tax_rate_pct?: number;             // 0..100, optional
  discount?: { kind: 'flat' | 'pct'; value: number };  // optional
  payment?: { url: string; label?: string };           // optional
  payment_instructions?: string;     // multi-line, optional
  notes?: string;                    // multi-line, optional
  template: 'modern' | 'classic' | 'minimal';
  accent_color?: string;             // only honored by Modern template
};
```

### Template 1 — Modern

- **Type**: Inter (Regular 11pt, Bold 14pt, Bold 22pt for invoice number)
- **Color**: accent band across the top (40px tall). User-selectable: `#FF6B35` (default, brand orange), `#0ea5e9` (sky), `#10b981` (emerald), `#8b5cf6` (violet).
- **Layout**: business block + logo top-left; "INVOICE #1234" large on the right.
- **Line items**: clean table, alternating row tint at 4% opacity of accent.
- **Payment block**: filled rounded-rectangle button (`PAY INVOICE →`), accent color background, white text.
- **Best for**: tech freelancers, designers, agencies.

### Template 2 — Classic

- **Type**: Lora (Bold 16pt headings), Inter (Regular 11pt body), all-caps small-caps for section labels.
- **Color**: pure black on white. No accent.
- **Layout**: business name centered at top in caps, full address below; "Invoice" small-caps label, number large on the right.
- **Line items**: full-bordered table, double-rule above and below the total row.
- **Payment block**: plain labeled hyperlink → `Pay online: https://buy.stripe.com/abc123` rendered as underlined blue.
- **Best for**: lawyers, accountants, consultants.

### Template 3 — Minimal

- **Type**: Inter throughout. 10pt body, 28pt invoice number.
- **Color**: pure black on white. No borders, no fills.
- **Layout**: all left-aligned, generous vertical whitespace. "INVOICE" as a small caption above the number.
- **Line items**: borderless list — description left, quantity × unit price center, total right; totals row separated by a thin horizontal rule.
- **Payment block**: single underlined link at the bottom: `Pay this invoice →` linking to the URL.
- **Best for**: freelancers who want their work to speak.

### Cross-cutting rules

- If `payment.url` is empty/missing, the entire payment block is **omitted**. No empty "Pay: [blank]".
- If `payment_instructions` is provided, it renders below the payment link in all templates as a small-text paragraph.
- If `notes` is provided, it appears as the very last block, below "Thank you for your business" in Modern/Classic, and in pure paragraph form in Minimal.
- Logo (if uploaded) appears in **Modern** and **Classic**; **Minimal** never renders a logo (by design — that's the aesthetic).
- We **do not validate** the payment URL provider. Any `https://...` is accepted. We do validate the URL is syntactically well-formed (`new URL(value)` parses without throwing) before allowing save.

## Form Fields

(Per the brainstorm — captured here for the implementer.)

```
SENDER (your business)
  ├─ Business name           required
  ├─ Your name               required
  ├─ Your email              required (must parse as email)
  ├─ Address                 optional, multi-line
  ├─ Logo                    optional, image upload, max 2 MB, png/jpg/webp
  └─ Tax ID / VAT number     optional

CLIENT
  ├─ Client name             required
  ├─ Client email            required (must parse as email)
  └─ Client address          optional, multi-line

INVOICE META
  ├─ Invoice number          required, auto-suggested (e.g. "INV-2026-001")
  ├─ Issue date              required, defaults to today
  ├─ Due date                required, must be >= issue date
  └─ Currency                required, dropdown: USD/EUR/GBP/INR/CAD/AUD

LINE ITEMS  (≥ 1 row)
  Each: description (required), quantity (number > 0), unit price (number ≥ 0)
  Line total auto-computed = quantity × unit_price (display only)

TOTALS  (computed, read-only)
  ├─ Subtotal                sum of line totals
  ├─ Tax rate %              optional, 0..100, default 0
  ├─ Discount                optional, kind ∈ {flat, pct}, value ≥ 0
  └─ Total                   subtotal − discount + (subtotal − discount) × (tax_rate / 100)

PAYMENT
  ├─ Payment link URL        optional, must parse as URL and start with http(s)://
  ├─ Payment link label      optional, defaults to "Pay invoice"
  └─ Payment instructions    optional, multi-line free text

NOTES
  └─ Notes / terms           optional, multi-line free text
```

### Totals math (the canonical formula)

```
subtotal = Σ (line.quantity × line.unit_price)

discount_amount =
   discount.kind == 'flat' ? min(discount.value, subtotal)
 : discount.kind == 'pct'  ? subtotal × (discount.value / 100)
 : 0

taxable     = max(0, subtotal − discount_amount)
tax_amount  = taxable × (tax_rate_pct / 100)
total       = taxable + tax_amount
```

All amounts are stored as **integer cents** internally, displayed with the appropriate locale + currency symbol. Floats are never used for money.

## Payment Link Handling

- Accepted: any URL that `new URL(value)` parses **and** whose protocol is `http:` or `https:`.
- Rejected: malformed strings, `javascript:` and other non-http(s) protocols, and the empty string when "include payment block" is enabled.
- The link is rendered in the PDF as a real PDF link annotation (clickable in any PDF viewer), not just colored text. `@react-pdf/renderer`'s `<Link src={...}>` handles this.
- Anchor text rules:
  - Modern: button label = `payment.label ?? "PAY INVOICE →"`.
  - Classic: prefixed inline label = `"Pay online: " + payment.url` (URL visible — formal convention).
  - Minimal: link text = `payment.label ?? "Pay this invoice →"`.

## Landing Page Integration

Add **one new feature card** to the existing `features` array in `frontend/src/components/LandingPage.tsx`, slotted **before** the existing "Just drop the invoice PDF" card (because creating comes before chasing in the user's journey):

```tsx
{
  icon: <FilePlus className="w-5 h-5" />,
  title: 'Create polished invoices in seconds',
  desc: 'Skip the spreadsheet. Pick from three professionally designed templates, add your Stripe or LemonSqueezy link, and download a clean PDF — ready to send. Saved invoices flow straight into the chase pipeline if the client ghosts.',
  color: '#8b5cf6',
  bg: 'from-violet-50 to-purple-50',
  border: 'border-violet-200/60',
},
```

Additionally:
- Update the **hero subhead** to mention "create *and* chase" (one-line copy change — done as part of the same PR).
- Update the **demo reel** (`ProductDemoReel.tsx`) only if it's trivial — otherwise leave for a follow-up.

## TDD Strategy & Success Criteria

### Test stack (new dependencies)

```
vitest                      — test runner
@vitest/ui                  — optional dev UX
@testing-library/react      — component testing
@testing-library/user-event — interaction simulation
@testing-library/jest-dom   — assertions
jsdom                       — DOM environment for Vitest
```

Add `npm test`, `npm run test:watch`, `npm run test:coverage` scripts. Configure Vitest with `jsdom` env and a `setup.ts` that registers jest-dom matchers.

### TDD discipline

We follow the [`superpowers:test-driven-development`](skill) workflow:

1. **Write a failing test** for the smallest unit of behavior you can name (one test, one assertion's worth of behavior).
2. **Run it. Watch it fail** for the expected reason.
3. **Write the minimum code** to make it pass.
4. **Run it. Watch it pass.**
5. **Refactor** with the test as a safety net. Run again.
6. **Commit.** Then loop.

No implementation code lands without an accompanying test that *was written first* and *failed first*. PRs that interleave test-after work are sent back.

### Success criteria (objective, verifiable)

The feature ships when **all** of the following are true:

1. `npm run lint` passes with zero errors.
2. `npm run build` (which runs `tsc -b && vite build`) passes with zero errors.
3. `npm test` reports **100% green** across the new test suite.
4. Coverage for `frontend/src/components/invoice-generator/**` and `frontend/src/components/invoice-generator/pdf/**` is **≥ 90% lines, ≥ 85% branches** (enforced via Vitest's `--coverage` thresholds in `vite.config.ts`).
5. Manual smoke test passed in a real browser:
   - Fill the form with the happy-path data → live preview updates → download a real PDF.
   - Open the downloaded PDF in macOS Preview and Chrome — payment link is clickable and opens the URL.
   - Switch between all 3 templates — preview re-renders without errors.
   - Click "Save & Download" → invoice appears in `/dashboard`, can be opened in `/invoice/<id>`, chase agent loads cleanly.
6. Landing page change is visible at `/` (incognito) and renders on mobile (375px) without overflow.

### Test plan

The test list below is **the spec**. Implementing the feature without all of these tests = the feature isn't done.

#### A. Pure helpers (`pdf/shared/`)

`computeTotals.ts`
- ✅ happy: 2 lines, no tax, no discount → subtotal = sum, total = subtotal
- ✅ happy: 3 lines, 10% tax, no discount → total = subtotal × 1.10
- ✅ happy: flat discount → discount_amount caps at subtotal
- ✅ happy: pct discount + tax → tax applies to discounted subtotal
- ⚠️ edge: empty line_items → subtotal = 0, total = 0
- ⚠️ edge: zero quantity line → contributes 0
- ⚠️ edge: tax_rate_pct = 0 → equivalent to omitting tax
- ⚠️ edge: discount.kind = 'flat' with value > subtotal → discount_amount = subtotal (never negative total)
- ⚠️ edge: floating-point precision — `0.1 × 3 = 0.3` exactly (use integer-cent math, assert against cents)
- ⚠️ edge: pct discount with value = 100 → total = 0 (assuming no negative tax)
- ⚠️ edge: pct discount with value > 100 → clamped at 100 (validation rule)
- ⚠️ edge: negative quantity / negative unit_price → rejected by validator (separate test)

`formatCurrency.ts`
- ✅ happy: 199900 cents USD → "$1,999.00"
- ✅ happy: 199900 cents EUR → "€1,999.00" (locale-correct; we ship en-US locale for v1)
- ✅ happy: INR formatting uses lakhs grouping → "₹1,99,900.00"
- ⚠️ edge: 0 → "$0.00"
- ⚠️ edge: negative cents → never produced by our math; helper still renders sanely

`formatDate.ts`
- ✅ happy: "2026-05-23" → "May 23, 2026" (en-US)
- ⚠️ edge: invalid date string → throws with a clear error (we don't show invalid dates)

#### B. Form validation (`hooks/useInvoiceGeneratorForm.ts`)

- ✅ happy: all required fields filled, valid email, due ≥ issue, ≥ 1 line item, no payment link → `isValid = true`
- ⚠️ edge: business_name empty → `errors.business_name = "Business name is required"`
- ⚠️ edge: your_email = "not-an-email" → `errors.your_email = "Enter a valid email address"`
- ⚠️ edge: client_email empty → required error
- ⚠️ edge: due_date < issue_date → `errors.due_date = "Due date can't be before issue date"`
- ⚠️ edge: zero line items → `errors.line_items = "Add at least one line item"`
- ⚠️ edge: line item with empty description → row-level error, form invalid
- ⚠️ edge: line item with quantity = 0 → row-level error
- ⚠️ edge: line item with unit_price < 0 → row-level error
- ⚠️ edge: payment URL = "not a url" → `errors.payment_url = "Enter a valid URL starting with http:// or https://"`
- ⚠️ edge: payment URL = "javascript:alert(1)" → rejected (protocol not allowed)
- ⚠️ edge: payment URL = "" → no error (it's optional)
- ⚠️ edge: tax_rate_pct = 150 → `errors.tax_rate_pct = "Tax rate must be between 0 and 100"`
- ⚠️ edge: discount kind=pct, value=120 → clamped or error (we error)
- ⚠️ edge: logo > 2 MB → file rejected with friendly error
- ⚠️ edge: logo mime = "image/gif" → rejected

#### C. PDF template snapshot tests (`pdf/{Modern,Classic,Minimal}Template.tsx`)

For each template:
- ✅ happy: full fixture → JSON-serializable PDF document tree matches snapshot
- ✅ happy: with payment block → snapshot includes a `<Link>` node with `src` matching URL
- ⚠️ edge: no payment block → snapshot does not include any `<Link>` node
- ⚠️ edge: no logo → no image element in tree
- ⚠️ edge: 50 line items → renders, no overflow assertion errors thrown
- ⚠️ edge: extremely long description (500 chars) → text wraps, doesn't truncate silently
- ⚠️ edge: unicode in notes ("中文 العربية ñ") → preserved in tree

Snapshot strategy: render the JSX, traverse the `react-pdf` document tree to a plain object, snapshot that object (not the binary PDF). Stable, diff-able, fast.

#### D. Component tests (`__tests__/`)

`TemplatePicker.test.tsx`
- ✅ happy: renders 3 thumbnails labeled Modern / Classic / Minimal
- ✅ happy: clicking a thumbnail calls `onChange` with the template id
- ✅ happy: active template gets `aria-pressed="true"` and a visual selected state
- ⚠️ edge: keyboard navigation — the picker is a `role="radiogroup"` of three `role="radio"` buttons; ← / → move focus and selection, Home/End jump to first/last, Tab leaves the group

`LineItemsEditor.test.tsx`
- ✅ happy: starts with one empty row
- ✅ happy: "Add line" button appends a row
- ✅ happy: "Remove" button removes a row
- ⚠️ edge: can't remove the last row (button disabled, with title attr)
- ⚠️ edge: editing a row updates the bound state
- ⚠️ edge: pasting "12.50" into unit_price stores 1250 cents
- ⚠️ edge: pasting "abc" into quantity is ignored, doesn't crash

`InvoiceGeneratorPage.test.tsx`
- ✅ happy: full path — render → fill form → switch template → click Download → mocked PDF generator was invoked with the right `InvoiceData`
- ✅ happy: Save & Download path — mocked storage upload + mocked `createGeneratedInvoice` API are both called in order, with the correct payload, then navigation occurs to `/invoice/<id>`
- ⚠️ edge: submit while form invalid → submit button is disabled, no API calls
- ⚠️ edge: API failure on save → error toast surfaces, no navigation
- ⚠️ edge: storage upload failure → invoice row is NOT created (no orphaned rows)
- ⚠️ edge: sender profile fetch errors → form still usable, profile fields empty

#### E. Backend tests (Python, `tests/test_sender_profile.py`, `tests/test_generated_invoice.py`)

We don't have a Python test suite today; this feature **adds one**. Stack: `pytest` + `httpx.AsyncClient`. The backend changes are small enough that 2 test files is the whole surface.

`test_sender_profile.py`
- ✅ happy: GET returns empty `{}` for new users
- ✅ happy: PATCH stores the profile, GET returns it
- ⚠️ edge: PATCH with extra unknown keys → rejected (422)
- ⚠️ edge: PATCH with invalid email → rejected (422)
- ⚠️ edge: unauthenticated GET → 401

`test_generated_invoice.py`
- ✅ happy: POST `/api/invoices/generated` with a valid Supabase Storage path creates an `invoices` row at escalation_level=0
- ⚠️ edge: POST with a storage path that doesn't belong to this user → 403
- ⚠️ edge: POST with duplicate invoice_id for this user → 409 (we add an app-level uniqueness check; schema has no constraint today, the spec adds one as part of Phase 5)
- ⚠️ edge: unauthenticated POST → 401
- ⚠️ edge: guest users (cookie session) can create — same path as login users

## Build Sequence

Phases are ordered so each one ends on green tests. **No phase ends until its tests pass.**

```
Phase 0 — Tooling
  ✅ Install Vitest + RTL + jsdom; configure vite.config.ts
  ✅ Add npm test scripts; CI hook (we don't have CI yet — see Open Questions)
  ✅ Smoke: write one trivial test that asserts 2 + 2 === 4 to confirm runner

Phase 1 — Pure helpers (no UI)
  ✅ computeTotals + tests (integer-cent math)
  ✅ formatCurrency + tests
  ✅ formatDate + tests

Phase 2 — Form state hook
  ✅ useInvoiceGeneratorForm with full validation rules + all tests in section B

Phase 3 — PDF templates
  ✅ Install @react-pdf/renderer
  ✅ ModernTemplate + snapshot tests
  ✅ ClassicTemplate + snapshot tests
  ✅ MinimalTemplate + snapshot tests
  ✅ Template registry index.ts

Phase 4 — UI components
  ✅ TemplatePicker + tests
  ✅ LineItemsEditor + tests
  ✅ SenderProfileSection + tests
  ✅ PDFPreview wrapper (uses <PDFViewer> from react-pdf in dev, no test)

Phase 5 — Backend
  ✅ Migration: ADD COLUMN users.sender_profile JSONB
  ✅ Pydantic models for sender profile
  ✅ GET/PATCH /api/users/me/sender-profile + tests
  ✅ POST /api/invoices/generated + tests

Phase 6 — Wire the page
  ✅ InvoiceGeneratorPage container — pulls profile, runs form, owns PDF render
  ✅ Add route to App.tsx
  ✅ Wire Dashboard split CTA
  ✅ InvoiceGeneratorPage.test.tsx (full-flow tests with mocks)

Phase 7 — Landing page
  ✅ Add the new feature card
  ✅ Adjust hero subhead if it reads cleaner

Phase 8 — Verification
  ✅ npm run lint
  ✅ npm run build
  ✅ npm test (full suite)
  ✅ Coverage thresholds enforced
  ✅ Manual smoke test (download a real PDF, open in Preview + Chrome)
```

Each phase = one commit (or one small set of commits). Don't move to the next phase until the current one's tests are green.

## File Inventory

**New files:**

```
frontend/src/components/invoice-generator/
  InvoiceGeneratorPage.tsx
  TemplatePicker.tsx
  InvoiceGeneratorForm.tsx
  LineItemsEditor.tsx
  PDFPreview.tsx
  SenderProfileSection.tsx
  pdf/
    ModernTemplate.tsx
    ClassicTemplate.tsx
    MinimalTemplate.tsx
    shared/
      computeTotals.ts
      formatCurrency.ts
      formatDate.ts
    index.ts
  __tests__/
    computeTotals.test.ts
    formatCurrency.test.ts
    formatDate.test.ts
    useInvoiceGeneratorForm.test.ts
    ModernTemplate.test.tsx
    ClassicTemplate.test.tsx
    MinimalTemplate.test.tsx
    TemplatePicker.test.tsx
    LineItemsEditor.test.tsx
    InvoiceGeneratorPage.test.tsx
frontend/src/hooks/
  useInvoiceGeneratorForm.ts
  useSenderProfile.ts
frontend/vitest.config.ts                         (or extend vite.config.ts)
frontend/src/test/setup.ts                        (jest-dom registration)
tests/                                             (new Python test dir)
  conftest.py
  test_sender_profile.py
  test_generated_invoice.py
docs/superpowers/specs/2026-05-23-invoice-pdf-generator-design.md  (this file)
docs/superpowers/plans/2026-05-23-invoice-pdf-generator-plan.md    (created by writing-plans)
```

**Modified files:**

```
frontend/package.json                  (add deps + test scripts)
frontend/src/App.tsx                   (route)
frontend/src/api.ts                    (3 new methods)
frontend/src/types.ts                  (SenderProfile, InvoiceData, GenerateInvoiceRequest)
frontend/src/components/LandingPage.tsx (new feature card + hero subhead)
frontend/src/components/Dashboard.tsx  (split CTA: "Generate" / "Chase upload")
api/index.py                           (3 new routes — sender profile GET/PATCH, generated invoice POST)
supabase/schema.sql                    (sender_profile column)
```

## Out of Scope (recapping the YAGNI list)

- Word/DOCX export
- Server-side PDF rendering
- Multi-currency conversion
- Per-line tax rates
- Recurring invoices
- Stripe/LemonSqueezy API integration (we accept a URL the user already created)
- Custom template editor
- Editing/regenerating a previously saved invoice from stored source data

## Open Questions

1. **CI.** We don't have a CI pipeline today. Vitest will run locally, but enforcement of "tests must pass before merge" is honor-system until CI lands. Flag for follow-up; not blocking.
2. **PDF/A compliance.** Some jurisdictions require PDF/A for archived invoices. `@react-pdf/renderer` doesn't emit PDF/A. We accept this for v1.
3. **Locale.** All formatting is `en-US`. Currency symbols are correct, but date and number grouping is en-US-centric. Real localization is future work.
4. **Logo storage path.** First-pass uses `invoice-files/logos/<user_id>/<uuid>.png`. Cleanup of orphaned logos is not addressed in v1.
