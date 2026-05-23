# Invoice PDF Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a client-side invoice generator that renders PDFs in three templates (Modern/Classic/Minimal), embeds a user-supplied payment URL, lets the user download the PDF, and persists generated invoices into the existing chase pipeline.

**Architecture:** All PDF rendering happens in the browser using `@react-pdf/renderer`. The React form drives an `InvoiceData` shape that the templates render declaratively. On "Save & Download", the rendered Blob is uploaded to Supabase Storage and a row is created in the existing `invoices` table via a new backend endpoint. Sender-business fields persist per-user. A migration adds `users.sender_profile JSONB`. The agent-side chase flow is untouched.

**Tech Stack:** React 19 + TypeScript + Vite, Tailwind 4, `@react-pdf/renderer`, Vitest + @testing-library/react + jsdom, Python FastAPI + httpx (existing), pytest (new for backend tests), Supabase Postgres + Storage.

**Spec:** `docs/superpowers/specs/2026-05-23-invoice-pdf-generator-design.md`

---

## File Structure

### New files

| File | Responsibility |
|------|----------------|
| `frontend/vitest.config.ts` | Vitest config (jsdom env, coverage thresholds) |
| `frontend/src/test/setup.ts` | Test setup — registers jest-dom matchers |
| `frontend/src/components/invoice-generator/InvoiceGeneratorPage.tsx` | Route container: orchestrates form + preview + actions |
| `frontend/src/components/invoice-generator/TemplatePicker.tsx` | Three-thumbnail radio-group selector |
| `frontend/src/components/invoice-generator/InvoiceGeneratorForm.tsx` | The form (all sections) |
| `frontend/src/components/invoice-generator/LineItemsEditor.tsx` | Add/remove/edit line-item rows |
| `frontend/src/components/invoice-generator/SenderProfileSection.tsx` | Sender block within the form |
| `frontend/src/components/invoice-generator/PDFPreview.tsx` | Wraps `<PDFViewer>` from react-pdf |
| `frontend/src/components/invoice-generator/pdf/ModernTemplate.tsx` | Modern template PDF document |
| `frontend/src/components/invoice-generator/pdf/ClassicTemplate.tsx` | Classic template PDF document |
| `frontend/src/components/invoice-generator/pdf/MinimalTemplate.tsx` | Minimal template PDF document |
| `frontend/src/components/invoice-generator/pdf/index.ts` | Template registry (id → component, thumbnail) |
| `frontend/src/components/invoice-generator/pdf/shared/computeTotals.ts` | Integer-cent totals math |
| `frontend/src/components/invoice-generator/pdf/shared/formatCurrency.ts` | Currency formatter |
| `frontend/src/components/invoice-generator/pdf/shared/formatDate.ts` | Date formatter |
| `frontend/src/hooks/useInvoiceGeneratorForm.ts` | Form state + validation |
| `frontend/src/hooks/useSenderProfile.ts` | Sender profile fetch/update |
| `frontend/src/components/invoice-generator/__tests__/computeTotals.test.ts` | Helper tests |
| `frontend/src/components/invoice-generator/__tests__/formatCurrency.test.ts` | Helper tests |
| `frontend/src/components/invoice-generator/__tests__/formatDate.test.ts` | Helper tests |
| `frontend/src/components/invoice-generator/__tests__/useInvoiceGeneratorForm.test.ts` | Form-hook tests |
| `frontend/src/components/invoice-generator/__tests__/ModernTemplate.test.tsx` | Snapshot tests |
| `frontend/src/components/invoice-generator/__tests__/ClassicTemplate.test.tsx` | Snapshot tests |
| `frontend/src/components/invoice-generator/__tests__/MinimalTemplate.test.tsx` | Snapshot tests |
| `frontend/src/components/invoice-generator/__tests__/TemplatePicker.test.tsx` | Picker tests |
| `frontend/src/components/invoice-generator/__tests__/LineItemsEditor.test.tsx` | Line-items editor tests |
| `frontend/src/components/invoice-generator/__tests__/InvoiceGeneratorPage.test.tsx` | Full-flow tests |
| `frontend/src/components/invoice-generator/__tests__/fixtures.ts` | Shared test fixtures |
| `tests/__init__.py` | Make `tests/` a package |
| `tests/conftest.py` | pytest fixtures (test client, fake user) |
| `tests/test_sender_profile.py` | Backend tests — sender profile GET/PATCH |
| `tests/test_generated_invoice.py` | Backend tests — POST generated invoice |

### Modified files

| File | Changes |
|------|---------|
| `frontend/package.json` | Add deps (`@react-pdf/renderer`, vitest, RTL, jsdom); add npm scripts |
| `frontend/src/App.tsx` | Add route `/generate-invoice` |
| `frontend/src/api.ts` | Add `getSenderProfile`, `updateSenderProfile`, `uploadGeneratedInvoicePdf`, `createGeneratedInvoice` |
| `frontend/src/types.ts` | Add `SenderProfile`, `LineItem`, `InvoiceData`, `GenerateInvoiceRequest`, `TemplateId` |
| `frontend/src/components/LandingPage.tsx` | Add "Create polished invoices" feature card; tweak hero subhead |
| `frontend/src/components/Dashboard.tsx` | Split "+ New" CTA → "Generate invoice" / "Chase an existing invoice" |
| `api/index.py` | Add 3 routes: GET/PATCH `/api/users/me/sender-profile`, POST `/api/invoices/generated` |
| `supabase/schema.sql` | Add `users.sender_profile JSONB`; add unique constraint `(user_id, invoice_id_external)` if implemented as a separate column, or document the app-level check |
| `requirements.txt` | Add `pytest`, `pytest-asyncio`, `httpx` (if not already pinned) for backend tests |
| `.gitignore` | Add `frontend/coverage/`, `.pytest_cache/` |

---

## Conventions Used Throughout This Plan

- **Currency is integer cents** in JS. Never floats for money. Format only at the edge (`formatCurrency`).
- **Dates are ISO `yyyy-mm-dd` strings** internally. Format only at the edge (`formatDate`).
- **Tests live alongside source** under `__tests__/` directories. One test file per source file. Test the public surface, not internals.
- **TDD loop, every task:** write the failing test → run it and watch it fail with the expected error → write the minimum implementation → run it and watch it pass → commit. No mixing.
- **Commit message style:** Conventional Commits (`feat:`, `test:`, `chore:`, `refactor:`, `fix:`). Each commit includes the `Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>` trailer when committed by the agent.
- **Frontend file edits**: keep imports sorted (React first, then third-party, then `~/` local — match existing style in the file).
- **No ESLint disable comments.** If lint fails, fix the underlying issue.

---

# Phase 0 — Tooling

## Task 0.1: Install Vitest + RTL and configure

**Goal:** Get a green test runner before writing any feature code.

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/test/smoke.test.ts` (deleted at end of task)
- Modify: `.gitignore`

- [ ] **Step 1: Install dev dependencies**

```bash
cd frontend && npm install -D vitest @vitest/coverage-v8 @testing-library/react @testing-library/user-event @testing-library/jest-dom jsdom @types/node
```

Expected: `package.json` `devDependencies` updated; no errors.

- [ ] **Step 2: Install runtime dependency for PDF rendering**

```bash
cd frontend && npm install @react-pdf/renderer
```

- [ ] **Step 3: Add npm scripts to `frontend/package.json`**

Edit `frontend/package.json`, replace the `scripts` block with:

```json
"scripts": {
  "dev": "vite",
  "build": "tsc -b && vite build",
  "lint": "eslint .",
  "preview": "vite preview",
  "test": "vitest run",
  "test:watch": "vitest",
  "test:coverage": "vitest run --coverage"
}
```

- [ ] **Step 4: Create `frontend/vitest.config.ts`**

```ts
/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      include: [
        'src/components/invoice-generator/**',
        'src/hooks/useInvoiceGeneratorForm.ts',
        'src/hooks/useSenderProfile.ts',
      ],
      thresholds: {
        lines: 90,
        statements: 90,
        branches: 85,
        functions: 90,
      },
    },
  },
});
```

- [ ] **Step 5: Create `frontend/src/test/setup.ts`**

```ts
import '@testing-library/jest-dom/vitest';
```

- [ ] **Step 6: Write the smoke test at `frontend/src/test/smoke.test.ts`**

```ts
import { describe, it, expect } from 'vitest';

describe('test runner', () => {
  it('runs', () => {
    expect(2 + 2).toBe(4);
  });
});
```

- [ ] **Step 7: Run the smoke test**

```bash
cd frontend && npm test
```

Expected: `Test Files  1 passed (1)` `Tests  1 passed (1)`.

- [ ] **Step 8: Delete the smoke test**

```bash
rm frontend/src/test/smoke.test.ts
```

- [ ] **Step 9: Update `.gitignore`**

Append:

```
frontend/coverage/
.pytest_cache/
```

- [ ] **Step 10: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts frontend/src/test/setup.ts .gitignore
git commit -m "chore: add Vitest + RTL test runner and @react-pdf/renderer

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

# Phase 1 — Pure helpers

## Task 1.1: `computeTotals` — integer-cent totals math

**Files:**
- Create: `frontend/src/components/invoice-generator/pdf/shared/computeTotals.ts`
- Create: `frontend/src/components/invoice-generator/__tests__/computeTotals.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/invoice-generator/__tests__/computeTotals.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { computeTotals } from '../pdf/shared/computeTotals';

const cents = (n: number) => Math.round(n * 100);

describe('computeTotals', () => {
  it('sums two lines with no tax or discount', () => {
    const r = computeTotals({
      line_items: [
        { description: 'A', quantity: 2, unit_price_cents: cents(50) },  // 100.00
        { description: 'B', quantity: 1, unit_price_cents: cents(25) },  // 25.00
      ],
    });
    expect(r.subtotal_cents).toBe(cents(125));
    expect(r.discount_cents).toBe(0);
    expect(r.tax_cents).toBe(0);
    expect(r.total_cents).toBe(cents(125));
  });

  it('applies a 10% tax to the discounted subtotal', () => {
    const r = computeTotals({
      line_items: [{ description: 'A', quantity: 1, unit_price_cents: cents(100) }],
      tax_rate_pct: 10,
    });
    expect(r.total_cents).toBe(cents(110));
  });

  it('flat discount caps at subtotal (never negative)', () => {
    const r = computeTotals({
      line_items: [{ description: 'A', quantity: 1, unit_price_cents: cents(50) }],
      discount: { kind: 'flat', value: 200 }, // 200.00 flat on 50.00 subtotal
    });
    expect(r.discount_cents).toBe(cents(50));
    expect(r.total_cents).toBe(0);
  });

  it('pct discount applied before tax', () => {
    const r = computeTotals({
      line_items: [{ description: 'A', quantity: 1, unit_price_cents: cents(100) }],
      discount: { kind: 'pct', value: 50 },
      tax_rate_pct: 10,
    });
    // subtotal=100, discount=50, taxable=50, tax=5, total=55
    expect(r.subtotal_cents).toBe(cents(100));
    expect(r.discount_cents).toBe(cents(50));
    expect(r.tax_cents).toBe(cents(5));
    expect(r.total_cents).toBe(cents(55));
  });

  it('empty line items return all zeros', () => {
    const r = computeTotals({ line_items: [] });
    expect(r.subtotal_cents).toBe(0);
    expect(r.total_cents).toBe(0);
  });

  it('zero quantity contributes 0', () => {
    const r = computeTotals({
      line_items: [{ description: 'A', quantity: 0, unit_price_cents: cents(99) }],
    });
    expect(r.subtotal_cents).toBe(0);
  });

  it('tax_rate_pct = 0 equals omitting tax', () => {
    const a = computeTotals({
      line_items: [{ description: 'A', quantity: 1, unit_price_cents: cents(100) }],
      tax_rate_pct: 0,
    });
    const b = computeTotals({
      line_items: [{ description: 'A', quantity: 1, unit_price_cents: cents(100) }],
    });
    expect(a.total_cents).toBe(b.total_cents);
  });

  it('integer-cent arithmetic — 0.1 * 3 stays exact', () => {
    const r = computeTotals({
      line_items: [
        { description: 'A', quantity: 1, unit_price_cents: 10 },
        { description: 'B', quantity: 1, unit_price_cents: 10 },
        { description: 'C', quantity: 1, unit_price_cents: 10 },
      ],
    });
    expect(r.subtotal_cents).toBe(30);
    expect(r.total_cents).toBe(30);
  });

  it('pct discount of 100% with no tax yields zero', () => {
    const r = computeTotals({
      line_items: [{ description: 'A', quantity: 1, unit_price_cents: cents(100) }],
      discount: { kind: 'pct', value: 100 },
    });
    expect(r.total_cents).toBe(0);
  });

  it('pct discount above 100% clamps to 100%', () => {
    const r = computeTotals({
      line_items: [{ description: 'A', quantity: 1, unit_price_cents: cents(100) }],
      discount: { kind: 'pct', value: 150 },
    });
    expect(r.discount_cents).toBe(cents(100));
    expect(r.total_cents).toBe(0);
  });
});
```

- [ ] **Step 2: Run and watch it fail**

```bash
cd frontend && npm test -- computeTotals
```

Expected: All tests fail with `Cannot find module '../pdf/shared/computeTotals'`.

- [ ] **Step 3: Implement `computeTotals`**

Create `frontend/src/components/invoice-generator/pdf/shared/computeTotals.ts`:

```ts
export type LineItemInput = {
  description: string;
  quantity: number;
  unit_price_cents: number;
};

export type DiscountInput = {
  kind: 'flat' | 'pct';
  value: number;
};

export type ComputeTotalsInput = {
  line_items: LineItemInput[];
  tax_rate_pct?: number;
  discount?: DiscountInput;
};

export type Totals = {
  subtotal_cents: number;
  discount_cents: number;
  tax_cents: number;
  total_cents: number;
};

export function computeTotals(input: ComputeTotalsInput): Totals {
  const subtotal_cents = input.line_items.reduce(
    (acc, li) => acc + Math.round(li.quantity * li.unit_price_cents),
    0
  );

  let discount_cents = 0;
  if (input.discount) {
    if (input.discount.kind === 'flat') {
      discount_cents = Math.min(
        Math.max(0, Math.round(input.discount.value * 100)),
        subtotal_cents
      );
    } else {
      const pct = Math.min(100, Math.max(0, input.discount.value));
      discount_cents = Math.round(subtotal_cents * (pct / 100));
    }
  }

  const taxable_cents = Math.max(0, subtotal_cents - discount_cents);
  const rate = Math.max(0, input.tax_rate_pct ?? 0);
  const tax_cents = Math.round(taxable_cents * (rate / 100));
  const total_cents = taxable_cents + tax_cents;

  return { subtotal_cents, discount_cents, tax_cents, total_cents };
}
```

> Note: `flat` discount input is expressed in **dollars**, converted to cents internally — matching how the form will collect it. This is the only place "dollar" enters the helper; everything else is cents.

- [ ] **Step 4: Run and watch it pass**

```bash
cd frontend && npm test -- computeTotals
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/invoice-generator/
git commit -m "feat(invoice-gen): add computeTotals helper with integer-cent math

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 1.2: `formatCurrency`

**Files:**
- Create: `frontend/src/components/invoice-generator/pdf/shared/formatCurrency.ts`
- Create: `frontend/src/components/invoice-generator/__tests__/formatCurrency.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from 'vitest';
import { formatCurrency } from '../pdf/shared/formatCurrency';

describe('formatCurrency', () => {
  it('formats USD with dollar sign and grouping', () => {
    expect(formatCurrency(199900, 'USD')).toBe('$1,999.00');
  });

  it('formats EUR', () => {
    expect(formatCurrency(199900, 'EUR')).toBe('€1,999.00');
  });

  it('formats GBP', () => {
    expect(formatCurrency(199900, 'GBP')).toBe('£1,999.00');
  });

  it('formats INR with lakhs grouping', () => {
    expect(formatCurrency(19990000, 'INR')).toBe('₹1,99,900.00');
  });

  it('formats zero correctly', () => {
    expect(formatCurrency(0, 'USD')).toBe('$0.00');
  });

  it('formats sub-dollar amounts with leading zero', () => {
    expect(formatCurrency(7, 'USD')).toBe('$0.07');
  });
});
```

- [ ] **Step 2: Run and watch it fail**

```bash
cd frontend && npm test -- formatCurrency
```

Expected: All fail with "Cannot find module".

- [ ] **Step 3: Implement**

```ts
export type Currency = 'USD' | 'EUR' | 'GBP' | 'INR' | 'CAD' | 'AUD';

const LOCALES: Record<Currency, string> = {
  USD: 'en-US',
  EUR: 'en-IE',  // gives "€1,999.00" symbol-prefixed
  GBP: 'en-GB',
  INR: 'en-IN',
  CAD: 'en-CA',
  AUD: 'en-AU',
};

export function formatCurrency(amount_cents: number, currency: Currency): string {
  return new Intl.NumberFormat(LOCALES[currency], {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount_cents / 100);
}
```

- [ ] **Step 4: Run and watch it pass**

```bash
cd frontend && npm test -- formatCurrency
```

Expected: 6 passed.

> Note: `Intl.NumberFormat` output is locale-dependent and may differ slightly across Node versions. If a test fails on a specific symbol (e.g., EUR uses "€" vs "EUR"), pin the locale until the test matches. The intent — clear human-readable currency — is what matters.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/invoice-generator/
git commit -m "feat(invoice-gen): add formatCurrency helper

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 1.3: `formatDate`

**Files:**
- Create: `frontend/src/components/invoice-generator/pdf/shared/formatDate.ts`
- Create: `frontend/src/components/invoice-generator/__tests__/formatDate.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from 'vitest';
import { formatDate } from '../pdf/shared/formatDate';

describe('formatDate', () => {
  it('formats an ISO date in long en-US form', () => {
    expect(formatDate('2026-05-23')).toBe('May 23, 2026');
  });

  it('throws for an invalid date string', () => {
    expect(() => formatDate('not-a-date')).toThrow(/invalid date/i);
  });

  it('throws for empty string', () => {
    expect(() => formatDate('')).toThrow(/invalid date/i);
  });

  it('handles single-digit months and days', () => {
    expect(formatDate('2026-01-05')).toBe('January 5, 2026');
  });
});
```

- [ ] **Step 2: Run and watch it fail**

```bash
cd frontend && npm test -- formatDate
```

- [ ] **Step 3: Implement**

```ts
export function formatDate(iso: string): string {
  if (!iso || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) {
    throw new Error(`Invalid date: ${iso}`);
  }
  const [y, m, d] = iso.split('-').map(Number);
  const date = new Date(Date.UTC(y, m - 1, d));
  if (Number.isNaN(date.getTime())) {
    throw new Error(`Invalid date: ${iso}`);
  }
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    timeZone: 'UTC',
  }).format(date);
}
```

- [ ] **Step 4: Run and watch it pass**

```bash
cd frontend && npm test -- formatDate
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/invoice-generator/
git commit -m "feat(invoice-gen): add formatDate helper

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

# Phase 2 — Form state + validation

## Task 2.1: Shared types in `types.ts`

**Files:**
- Modify: `frontend/src/types.ts`

This task introduces types only — no tests of its own; correctness is exercised by Task 2.2 and Task 3 onward.

- [ ] **Step 1: Append to `frontend/src/types.ts`**

```ts
// ─── Invoice Generator ───────────────────────────────────────────

export type TemplateId = 'modern' | 'classic' | 'minimal';

export type Currency = 'USD' | 'EUR' | 'GBP' | 'INR' | 'CAD' | 'AUD';

export interface SenderProfile {
  business_name?: string;
  your_name?: string;
  your_email?: string;
  address?: string;
  logo_url?: string;
  tax_id?: string;
}

export interface LineItem {
  description: string;
  quantity: number;
  unit_price_cents: number;
}

export interface InvoiceData {
  sender: SenderProfile;
  client: { name: string; email: string; address?: string };
  meta: {
    invoice_number: string;
    issue_date: string;  // yyyy-mm-dd
    due_date: string;    // yyyy-mm-dd
    currency: Currency;
  };
  line_items: LineItem[];
  tax_rate_pct?: number;
  discount?: { kind: 'flat' | 'pct'; value: number };
  payment?: { url: string; label?: string };
  payment_instructions?: string;
  notes?: string;
  template: TemplateId;
  accent_color?: string;  // honored by Modern only
}

export interface GenerateInvoiceRequest {
  invoice_id: string;
  client_name: string;
  client_email: string;
  invoice_amount_cents: number;
  due_date: string;
  jurisdiction?: string;
  storage_path: string;  // path within invoice-files bucket
  file_name: string;
  file_size: number;
}
```

- [ ] **Step 2: Build to confirm types compile**

```bash
cd frontend && npx tsc --noEmit
```

Expected: zero errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types.ts
git commit -m "feat(invoice-gen): add types for invoice generator

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 2.2: `useInvoiceGeneratorForm` hook

**Files:**
- Create: `frontend/src/hooks/useInvoiceGeneratorForm.ts`
- Create: `frontend/src/components/invoice-generator/__tests__/fixtures.ts`
- Create: `frontend/src/components/invoice-generator/__tests__/useInvoiceGeneratorForm.test.ts`

- [ ] **Step 1: Write the fixture file**

Create `frontend/src/components/invoice-generator/__tests__/fixtures.ts`:

```ts
import type { InvoiceData } from '../../../types';

export const validInvoice = (): InvoiceData => ({
  sender: {
    business_name: 'Acme Studio',
    your_name: 'Jane Doe',
    your_email: 'jane@acme.example',
    address: '1 Main St\nSpringfield',
  },
  client: { name: 'BigCorp', email: 'ap@bigcorp.example' },
  meta: {
    invoice_number: 'INV-2026-001',
    issue_date: '2026-05-01',
    due_date: '2026-05-15',
    currency: 'USD',
  },
  line_items: [
    { description: 'Design work', quantity: 10, unit_price_cents: 15000 }, // $150.00
  ],
  template: 'modern',
});
```

- [ ] **Step 2: Write the failing tests**

Create `frontend/src/components/invoice-generator/__tests__/useInvoiceGeneratorForm.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useInvoiceGeneratorForm } from '../../../hooks/useInvoiceGeneratorForm';
import { validInvoice } from './fixtures';

describe('useInvoiceGeneratorForm', () => {
  it('starts valid when seeded with valid data', () => {
    const { result } = renderHook(() => useInvoiceGeneratorForm(validInvoice()));
    expect(result.current.isValid).toBe(true);
    expect(result.current.errors).toEqual({});
  });

  it('flags empty business_name as required', () => {
    const seed = validInvoice();
    seed.sender.business_name = '';
    const { result } = renderHook(() => useInvoiceGeneratorForm(seed));
    expect(result.current.isValid).toBe(false);
    expect(result.current.errors['sender.business_name']).toMatch(/required/i);
  });

  it('flags invalid your_email', () => {
    const seed = validInvoice();
    seed.sender.your_email = 'not-an-email';
    const { result } = renderHook(() => useInvoiceGeneratorForm(seed));
    expect(result.current.errors['sender.your_email']).toMatch(/valid email/i);
  });

  it('requires client_email', () => {
    const seed = validInvoice();
    seed.client.email = '';
    const { result } = renderHook(() => useInvoiceGeneratorForm(seed));
    expect(result.current.errors['client.email']).toMatch(/required/i);
  });

  it('flags due_date before issue_date', () => {
    const seed = validInvoice();
    seed.meta.issue_date = '2026-05-15';
    seed.meta.due_date = '2026-05-01';
    const { result } = renderHook(() => useInvoiceGeneratorForm(seed));
    expect(result.current.errors['meta.due_date']).toMatch(/before issue date/i);
  });

  it('requires at least one line item', () => {
    const seed = validInvoice();
    seed.line_items = [];
    const { result } = renderHook(() => useInvoiceGeneratorForm(seed));
    expect(result.current.errors['line_items']).toMatch(/at least one/i);
  });

  it('flags line item with empty description', () => {
    const seed = validInvoice();
    seed.line_items = [{ description: '', quantity: 1, unit_price_cents: 100 }];
    const { result } = renderHook(() => useInvoiceGeneratorForm(seed));
    expect(result.current.errors['line_items.0.description']).toMatch(/required/i);
  });

  it('flags zero quantity', () => {
    const seed = validInvoice();
    seed.line_items = [{ description: 'A', quantity: 0, unit_price_cents: 100 }];
    const { result } = renderHook(() => useInvoiceGeneratorForm(seed));
    expect(result.current.errors['line_items.0.quantity']).toMatch(/greater than 0/i);
  });

  it('flags negative unit_price', () => {
    const seed = validInvoice();
    seed.line_items = [{ description: 'A', quantity: 1, unit_price_cents: -1 }];
    const { result } = renderHook(() => useInvoiceGeneratorForm(seed));
    expect(result.current.errors['line_items.0.unit_price_cents']).toMatch(/non-negative/i);
  });

  it('accepts empty payment URL (it is optional)', () => {
    const seed = validInvoice();
    seed.payment = { url: '' };
    const { result } = renderHook(() => useInvoiceGeneratorForm(seed));
    expect(result.current.errors['payment.url']).toBeUndefined();
    expect(result.current.isValid).toBe(true);
  });

  it('rejects malformed payment URL', () => {
    const seed = validInvoice();
    seed.payment = { url: 'not a url' };
    const { result } = renderHook(() => useInvoiceGeneratorForm(seed));
    expect(result.current.errors['payment.url']).toMatch(/valid URL/i);
  });

  it('rejects javascript: URL', () => {
    const seed = validInvoice();
    seed.payment = { url: 'javascript:alert(1)' };
    const { result } = renderHook(() => useInvoiceGeneratorForm(seed));
    expect(result.current.errors['payment.url']).toMatch(/http/i);
  });

  it('rejects tax_rate above 100', () => {
    const seed = validInvoice();
    seed.tax_rate_pct = 150;
    const { result } = renderHook(() => useInvoiceGeneratorForm(seed));
    expect(result.current.errors['tax_rate_pct']).toMatch(/between 0 and 100/i);
  });

  it('rejects pct discount above 100', () => {
    const seed = validInvoice();
    seed.discount = { kind: 'pct', value: 120 };
    const { result } = renderHook(() => useInvoiceGeneratorForm(seed));
    expect(result.current.errors['discount.value']).toMatch(/between 0 and 100/i);
  });

  it('setField updates the value and re-validates', () => {
    const { result } = renderHook(() => useInvoiceGeneratorForm(validInvoice()));
    act(() => { result.current.setField('sender.business_name', ''); });
    expect(result.current.errors['sender.business_name']).toBeTruthy();
    act(() => { result.current.setField('sender.business_name', 'Acme'); });
    expect(result.current.errors['sender.business_name']).toBeUndefined();
  });

  it('setLineItems replaces the line item array and re-validates', () => {
    const { result } = renderHook(() => useInvoiceGeneratorForm(validInvoice()));
    act(() => { result.current.setLineItems([]); });
    expect(result.current.errors['line_items']).toBeTruthy();
  });
});
```

- [ ] **Step 3: Run and watch it fail**

```bash
cd frontend && npm test -- useInvoiceGeneratorForm
```

Expected: All fail with "Cannot find module".

- [ ] **Step 4: Implement the hook**

Create `frontend/src/hooks/useInvoiceGeneratorForm.ts`:

```ts
import { useCallback, useMemo, useState } from 'react';
import type { InvoiceData, LineItem } from '../types';

export type FormErrors = Record<string, string>;

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validate(data: InvoiceData): FormErrors {
  const errors: FormErrors = {};

  if (!data.sender.business_name?.trim()) {
    errors['sender.business_name'] = 'Business name is required';
  }
  if (!data.sender.your_name?.trim()) {
    errors['sender.your_name'] = 'Your name is required';
  }
  if (!data.sender.your_email?.trim()) {
    errors['sender.your_email'] = 'Your email is required';
  } else if (!EMAIL_RE.test(data.sender.your_email)) {
    errors['sender.your_email'] = 'Enter a valid email address';
  }

  if (!data.client.name?.trim()) {
    errors['client.name'] = 'Client name is required';
  }
  if (!data.client.email?.trim()) {
    errors['client.email'] = 'Client email is required';
  } else if (!EMAIL_RE.test(data.client.email)) {
    errors['client.email'] = 'Enter a valid client email';
  }

  if (!data.meta.invoice_number?.trim()) {
    errors['meta.invoice_number'] = 'Invoice number is required';
  }
  if (!data.meta.issue_date) {
    errors['meta.issue_date'] = 'Issue date is required';
  }
  if (!data.meta.due_date) {
    errors['meta.due_date'] = 'Due date is required';
  } else if (data.meta.issue_date && data.meta.due_date < data.meta.issue_date) {
    errors['meta.due_date'] = "Due date can't be before issue date";
  }

  if (data.line_items.length === 0) {
    errors['line_items'] = 'Add at least one line item';
  } else {
    data.line_items.forEach((li, i) => {
      if (!li.description?.trim()) {
        errors[`line_items.${i}.description`] = 'Description is required';
      }
      if (!(li.quantity > 0)) {
        errors[`line_items.${i}.quantity`] = 'Quantity must be greater than 0';
      }
      if (li.unit_price_cents < 0) {
        errors[`line_items.${i}.unit_price_cents`] = 'Unit price must be non-negative';
      }
    });
  }

  if (data.tax_rate_pct !== undefined) {
    if (data.tax_rate_pct < 0 || data.tax_rate_pct > 100) {
      errors['tax_rate_pct'] = 'Tax rate must be between 0 and 100';
    }
  }

  if (data.discount) {
    if (data.discount.value < 0) {
      errors['discount.value'] = 'Discount must be non-negative';
    } else if (data.discount.kind === 'pct' && data.discount.value > 100) {
      errors['discount.value'] = 'Percentage discount must be between 0 and 100';
    }
  }

  if (data.payment?.url) {
    try {
      const url = new URL(data.payment.url);
      if (url.protocol !== 'http:' && url.protocol !== 'https:') {
        errors['payment.url'] = 'Payment URL must use http:// or https://';
      }
    } catch {
      errors['payment.url'] = 'Enter a valid URL starting with http:// or https://';
    }
  }

  return errors;
}

function setNested(obj: any, path: string, value: unknown): any {
  const parts = path.split('.');
  const clone = structuredClone(obj);
  let cur: any = clone;
  for (let i = 0; i < parts.length - 1; i++) {
    if (cur[parts[i]] === undefined || cur[parts[i]] === null) {
      cur[parts[i]] = {};
    }
    cur = cur[parts[i]];
  }
  cur[parts[parts.length - 1]] = value;
  return clone;
}

export interface UseInvoiceGeneratorForm {
  data: InvoiceData;
  errors: FormErrors;
  isValid: boolean;
  setData: (next: InvoiceData) => void;
  setField: (path: string, value: unknown) => void;
  setLineItems: (items: LineItem[]) => void;
}

export function useInvoiceGeneratorForm(initial: InvoiceData): UseInvoiceGeneratorForm {
  const [data, setData] = useState<InvoiceData>(initial);
  const errors = useMemo(() => validate(data), [data]);
  const isValid = Object.keys(errors).length === 0;

  const setField = useCallback((path: string, value: unknown) => {
    setData(prev => setNested(prev, path, value));
  }, []);

  const setLineItems = useCallback((items: LineItem[]) => {
    setData(prev => ({ ...prev, line_items: items }));
  }, []);

  return { data, errors, isValid, setData, setField, setLineItems };
}
```

- [ ] **Step 5: Run and watch it pass**

```bash
cd frontend && npm test -- useInvoiceGeneratorForm
```

Expected: 16 passed.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/useInvoiceGeneratorForm.ts frontend/src/components/invoice-generator/__tests__/
git commit -m "feat(invoice-gen): add form-state hook with full validation

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

# Phase 3 — PDF templates

## Task 3.1: Modern template

**Files:**
- Create: `frontend/src/components/invoice-generator/pdf/ModernTemplate.tsx`
- Create: `frontend/src/components/invoice-generator/__tests__/ModernTemplate.test.tsx`

The snapshot strategy: render the template, traverse the `react-pdf` document tree to a serializable object, snapshot the object. We don't snapshot the binary PDF — that's brittle and gives no diff signal.

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, it, expect } from 'vitest';
import React from 'react';
import { ModernTemplate } from '../pdf/ModernTemplate';
import { validInvoice } from './fixtures';

// Recursively strip React internals and serialize the document tree.
function serialize(node: React.ReactNode): unknown {
  if (node === null || node === undefined) return null;
  if (typeof node === 'string' || typeof node === 'number') return node;
  if (Array.isArray(node)) return node.map(serialize);
  if (React.isValidElement(node)) {
    const el = node as React.ReactElement<{ children?: React.ReactNode }>;
    const type = typeof el.type === 'string'
      ? el.type
      : (el.type as { displayName?: string; name?: string }).displayName
        ?? (el.type as { name?: string }).name
        ?? 'Unknown';
    const { children, ...rest } = (el.props ?? {}) as Record<string, unknown>;
    return { type, props: rest, children: serialize(children as React.ReactNode) };
  }
  return null;
}

describe('ModernTemplate', () => {
  it('matches the snapshot for a full invoice', () => {
    const tree = serialize(<ModernTemplate data={validInvoice()} />);
    expect(tree).toMatchSnapshot();
  });

  it('includes a Link node when payment.url is provided', () => {
    const data = validInvoice();
    data.payment = { url: 'https://buy.stripe.com/abc', label: 'PAY' };
    const tree = JSON.stringify(serialize(<ModernTemplate data={data} />));
    expect(tree).toContain('"type":"Link"');
    expect(tree).toContain('https://buy.stripe.com/abc');
  });

  it('omits the payment block entirely when payment is undefined', () => {
    const data = validInvoice();
    delete data.payment;
    const tree = JSON.stringify(serialize(<ModernTemplate data={data} />));
    expect(tree).not.toContain('"type":"Link"');
  });

  it('omits the logo block when sender.logo_url is undefined', () => {
    const data = validInvoice();
    const tree = JSON.stringify(serialize(<ModernTemplate data={data} />));
    expect(tree).not.toContain('"type":"Image"');
  });

  it('renders 50 line items without throwing', () => {
    const data = validInvoice();
    data.line_items = Array.from({ length: 50 }, (_, i) => ({
      description: `Item ${i}`,
      quantity: 1,
      unit_price_cents: 100,
    }));
    expect(() => serialize(<ModernTemplate data={data} />)).not.toThrow();
  });

  it('preserves unicode in notes', () => {
    const data = validInvoice();
    data.notes = '中文 العربية ñ';
    const tree = JSON.stringify(serialize(<ModernTemplate data={data} />));
    expect(tree).toContain('中文');
  });
});
```

- [ ] **Step 2: Run and watch it fail**

```bash
cd frontend && npm test -- ModernTemplate
```

Expected: all fail with "Cannot find module".

- [ ] **Step 3: Implement ModernTemplate**

Create `frontend/src/components/invoice-generator/pdf/ModernTemplate.tsx`:

```tsx
import { Document, Page, View, Text, Image, Link, StyleSheet } from '@react-pdf/renderer';
import type { InvoiceData } from '../../../types';
import { computeTotals } from './shared/computeTotals';
import { formatCurrency } from './shared/formatCurrency';
import { formatDate } from './shared/formatDate';

interface Props { data: InvoiceData }

const DEFAULT_ACCENT = '#FF6B35';

const styles = StyleSheet.create({
  page: { paddingTop: 0, paddingBottom: 40, paddingHorizontal: 40, fontFamily: 'Helvetica', fontSize: 10 },
  band: { height: 40, marginBottom: 24 },
  header: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 24 },
  bizBlock: { flexDirection: 'column', maxWidth: 280 },
  bizName: { fontSize: 14, fontWeight: 'bold', marginBottom: 4 },
  bizAddr: { fontSize: 9, color: '#555', lineHeight: 1.4 },
  invMeta: { textAlign: 'right' },
  invLabel: { fontSize: 9, color: '#888', letterSpacing: 1 },
  invNum: { fontSize: 22, fontWeight: 'bold', marginTop: 2 },
  invDates: { fontSize: 9, color: '#555', marginTop: 6, lineHeight: 1.4 },
  section: { marginBottom: 16 },
  sectionLabel: { fontSize: 9, color: '#888', letterSpacing: 1, marginBottom: 4 },
  clientName: { fontSize: 11, fontWeight: 'bold' },
  clientLine: { fontSize: 9, color: '#444', lineHeight: 1.4 },
  table: { marginTop: 8 },
  thead: { flexDirection: 'row', borderBottomWidth: 1, paddingBottom: 4 },
  th: { fontSize: 9, color: '#888', fontWeight: 'bold' },
  tr: { flexDirection: 'row', paddingVertical: 4 },
  trAlt: { backgroundColor: '#FFF4EE' },
  td: { fontSize: 10 },
  col_desc: { flex: 4 },
  col_qty: { flex: 1, textAlign: 'right' },
  col_unit: { flex: 1.5, textAlign: 'right' },
  col_total: { flex: 1.5, textAlign: 'right' },
  totals: { marginTop: 12, alignItems: 'flex-end' },
  totalRow: { flexDirection: 'row', marginBottom: 2 },
  totalLabel: { width: 100, textAlign: 'right', marginRight: 12, color: '#666' },
  totalVal: { width: 80, textAlign: 'right' },
  totalGrand: { fontSize: 14, fontWeight: 'bold', marginTop: 4 },
  payBtn: {
    marginTop: 24,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 6,
    color: '#FFFFFF',
    textAlign: 'center',
    textDecoration: 'none',
    fontWeight: 'bold',
    fontSize: 11,
    letterSpacing: 1,
  },
  payInstructions: { marginTop: 8, fontSize: 9, color: '#444', lineHeight: 1.4 },
  notes: { marginTop: 24, fontSize: 9, color: '#444', lineHeight: 1.4 },
  logo: { width: 60, height: 60, objectFit: 'contain', marginBottom: 8 },
});

export function ModernTemplate({ data }: Props) {
  const accent = data.accent_color || DEFAULT_ACCENT;
  const totals = computeTotals(data);
  const ccy = data.meta.currency;

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <View style={[styles.band, { backgroundColor: accent }]} />

        <View style={styles.header}>
          <View style={styles.bizBlock}>
            {data.sender.logo_url ? <Image style={styles.logo} src={data.sender.logo_url} /> : null}
            <Text style={styles.bizName}>{data.sender.business_name}</Text>
            <Text style={styles.bizAddr}>{data.sender.your_name}</Text>
            {data.sender.address ? <Text style={styles.bizAddr}>{data.sender.address}</Text> : null}
            <Text style={styles.bizAddr}>{data.sender.your_email}</Text>
            {data.sender.tax_id ? <Text style={styles.bizAddr}>Tax ID: {data.sender.tax_id}</Text> : null}
          </View>
          <View style={styles.invMeta}>
            <Text style={styles.invLabel}>INVOICE</Text>
            <Text style={styles.invNum}>{data.meta.invoice_number}</Text>
            <Text style={styles.invDates}>Issued: {formatDate(data.meta.issue_date)}</Text>
            <Text style={styles.invDates}>Due: {formatDate(data.meta.due_date)}</Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionLabel}>BILL TO</Text>
          <Text style={styles.clientName}>{data.client.name}</Text>
          <Text style={styles.clientLine}>{data.client.email}</Text>
          {data.client.address ? <Text style={styles.clientLine}>{data.client.address}</Text> : null}
        </View>

        <View style={styles.table}>
          <View style={styles.thead}>
            <Text style={[styles.th, styles.col_desc]}>DESCRIPTION</Text>
            <Text style={[styles.th, styles.col_qty]}>QTY</Text>
            <Text style={[styles.th, styles.col_unit]}>UNIT</Text>
            <Text style={[styles.th, styles.col_total]}>TOTAL</Text>
          </View>
          {data.line_items.map((li, i) => (
            <View key={i} style={[styles.tr, i % 2 === 1 ? styles.trAlt : {}]}>
              <Text style={[styles.td, styles.col_desc]}>{li.description}</Text>
              <Text style={[styles.td, styles.col_qty]}>{li.quantity}</Text>
              <Text style={[styles.td, styles.col_unit]}>{formatCurrency(li.unit_price_cents, ccy)}</Text>
              <Text style={[styles.td, styles.col_total]}>
                {formatCurrency(Math.round(li.quantity * li.unit_price_cents), ccy)}
              </Text>
            </View>
          ))}
        </View>

        <View style={styles.totals}>
          <View style={styles.totalRow}>
            <Text style={styles.totalLabel}>Subtotal</Text>
            <Text style={styles.totalVal}>{formatCurrency(totals.subtotal_cents, ccy)}</Text>
          </View>
          {totals.discount_cents > 0 ? (
            <View style={styles.totalRow}>
              <Text style={styles.totalLabel}>Discount</Text>
              <Text style={styles.totalVal}>− {formatCurrency(totals.discount_cents, ccy)}</Text>
            </View>
          ) : null}
          {totals.tax_cents > 0 ? (
            <View style={styles.totalRow}>
              <Text style={styles.totalLabel}>Tax ({data.tax_rate_pct ?? 0}%)</Text>
              <Text style={styles.totalVal}>{formatCurrency(totals.tax_cents, ccy)}</Text>
            </View>
          ) : null}
          <View style={styles.totalRow}>
            <Text style={[styles.totalLabel, styles.totalGrand]}>Total</Text>
            <Text style={[styles.totalVal, styles.totalGrand]}>{formatCurrency(totals.total_cents, ccy)}</Text>
          </View>
        </View>

        {data.payment?.url ? (
          <Link src={data.payment.url} style={[styles.payBtn, { backgroundColor: accent }]}>
            {data.payment.label || 'PAY INVOICE →'}
          </Link>
        ) : null}

        {data.payment_instructions ? (
          <Text style={styles.payInstructions}>{data.payment_instructions}</Text>
        ) : null}

        {data.notes ? <Text style={styles.notes}>{data.notes}</Text> : null}
      </Page>
    </Document>
  );
}
```

- [ ] **Step 4: Run and watch it pass**

```bash
cd frontend && npm test -- ModernTemplate
```

Expected: 6 passed, 1 snapshot written. Review the snapshot file `frontend/src/components/invoice-generator/__tests__/__snapshots__/ModernTemplate.test.tsx.snap` to confirm it's sane (correct structure, no leaked internals).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/invoice-generator/
git commit -m "feat(invoice-gen): add Modern PDF template with tests

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 3.2: Classic template

**Files:**
- Create: `frontend/src/components/invoice-generator/pdf/ClassicTemplate.tsx`
- Create: `frontend/src/components/invoice-generator/__tests__/ClassicTemplate.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/invoice-generator/__tests__/ClassicTemplate.test.tsx`. Reuse the `serialize` helper pattern from Task 3.1 — copy it into this file (don't extract — keeps tests isolated and self-contained):

```tsx
import { describe, it, expect } from 'vitest';
import React from 'react';
import { ClassicTemplate } from '../pdf/ClassicTemplate';
import { validInvoice } from './fixtures';

function serialize(node: React.ReactNode): unknown {
  if (node === null || node === undefined) return null;
  if (typeof node === 'string' || typeof node === 'number') return node;
  if (Array.isArray(node)) return node.map(serialize);
  if (React.isValidElement(node)) {
    const el = node as React.ReactElement<{ children?: React.ReactNode }>;
    const type = typeof el.type === 'string'
      ? el.type
      : (el.type as { displayName?: string; name?: string }).displayName
        ?? (el.type as { name?: string }).name
        ?? 'Unknown';
    const { children, ...rest } = (el.props ?? {}) as Record<string, unknown>;
    return { type, props: rest, children: serialize(children as React.ReactNode) };
  }
  return null;
}

describe('ClassicTemplate', () => {
  it('matches the snapshot for a full invoice', () => {
    const tree = serialize(<ClassicTemplate data={validInvoice()} />);
    expect(tree).toMatchSnapshot();
  });

  it('renders payment URL inline as "Pay online: <url>" when payment provided', () => {
    const data = validInvoice();
    data.payment = { url: 'https://buy.stripe.com/xyz' };
    const tree = JSON.stringify(serialize(<ClassicTemplate data={data} />));
    expect(tree).toContain('Pay online');
    expect(tree).toContain('https://buy.stripe.com/xyz');
  });

  it('omits the payment block when payment is undefined', () => {
    const data = validInvoice();
    delete data.payment;
    const tree = JSON.stringify(serialize(<ClassicTemplate data={data} />));
    expect(tree).not.toContain('Pay online');
  });

  it('renders 50 line items without throwing', () => {
    const data = validInvoice();
    data.line_items = Array.from({ length: 50 }, (_, i) => ({
      description: `Item ${i}`, quantity: 1, unit_price_cents: 100,
    }));
    expect(() => serialize(<ClassicTemplate data={data} />)).not.toThrow();
  });
});
```

- [ ] **Step 2: Run and watch it fail**

```bash
cd frontend && npm test -- ClassicTemplate
```

- [ ] **Step 3: Implement ClassicTemplate**

Create `frontend/src/components/invoice-generator/pdf/ClassicTemplate.tsx`:

```tsx
import { Document, Page, View, Text, Image, Link, StyleSheet } from '@react-pdf/renderer';
import type { InvoiceData } from '../../../types';
import { computeTotals } from './shared/computeTotals';
import { formatCurrency } from './shared/formatCurrency';
import { formatDate } from './shared/formatDate';

interface Props { data: InvoiceData }

const styles = StyleSheet.create({
  page: { padding: 50, fontFamily: 'Times-Roman', fontSize: 10, color: '#000' },
  letterhead: { textAlign: 'center', marginBottom: 32 },
  bizName: { fontSize: 16, fontWeight: 'bold', letterSpacing: 2, marginBottom: 4 },
  bizLine: { fontSize: 9, lineHeight: 1.4 },
  rule: { borderBottomWidth: 1, marginVertical: 16 },
  metaRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 24 },
  metaLeft: { flexDirection: 'column' },
  metaLabel: { fontSize: 9, letterSpacing: 1, marginBottom: 4 },
  invNum: { fontSize: 18, fontWeight: 'bold' },
  metaRight: { textAlign: 'right' },
  table: { borderWidth: 1, marginBottom: 12 },
  thead: { flexDirection: 'row', borderBottomWidth: 1, padding: 6, backgroundColor: '#F5F5F0' },
  tr: { flexDirection: 'row', padding: 6, borderBottomWidth: 0.5, borderColor: '#999' },
  th: { fontSize: 9, fontWeight: 'bold', letterSpacing: 1 },
  td: { fontSize: 10 },
  col_desc: { flex: 4 },
  col_qty: { flex: 1, textAlign: 'right' },
  col_unit: { flex: 1.5, textAlign: 'right' },
  col_total: { flex: 1.5, textAlign: 'right' },
  totalsBox: {
    marginLeft: 'auto',
    width: 220,
    borderTopWidth: 2,
    borderBottomWidth: 2,
    paddingVertical: 8,
    marginTop: 8,
  },
  totalRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 2 },
  totalLabel: { fontSize: 10 },
  totalVal: { fontSize: 10 },
  grandLabel: { fontSize: 12, fontWeight: 'bold', marginTop: 4 },
  grandVal: { fontSize: 12, fontWeight: 'bold', marginTop: 4 },
  payBlock: { marginTop: 24 },
  payText: { fontSize: 10 },
  payLink: { color: '#1A4FBF', textDecoration: 'underline' },
  payInstructions: { marginTop: 8, fontSize: 9, lineHeight: 1.4 },
  notes: { marginTop: 24, fontSize: 9, lineHeight: 1.4 },
  logo: { width: 50, height: 50, alignSelf: 'center', marginBottom: 8 },
});

export function ClassicTemplate({ data }: Props) {
  const totals = computeTotals(data);
  const ccy = data.meta.currency;

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <View style={styles.letterhead}>
          {data.sender.logo_url ? <Image style={styles.logo} src={data.sender.logo_url} /> : null}
          <Text style={styles.bizName}>{data.sender.business_name?.toUpperCase()}</Text>
          {data.sender.address ? <Text style={styles.bizLine}>{data.sender.address}</Text> : null}
          <Text style={styles.bizLine}>{data.sender.your_email}</Text>
          {data.sender.tax_id ? <Text style={styles.bizLine}>Tax ID: {data.sender.tax_id}</Text> : null}
        </View>

        <View style={styles.rule} />

        <View style={styles.metaRow}>
          <View style={styles.metaLeft}>
            <Text style={styles.metaLabel}>BILL TO</Text>
            <Text style={[styles.td, { fontWeight: 'bold' }]}>{data.client.name}</Text>
            <Text style={styles.bizLine}>{data.client.email}</Text>
            {data.client.address ? <Text style={styles.bizLine}>{data.client.address}</Text> : null}
          </View>
          <View style={styles.metaRight}>
            <Text style={styles.metaLabel}>INVOICE</Text>
            <Text style={styles.invNum}>{data.meta.invoice_number}</Text>
            <Text style={styles.bizLine}>Issued: {formatDate(data.meta.issue_date)}</Text>
            <Text style={styles.bizLine}>Due: {formatDate(data.meta.due_date)}</Text>
          </View>
        </View>

        <View style={styles.table}>
          <View style={styles.thead}>
            <Text style={[styles.th, styles.col_desc]}>DESCRIPTION</Text>
            <Text style={[styles.th, styles.col_qty]}>QTY</Text>
            <Text style={[styles.th, styles.col_unit]}>UNIT</Text>
            <Text style={[styles.th, styles.col_total]}>TOTAL</Text>
          </View>
          {data.line_items.map((li, i) => (
            <View key={i} style={styles.tr}>
              <Text style={[styles.td, styles.col_desc]}>{li.description}</Text>
              <Text style={[styles.td, styles.col_qty]}>{li.quantity}</Text>
              <Text style={[styles.td, styles.col_unit]}>{formatCurrency(li.unit_price_cents, ccy)}</Text>
              <Text style={[styles.td, styles.col_total]}>
                {formatCurrency(Math.round(li.quantity * li.unit_price_cents), ccy)}
              </Text>
            </View>
          ))}
        </View>

        <View style={styles.totalsBox}>
          <View style={styles.totalRow}>
            <Text style={styles.totalLabel}>Subtotal</Text>
            <Text style={styles.totalVal}>{formatCurrency(totals.subtotal_cents, ccy)}</Text>
          </View>
          {totals.discount_cents > 0 ? (
            <View style={styles.totalRow}>
              <Text style={styles.totalLabel}>Discount</Text>
              <Text style={styles.totalVal}>− {formatCurrency(totals.discount_cents, ccy)}</Text>
            </View>
          ) : null}
          {totals.tax_cents > 0 ? (
            <View style={styles.totalRow}>
              <Text style={styles.totalLabel}>Tax ({data.tax_rate_pct ?? 0}%)</Text>
              <Text style={styles.totalVal}>{formatCurrency(totals.tax_cents, ccy)}</Text>
            </View>
          ) : null}
          <View style={styles.totalRow}>
            <Text style={styles.grandLabel}>Total</Text>
            <Text style={styles.grandVal}>{formatCurrency(totals.total_cents, ccy)}</Text>
          </View>
        </View>

        {data.payment?.url ? (
          <View style={styles.payBlock}>
            <Text style={styles.payText}>
              Pay online:{' '}
              <Link src={data.payment.url} style={styles.payLink}>{data.payment.url}</Link>
            </Text>
          </View>
        ) : null}

        {data.payment_instructions ? (
          <Text style={styles.payInstructions}>{data.payment_instructions}</Text>
        ) : null}

        {data.notes ? <Text style={styles.notes}>{data.notes}</Text> : null}
      </Page>
    </Document>
  );
}
```

- [ ] **Step 4: Run and watch it pass**

```bash
cd frontend && npm test -- ClassicTemplate
```

Expected: 4 passed, 1 snapshot written.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/invoice-generator/
git commit -m "feat(invoice-gen): add Classic PDF template with tests

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 3.3: Minimal template

**Files:**
- Create: `frontend/src/components/invoice-generator/pdf/MinimalTemplate.tsx`
- Create: `frontend/src/components/invoice-generator/__tests__/MinimalTemplate.test.tsx`

- [ ] **Step 1: Write the failing test**

Same `serialize` helper inlined. Test file:

```tsx
import { describe, it, expect } from 'vitest';
import React from 'react';
import { MinimalTemplate } from '../pdf/MinimalTemplate';
import { validInvoice } from './fixtures';

function serialize(node: React.ReactNode): unknown {
  if (node === null || node === undefined) return null;
  if (typeof node === 'string' || typeof node === 'number') return node;
  if (Array.isArray(node)) return node.map(serialize);
  if (React.isValidElement(node)) {
    const el = node as React.ReactElement<{ children?: React.ReactNode }>;
    const type = typeof el.type === 'string'
      ? el.type
      : (el.type as { displayName?: string; name?: string }).displayName
        ?? (el.type as { name?: string }).name
        ?? 'Unknown';
    const { children, ...rest } = (el.props ?? {}) as Record<string, unknown>;
    return { type, props: rest, children: serialize(children as React.ReactNode) };
  }
  return null;
}

describe('MinimalTemplate', () => {
  it('matches the snapshot for a full invoice', () => {
    const tree = serialize(<MinimalTemplate data={validInvoice()} />);
    expect(tree).toMatchSnapshot();
  });

  it('NEVER renders a logo, even if one is provided (by design)', () => {
    const data = validInvoice();
    data.sender.logo_url = 'https://example.com/logo.png';
    const tree = JSON.stringify(serialize(<MinimalTemplate data={data} />));
    expect(tree).not.toContain('"type":"Image"');
  });

  it('renders payment as an underlined link at the bottom when provided', () => {
    const data = validInvoice();
    data.payment = { url: 'https://buy.stripe.com/abc' };
    const tree = JSON.stringify(serialize(<MinimalTemplate data={data} />));
    expect(tree).toContain('"type":"Link"');
    expect(tree).toContain('Pay this invoice');
  });

  it('omits the payment block when payment is undefined', () => {
    const data = validInvoice();
    delete data.payment;
    const tree = JSON.stringify(serialize(<MinimalTemplate data={data} />));
    expect(tree).not.toContain('"type":"Link"');
  });
});
```

- [ ] **Step 2: Run and watch it fail**

- [ ] **Step 3: Implement MinimalTemplate**

```tsx
import { Document, Page, View, Text, Link, StyleSheet } from '@react-pdf/renderer';
import type { InvoiceData } from '../../../types';
import { computeTotals } from './shared/computeTotals';
import { formatCurrency } from './shared/formatCurrency';
import { formatDate } from './shared/formatDate';

interface Props { data: InvoiceData }

const styles = StyleSheet.create({
  page: { paddingTop: 72, paddingBottom: 72, paddingHorizontal: 64, fontFamily: 'Helvetica', fontSize: 10, color: '#000' },
  caption: { fontSize: 9, color: '#888', letterSpacing: 2, marginBottom: 4 },
  invNum: { fontSize: 28, marginBottom: 32 },
  pair: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 24 },
  block: { flexDirection: 'column', flexShrink: 1 },
  label: { fontSize: 8, color: '#888', letterSpacing: 1, marginBottom: 2 },
  textLine: { fontSize: 10, lineHeight: 1.4 },
  itemsHeader: { flexDirection: 'row', marginTop: 24, paddingBottom: 4 },
  hLabel: { fontSize: 8, color: '#888', letterSpacing: 1 },
  itemRow: { flexDirection: 'row', paddingVertical: 6 },
  col_desc: { flex: 4 },
  col_qty: { flex: 1, textAlign: 'right' },
  col_total: { flex: 2, textAlign: 'right' },
  ruleTop: { borderTopWidth: 1, marginTop: 8, paddingTop: 8 },
  totalRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 2 },
  totalLabel: { fontSize: 10 },
  totalVal: { fontSize: 10 },
  grandLabel: { fontSize: 12, fontWeight: 'bold', marginTop: 8 },
  grandVal: { fontSize: 12, fontWeight: 'bold', marginTop: 8 },
  payLink: { marginTop: 40, fontSize: 11, textDecoration: 'underline', color: '#000' },
  payInstructions: { marginTop: 8, fontSize: 9, lineHeight: 1.4 },
  notes: { marginTop: 32, fontSize: 9, lineHeight: 1.4 },
});

export function MinimalTemplate({ data }: Props) {
  const totals = computeTotals(data);
  const ccy = data.meta.currency;

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <Text style={styles.caption}>INVOICE</Text>
        <Text style={styles.invNum}>{data.meta.invoice_number}</Text>

        <View style={styles.pair}>
          <View style={styles.block}>
            <Text style={styles.label}>FROM</Text>
            <Text style={[styles.textLine, { fontWeight: 'bold' }]}>{data.sender.business_name}</Text>
            <Text style={styles.textLine}>{data.sender.your_name}</Text>
            <Text style={styles.textLine}>{data.sender.your_email}</Text>
            {data.sender.address ? <Text style={styles.textLine}>{data.sender.address}</Text> : null}
            {data.sender.tax_id ? <Text style={styles.textLine}>Tax ID: {data.sender.tax_id}</Text> : null}
          </View>
          <View style={styles.block}>
            <Text style={styles.label}>BILL TO</Text>
            <Text style={[styles.textLine, { fontWeight: 'bold' }]}>{data.client.name}</Text>
            <Text style={styles.textLine}>{data.client.email}</Text>
            {data.client.address ? <Text style={styles.textLine}>{data.client.address}</Text> : null}
          </View>
          <View style={styles.block}>
            <Text style={styles.label}>DATES</Text>
            <Text style={styles.textLine}>Issued {formatDate(data.meta.issue_date)}</Text>
            <Text style={styles.textLine}>Due {formatDate(data.meta.due_date)}</Text>
          </View>
        </View>

        <View style={styles.itemsHeader}>
          <Text style={[styles.hLabel, styles.col_desc]}>DESCRIPTION</Text>
          <Text style={[styles.hLabel, styles.col_qty]}>QTY × UNIT</Text>
          <Text style={[styles.hLabel, styles.col_total]}>AMOUNT</Text>
        </View>
        {data.line_items.map((li, i) => (
          <View key={i} style={styles.itemRow}>
            <Text style={[styles.textLine, styles.col_desc]}>{li.description}</Text>
            <Text style={[styles.textLine, styles.col_qty]}>
              {li.quantity} × {formatCurrency(li.unit_price_cents, ccy)}
            </Text>
            <Text style={[styles.textLine, styles.col_total]}>
              {formatCurrency(Math.round(li.quantity * li.unit_price_cents), ccy)}
            </Text>
          </View>
        ))}

        <View style={styles.ruleTop}>
          <View style={styles.totalRow}>
            <Text style={styles.totalLabel}>Subtotal</Text>
            <Text style={styles.totalVal}>{formatCurrency(totals.subtotal_cents, ccy)}</Text>
          </View>
          {totals.discount_cents > 0 ? (
            <View style={styles.totalRow}>
              <Text style={styles.totalLabel}>Discount</Text>
              <Text style={styles.totalVal}>− {formatCurrency(totals.discount_cents, ccy)}</Text>
            </View>
          ) : null}
          {totals.tax_cents > 0 ? (
            <View style={styles.totalRow}>
              <Text style={styles.totalLabel}>Tax ({data.tax_rate_pct ?? 0}%)</Text>
              <Text style={styles.totalVal}>{formatCurrency(totals.tax_cents, ccy)}</Text>
            </View>
          ) : null}
          <View style={styles.totalRow}>
            <Text style={styles.grandLabel}>Total</Text>
            <Text style={styles.grandVal}>{formatCurrency(totals.total_cents, ccy)}</Text>
          </View>
        </View>

        {data.payment?.url ? (
          <Link src={data.payment.url} style={styles.payLink}>
            {data.payment.label || 'Pay this invoice →'}
          </Link>
        ) : null}

        {data.payment_instructions ? (
          <Text style={styles.payInstructions}>{data.payment_instructions}</Text>
        ) : null}

        {data.notes ? <Text style={styles.notes}>{data.notes}</Text> : null}
      </Page>
    </Document>
  );
}
```

- [ ] **Step 4: Run and watch it pass**

```bash
cd frontend && npm test -- MinimalTemplate
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/invoice-generator/
git commit -m "feat(invoice-gen): add Minimal PDF template with tests

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 3.4: Template registry

**Files:**
- Create: `frontend/src/components/invoice-generator/pdf/index.ts`

This is a small wiring file — no separate test. Its correctness is covered transitively by Task 6 (`InvoiceGeneratorPage.test.tsx`).

- [ ] **Step 1: Create the registry**

```ts
import type { ComponentType } from 'react';
import type { InvoiceData, TemplateId } from '../../../types';
import { ModernTemplate } from './ModernTemplate';
import { ClassicTemplate } from './ClassicTemplate';
import { MinimalTemplate } from './MinimalTemplate';

export interface TemplateDescriptor {
  id: TemplateId;
  label: string;
  Component: ComponentType<{ data: InvoiceData }>;
  swatch: string;  // single hex color for the picker thumbnail
}

export const TEMPLATES: TemplateDescriptor[] = [
  { id: 'modern',  label: 'Modern',  Component: ModernTemplate,  swatch: '#FF6B35' },
  { id: 'classic', label: 'Classic', Component: ClassicTemplate, swatch: '#1F2937' },
  { id: 'minimal', label: 'Minimal', Component: MinimalTemplate, swatch: '#000000' },
];

export function getTemplate(id: TemplateId): TemplateDescriptor {
  const t = TEMPLATES.find(t => t.id === id);
  if (!t) throw new Error(`Unknown template id: ${id}`);
  return t;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/invoice-generator/pdf/index.ts
git commit -m "feat(invoice-gen): add template registry

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

# Phase 4 — UI components

## Task 4.1: `TemplatePicker`

**Files:**
- Create: `frontend/src/components/invoice-generator/TemplatePicker.tsx`
- Create: `frontend/src/components/invoice-generator/__tests__/TemplatePicker.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TemplatePicker } from '../TemplatePicker';

describe('TemplatePicker', () => {
  it('renders three options labeled Modern / Classic / Minimal', () => {
    render(<TemplatePicker value="modern" onChange={vi.fn()} />);
    expect(screen.getByRole('radio', { name: /modern/i })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /classic/i })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /minimal/i })).toBeInTheDocument();
  });

  it('marks the active option with aria-checked=true', () => {
    render(<TemplatePicker value="classic" onChange={vi.fn()} />);
    expect(screen.getByRole('radio', { name: /classic/i })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByRole('radio', { name: /modern/i })).toHaveAttribute('aria-checked', 'false');
  });

  it('calls onChange when a thumbnail is clicked', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<TemplatePicker value="modern" onChange={onChange} />);
    await user.click(screen.getByRole('radio', { name: /minimal/i }));
    expect(onChange).toHaveBeenCalledWith('minimal');
  });

  it('arrow-right moves selection forward and calls onChange', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<TemplatePicker value="modern" onChange={onChange} />);
    const modern = screen.getByRole('radio', { name: /modern/i });
    modern.focus();
    await user.keyboard('{ArrowRight}');
    expect(onChange).toHaveBeenLastCalledWith('classic');
  });

  it('arrow-left from first wraps to last', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<TemplatePicker value="modern" onChange={onChange} />);
    screen.getByRole('radio', { name: /modern/i }).focus();
    await user.keyboard('{ArrowLeft}');
    expect(onChange).toHaveBeenLastCalledWith('minimal');
  });

  it('Home jumps to first, End jumps to last', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<TemplatePicker value="classic" onChange={onChange} />);
    screen.getByRole('radio', { name: /classic/i }).focus();
    await user.keyboard('{End}');
    expect(onChange).toHaveBeenLastCalledWith('minimal');
    await user.keyboard('{Home}');
    expect(onChange).toHaveBeenLastCalledWith('modern');
  });
});
```

- [ ] **Step 2: Run and watch it fail**

- [ ] **Step 3: Implement TemplatePicker**

```tsx
import { useCallback, useRef } from 'react';
import { TEMPLATES } from './pdf';
import type { TemplateId } from '../../types';

interface Props {
  value: TemplateId;
  onChange: (next: TemplateId) => void;
}

export function TemplatePicker({ value, onChange }: Props) {
  const refs = useRef<Record<TemplateId, HTMLButtonElement | null>>({
    modern: null, classic: null, minimal: null,
  });

  const move = useCallback((delta: number) => {
    const idx = TEMPLATES.findIndex(t => t.id === value);
    const next = TEMPLATES[(idx + delta + TEMPLATES.length) % TEMPLATES.length];
    onChange(next.id);
    refs.current[next.id]?.focus();
  }, [value, onChange]);

  return (
    <div role="radiogroup" aria-label="Invoice template" className="grid grid-cols-3 gap-3">
      {TEMPLATES.map(t => {
        const active = t.id === value;
        return (
          <button
            key={t.id}
            ref={el => { refs.current[t.id] = el; }}
            role="radio"
            aria-checked={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(t.id)}
            onKeyDown={(e) => {
              if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); move(1); }
              else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
              else if (e.key === 'Home') { e.preventDefault(); onChange(TEMPLATES[0].id); refs.current[TEMPLATES[0].id]?.focus(); }
              else if (e.key === 'End') { e.preventDefault(); const last = TEMPLATES[TEMPLATES.length - 1]; onChange(last.id); refs.current[last.id]?.focus(); }
            }}
            className={`group flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all ${
              active
                ? 'border-violet-500 bg-violet-50 shadow-md'
                : 'border-slate-200 bg-white hover:border-slate-300'
            }`}
          >
            <div className="w-full h-16 rounded" style={{ background: t.swatch }} />
            <span className={`text-sm font-medium ${active ? 'text-violet-700' : 'text-slate-700'}`}>
              {t.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Run and watch it pass**

```bash
cd frontend && npm test -- TemplatePicker
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/invoice-generator/
git commit -m "feat(invoice-gen): add TemplatePicker (radiogroup with keyboard nav)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 4.2: `LineItemsEditor`

**Files:**
- Create: `frontend/src/components/invoice-generator/LineItemsEditor.tsx`
- Create: `frontend/src/components/invoice-generator/__tests__/LineItemsEditor.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LineItemsEditor } from '../LineItemsEditor';
import type { LineItem } from '../../../types';

describe('LineItemsEditor', () => {
  it('renders one empty row when starting empty', () => {
    render(<LineItemsEditor items={[]} onChange={vi.fn()} />);
    expect(screen.getAllByRole('row')).toHaveLength(2); // header + 1 row
  });

  it('renders supplied rows', () => {
    const items: LineItem[] = [
      { description: 'A', quantity: 1, unit_price_cents: 100 },
      { description: 'B', quantity: 2, unit_price_cents: 200 },
    ];
    render(<LineItemsEditor items={items} onChange={vi.fn()} />);
    expect(screen.getAllByRole('row')).toHaveLength(3); // header + 2
  });

  it('clicking "Add line" calls onChange with appended row', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<LineItemsEditor items={[{ description: 'A', quantity: 1, unit_price_cents: 100 }]} onChange={onChange} />);
    await user.click(screen.getByRole('button', { name: /add line/i }));
    expect(onChange).toHaveBeenCalledTimes(1);
    const next = onChange.mock.calls[0][0] as LineItem[];
    expect(next).toHaveLength(2);
    expect(next[1]).toEqual({ description: '', quantity: 1, unit_price_cents: 0 });
  });

  it('clicking remove removes the row at that index', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<LineItemsEditor
      items={[
        { description: 'A', quantity: 1, unit_price_cents: 100 },
        { description: 'B', quantity: 2, unit_price_cents: 200 },
      ]}
      onChange={onChange}
    />);
    const removes = screen.getAllByRole('button', { name: /remove/i });
    await user.click(removes[0]);
    const next = onChange.mock.calls[0][0] as LineItem[];
    expect(next).toEqual([{ description: 'B', quantity: 2, unit_price_cents: 200 }]);
  });

  it('cannot remove the last remaining row', () => {
    render(<LineItemsEditor items={[{ description: 'A', quantity: 1, unit_price_cents: 100 }]} onChange={vi.fn()} />);
    const removeBtn = screen.getByRole('button', { name: /remove/i });
    expect(removeBtn).toBeDisabled();
  });

  it('editing description updates the row', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<LineItemsEditor items={[{ description: '', quantity: 1, unit_price_cents: 0 }]} onChange={onChange} />);
    const descInput = screen.getByLabelText(/description/i);
    await user.type(descInput, 'X');
    const last = onChange.mock.calls.at(-1)![0] as LineItem[];
    expect(last[0].description).toBe('X');
  });

  it('typing "12.50" into unit price stores 1250 cents', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<LineItemsEditor items={[{ description: 'A', quantity: 1, unit_price_cents: 0 }]} onChange={onChange} />);
    const priceInput = screen.getByLabelText(/unit price/i);
    await user.type(priceInput, '12.50');
    const last = onChange.mock.calls.at(-1)![0] as LineItem[];
    expect(last[0].unit_price_cents).toBe(1250);
  });

  it('typing non-numeric into quantity is ignored gracefully', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<LineItemsEditor items={[{ description: 'A', quantity: 1, unit_price_cents: 0 }]} onChange={onChange} />);
    const qty = screen.getByLabelText(/quantity/i);
    await user.type(qty, 'abc');
    // quantity should not become NaN
    const last = onChange.mock.calls.at(-1)?.[0] as LineItem[] | undefined;
    if (last) expect(Number.isFinite(last[0].quantity)).toBe(true);
  });
});
```

- [ ] **Step 2: Run and watch it fail**

- [ ] **Step 3: Implement LineItemsEditor**

```tsx
import { Trash2, Plus } from 'lucide-react';
import type { LineItem } from '../../types';

interface Props {
  items: LineItem[];
  onChange: (items: LineItem[]) => void;
}

const displayed = (items: LineItem[]) =>
  items.length === 0 ? [{ description: '', quantity: 1, unit_price_cents: 0 }] : items;

function parsePriceToCents(raw: string): number {
  const cleaned = raw.replace(/[^\d.]/g, '');
  if (!cleaned) return 0;
  const f = parseFloat(cleaned);
  if (!Number.isFinite(f)) return 0;
  return Math.round(f * 100);
}

function parseQty(raw: string, fallback: number): number {
  const cleaned = raw.replace(/[^\d.]/g, '');
  if (!cleaned) return fallback;
  const f = parseFloat(cleaned);
  if (!Number.isFinite(f)) return fallback;
  return f;
}

export function LineItemsEditor({ items, onChange }: Props) {
  const rows = displayed(items);

  const updateRow = (i: number, patch: Partial<LineItem>) => {
    const next = rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r));
    onChange(next);
  };

  const addRow = () => onChange([...rows, { description: '', quantity: 1, unit_price_cents: 0 }]);

  const removeRow = (i: number) => {
    if (rows.length <= 1) return;
    onChange(rows.filter((_, idx) => idx !== i));
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm" role="table">
        <thead>
          <tr role="row" className="text-left text-xs uppercase text-slate-500">
            <th className="py-2">Description</th>
            <th className="py-2 w-20 text-right">Qty</th>
            <th className="py-2 w-28 text-right">Unit price</th>
            <th className="py-2 w-12" />
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr role="row" key={i} className="border-t border-slate-200">
              <td className="py-2 pr-2">
                <input
                  aria-label="Description"
                  className="w-full rounded border border-slate-300 px-2 py-1"
                  value={r.description}
                  onChange={(e) => updateRow(i, { description: e.target.value })}
                />
              </td>
              <td className="py-2 pr-2 text-right">
                <input
                  aria-label="Quantity"
                  className="w-full rounded border border-slate-300 px-2 py-1 text-right"
                  inputMode="decimal"
                  value={r.quantity}
                  onChange={(e) => updateRow(i, { quantity: parseQty(e.target.value, r.quantity) })}
                />
              </td>
              <td className="py-2 pr-2 text-right">
                <input
                  aria-label="Unit price"
                  className="w-full rounded border border-slate-300 px-2 py-1 text-right"
                  inputMode="decimal"
                  value={(r.unit_price_cents / 100).toFixed(2)}
                  onChange={(e) => updateRow(i, { unit_price_cents: parsePriceToCents(e.target.value) })}
                />
              </td>
              <td className="py-2 text-right">
                <button
                  type="button"
                  aria-label="Remove"
                  disabled={rows.length <= 1}
                  title={rows.length <= 1 ? 'Keep at least one row' : 'Remove row'}
                  onClick={() => removeRow(i)}
                  className="p-1 text-slate-500 hover:text-rose-600 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button
        type="button"
        onClick={addRow}
        className="mt-3 inline-flex items-center gap-1 text-sm text-violet-600 hover:text-violet-700 font-medium"
      >
        <Plus className="w-4 h-4" /> Add line
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Run and watch it pass**

```bash
cd frontend && npm test -- LineItemsEditor
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/invoice-generator/
git commit -m "feat(invoice-gen): add LineItemsEditor with add/remove/edit

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 4.3: `SenderProfileSection`

**Files:**
- Create: `frontend/src/components/invoice-generator/SenderProfileSection.tsx`

This component is a thin presentational wrapper — controlled by parent, passes `onChange` for individual fields. Tested transitively by `InvoiceGeneratorPage.test.tsx` (Phase 6). No dedicated test file to avoid testing implementation detail.

- [ ] **Step 1: Implement directly**

```tsx
import type { SenderProfile } from '../../types';

interface Props {
  value: SenderProfile;
  onChange: (next: SenderProfile) => void;
  errors?: Record<string, string>;
}

const fieldClasses = 'w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:ring-1 focus:ring-violet-500 outline-none';

export function SenderProfileSection({ value, onChange, errors = {} }: Props) {
  const set = <K extends keyof SenderProfile>(key: K, v: SenderProfile[K]) =>
    onChange({ ...value, [key]: v });

  return (
    <fieldset className="space-y-3">
      <legend className="text-xs uppercase font-semibold text-slate-500 tracking-wider mb-2">From</legend>

      <div>
        <label htmlFor="biz-name" className="block text-xs text-slate-600 mb-1">Business name *</label>
        <input id="biz-name" className={fieldClasses} value={value.business_name ?? ''}
               onChange={e => set('business_name', e.target.value)} />
        {errors['sender.business_name'] && <p className="text-xs text-rose-600 mt-1">{errors['sender.business_name']}</p>}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="your-name" className="block text-xs text-slate-600 mb-1">Your name *</label>
          <input id="your-name" className={fieldClasses} value={value.your_name ?? ''}
                 onChange={e => set('your_name', e.target.value)} />
          {errors['sender.your_name'] && <p className="text-xs text-rose-600 mt-1">{errors['sender.your_name']}</p>}
        </div>
        <div>
          <label htmlFor="your-email" className="block text-xs text-slate-600 mb-1">Your email *</label>
          <input id="your-email" type="email" className={fieldClasses} value={value.your_email ?? ''}
                 onChange={e => set('your_email', e.target.value)} />
          {errors['sender.your_email'] && <p className="text-xs text-rose-600 mt-1">{errors['sender.your_email']}</p>}
        </div>
      </div>

      <div>
        <label htmlFor="address" className="block text-xs text-slate-600 mb-1">Address</label>
        <textarea id="address" className={fieldClasses} rows={3}
                  value={value.address ?? ''} onChange={e => set('address', e.target.value)} />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="logo-url" className="block text-xs text-slate-600 mb-1">Logo URL</label>
          <input id="logo-url" className={fieldClasses} placeholder="https://…"
                 value={value.logo_url ?? ''} onChange={e => set('logo_url', e.target.value)} />
        </div>
        <div>
          <label htmlFor="tax-id" className="block text-xs text-slate-600 mb-1">Tax ID / VAT</label>
          <input id="tax-id" className={fieldClasses}
                 value={value.tax_id ?? ''} onChange={e => set('tax_id', e.target.value)} />
        </div>
      </div>
    </fieldset>
  );
}
```

> Note: Logo upload UX is out of scope for v1 — we accept a URL. If the user wants a logo, they paste a hosted URL (Imgur, their own CDN, etc.). Future work can add a dropzone that uploads to Supabase Storage and fills this field.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/invoice-generator/SenderProfileSection.tsx
git commit -m "feat(invoice-gen): add SenderProfileSection form block

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 4.4: `InvoiceGeneratorForm` (composes the form sections)

**Files:**
- Create: `frontend/src/components/invoice-generator/InvoiceGeneratorForm.tsx`

This component composes `SenderProfileSection`, `LineItemsEditor`, and inline blocks for client / meta / totals / payment / notes. It's controlled — parent owns state via `useInvoiceGeneratorForm`. Tested transitively in Phase 6.

- [ ] **Step 1: Implement**

```tsx
import type { InvoiceData, LineItem, SenderProfile } from '../../types';
import { SenderProfileSection } from './SenderProfileSection';
import { LineItemsEditor } from './LineItemsEditor';
import type { FormErrors } from '../../hooks/useInvoiceGeneratorForm';

interface Props {
  data: InvoiceData;
  errors: FormErrors;
  onSenderChange: (next: SenderProfile) => void;
  onField: (path: string, value: unknown) => void;
  onLineItemsChange: (items: LineItem[]) => void;
}

const field = 'w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:ring-1 focus:ring-violet-500 outline-none';
const legend = 'text-xs uppercase font-semibold text-slate-500 tracking-wider mb-2';

export function InvoiceGeneratorForm({ data, errors, onSenderChange, onField, onLineItemsChange }: Props) {
  return (
    <form className="space-y-8" onSubmit={(e) => e.preventDefault()}>
      <SenderProfileSection value={data.sender} onChange={onSenderChange} errors={errors} />

      <fieldset className="space-y-3">
        <legend className={legend}>Bill to</legend>
        <input className={field} placeholder="Client name" value={data.client.name}
               onChange={e => onField('client.name', e.target.value)} />
        {errors['client.name'] && <p className="text-xs text-rose-600">{errors['client.name']}</p>}
        <input className={field} type="email" placeholder="Client email" value={data.client.email}
               onChange={e => onField('client.email', e.target.value)} />
        {errors['client.email'] && <p className="text-xs text-rose-600">{errors['client.email']}</p>}
        <textarea className={field} rows={2} placeholder="Client address (optional)" value={data.client.address ?? ''}
                  onChange={e => onField('client.address', e.target.value)} />
      </fieldset>

      <fieldset className="grid grid-cols-2 gap-3">
        <legend className={`${legend} col-span-2`}>Invoice details</legend>
        <div>
          <label className="block text-xs text-slate-600 mb-1">Invoice number *</label>
          <input className={field} value={data.meta.invoice_number}
                 onChange={e => onField('meta.invoice_number', e.target.value)} />
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1">Currency</label>
          <select className={field} value={data.meta.currency}
                  onChange={e => onField('meta.currency', e.target.value)}>
            {['USD','EUR','GBP','INR','CAD','AUD'].map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1">Issue date *</label>
          <input className={field} type="date" value={data.meta.issue_date}
                 onChange={e => onField('meta.issue_date', e.target.value)} />
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1">Due date *</label>
          <input className={field} type="date" value={data.meta.due_date}
                 onChange={e => onField('meta.due_date', e.target.value)} />
          {errors['meta.due_date'] && <p className="text-xs text-rose-600">{errors['meta.due_date']}</p>}
        </div>
      </fieldset>

      <fieldset className="space-y-3">
        <legend className={legend}>Line items</legend>
        <LineItemsEditor items={data.line_items} onChange={onLineItemsChange} />
        {errors['line_items'] && <p className="text-xs text-rose-600">{errors['line_items']}</p>}
      </fieldset>

      <fieldset className="grid grid-cols-3 gap-3">
        <legend className={`${legend} col-span-3`}>Totals adjustments</legend>
        <div>
          <label className="block text-xs text-slate-600 mb-1">Tax rate (%)</label>
          <input className={field} inputMode="decimal" value={data.tax_rate_pct ?? ''}
                 onChange={e => {
                   const v = e.target.value;
                   onField('tax_rate_pct', v === '' ? undefined : Number(v));
                 }} />
          {errors['tax_rate_pct'] && <p className="text-xs text-rose-600">{errors['tax_rate_pct']}</p>}
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1">Discount</label>
          <select className={field} value={data.discount?.kind ?? ''}
                  onChange={e => {
                    if (!e.target.value) onField('discount', undefined);
                    else onField('discount', { kind: e.target.value, value: data.discount?.value ?? 0 });
                  }}>
            <option value="">None</option>
            <option value="flat">Flat amount</option>
            <option value="pct">Percentage</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1">Discount value</label>
          <input className={field} inputMode="decimal" disabled={!data.discount}
                 value={data.discount?.value ?? ''}
                 onChange={e => onField('discount.value', Number(e.target.value))} />
          {errors['discount.value'] && <p className="text-xs text-rose-600">{errors['discount.value']}</p>}
        </div>
      </fieldset>

      <fieldset className="space-y-3">
        <legend className={legend}>Payment</legend>
        <input className={field} placeholder="Payment URL (Stripe, LemonSqueezy, PayPal, etc.)"
               value={data.payment?.url ?? ''}
               onChange={e => onField('payment', e.target.value
                 ? { ...(data.payment ?? {}), url: e.target.value }
                 : undefined)} />
        {errors['payment.url'] && <p className="text-xs text-rose-600">{errors['payment.url']}</p>}
        <input className={field} placeholder='Button label (defaults to "Pay invoice")'
               value={data.payment?.label ?? ''}
               disabled={!data.payment?.url}
               onChange={e => onField('payment.label', e.target.value)} />
        <textarea className={field} rows={3} placeholder="Bank wire / additional payment instructions (optional)"
                  value={data.payment_instructions ?? ''}
                  onChange={e => onField('payment_instructions', e.target.value)} />
      </fieldset>

      <fieldset>
        <legend className={legend}>Notes</legend>
        <textarea className={field} rows={3} placeholder="Thank you for your business, terms, etc."
                  value={data.notes ?? ''}
                  onChange={e => onField('notes', e.target.value)} />
      </fieldset>
    </form>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/invoice-generator/InvoiceGeneratorForm.tsx
git commit -m "feat(invoice-gen): add InvoiceGeneratorForm composition

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 4.5: `PDFPreview`

**Files:**
- Create: `frontend/src/components/invoice-generator/PDFPreview.tsx`

Thin wrapper around `<PDFViewer>` from `@react-pdf/renderer`. No unit test — `<PDFViewer>` uses an iframe + native PDF renderer, which jsdom can't host. Covered manually in the verification phase.

- [ ] **Step 1: Implement**

```tsx
import { PDFViewer } from '@react-pdf/renderer';
import { getTemplate } from './pdf';
import type { InvoiceData } from '../../types';

interface Props {
  data: InvoiceData;
  className?: string;
}

export function PDFPreview({ data, className }: Props) {
  const { Component } = getTemplate(data.template);
  return (
    <div className={className ?? 'w-full h-full min-h-[600px]'}>
      <PDFViewer width="100%" height="100%" showToolbar={false}>
        <Component data={data} />
      </PDFViewer>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/invoice-generator/PDFPreview.tsx
git commit -m "feat(invoice-gen): add PDFPreview wrapper

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

# Phase 5 — Backend

## Task 5.1: Migration — `users.sender_profile`

**Files:**
- Modify: `supabase/schema.sql`

- [ ] **Step 1: Append migration**

Append at the end of `supabase/schema.sql`:

```sql
-- Sender profile (used by the Invoice Generator module).
ALTER TABLE users ADD COLUMN IF NOT EXISTS sender_profile JSONB NOT NULL DEFAULT '{}'::jsonb;
```

- [ ] **Step 2: Apply via Supabase MCP**

Run the migration in the project's remote Supabase. The implementer must use the MCP `apply_migration` tool — this plan does not embed the credentials. The migration name should be `add_users_sender_profile`. After applying, verify with `list_tables` that `users.sender_profile` exists.

- [ ] **Step 3: Commit**

```bash
git add supabase/schema.sql
git commit -m "feat(db): add users.sender_profile JSONB for invoice generator

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 5.2: Backend test scaffolding (pytest)

**Files:**
- Create: `tests/__init__.py` (empty)
- Create: `tests/conftest.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Append to `requirements.txt`**

```
pytest==8.3.4
pytest-asyncio==0.24.0
httpx==0.28.1
```

(If httpx is already pinned to a different version, keep the existing pin — don't downgrade other deps.)

- [ ] **Step 2: Install**

```bash
pip install -r requirements.txt
```

- [ ] **Step 3: Create `tests/__init__.py`**

Empty file.

- [ ] **Step 4: Create `tests/conftest.py`**

```python
import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Ensure required env vars exist *before* importing the app.
os.environ.setdefault("GROQ_API_KEY", "test")
os.environ.setdefault("TAVILY_API_KEY", "test")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test")
os.environ.setdefault("GOOGLE_REDIRECT_URI", "http://localhost:5173/auth/google/callback")
os.environ.setdefault("SECRET_KEY", "Mn1uJrEa0v7P9z8X2Q3R4S5T6U7W8Y9Z0a1B2C3D4E5=")  # 32-byte b64
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_KEY", "test")

from api.index import app  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
```

- [ ] **Step 5: Smoke-test it works**

Add `tests/test_smoke.py`:

```python
import pytest

@pytest.mark.asyncio
async def test_health(client):
    # Hit any GET that returns without auth — we don't have /health,
    # but the openapi endpoint always responds.
    r = await client.get("/openapi.json")
    assert r.status_code == 200
```

Run:

```bash
pytest tests/test_smoke.py -v
```

Expected: 1 passed.

- [ ] **Step 6: Delete the smoke test**

```bash
rm tests/test_smoke.py
```

- [ ] **Step 7: Commit**

```bash
git add tests/__init__.py tests/conftest.py requirements.txt
git commit -m "test: add pytest scaffolding for backend tests

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 5.3: Sender profile endpoints

**Files:**
- Modify: `api/index.py`
- Create: `tests/test_sender_profile.py`

**Note for the implementer:** Before writing tests, **read** the current `api/index.py` to discover how existing endpoints handle:
- The `Depends(get_current_user)` (or equivalent) pattern for `current_user_id`
- How Supabase reads/writes are wired (`src/db.py` helpers)
- Whether guests are allowed (existing pattern: yes, per-session `guest-<uuid>`)

Mirror that style. If the existing helpers don't expose `update_user` for arbitrary JSONB fields, add one in `src/db.py` and test it via the endpoint tests.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_sender_profile.py`:

```python
import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_get_sender_profile_empty_for_new_user(client):
    # New guest gets a guest-<uuid> session cookie; profile defaults to {}.
    r = await client.get("/api/users/me/sender-profile")
    assert r.status_code == 200
    assert r.json() == {}


@pytest.mark.asyncio
async def test_patch_then_get_round_trip(client):
    payload = {
        "business_name": "Acme",
        "your_name": "Jane",
        "your_email": "jane@acme.example",
    }
    r = await client.patch("/api/users/me/sender-profile", json=payload)
    assert r.status_code == 200
    r2 = await client.get("/api/users/me/sender-profile")
    assert r2.status_code == 200
    body = r2.json()
    assert body["business_name"] == "Acme"
    assert body["your_email"] == "jane@acme.example"


@pytest.mark.asyncio
async def test_patch_rejects_unknown_keys(client):
    r = await client.patch("/api/users/me/sender-profile", json={"haxx": "nope"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_patch_rejects_invalid_email(client):
    r = await client.patch("/api/users/me/sender-profile", json={"your_email": "nope"})
    assert r.status_code == 422
```

- [ ] **Step 2: Run and watch them fail**

```bash
pytest tests/test_sender_profile.py -v
```

Expected: 4 fail with 404 (endpoints don't exist yet).

- [ ] **Step 3: Add the endpoints**

In `api/index.py`, find an appropriate location (near the existing `/api/auth/me` route — sender profile is a "me" endpoint). Add:

```python
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional


class SenderProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    business_name: Optional[str] = None
    your_name: Optional[str] = None
    your_email: Optional[EmailStr] = None
    address: Optional[str] = None
    logo_url: Optional[str] = None
    tax_id: Optional[str] = None


@app.get("/api/users/me/sender-profile")
async def get_sender_profile(request: Request):
    user_id = resolve_current_user_id(request)  # use the existing helper name
    user = db.get_user(user_id)
    return (user or {}).get("sender_profile") or {}


@app.patch("/api/users/me/sender-profile")
async def patch_sender_profile(request: Request, profile: SenderProfile):
    user_id = resolve_current_user_id(request)
    # Merge with existing — PATCH semantics.
    existing = (db.get_user(user_id) or {}).get("sender_profile") or {}
    incoming = profile.model_dump(exclude_unset=True)
    merged = {**existing, **incoming}
    db.update_user(user_id, {"sender_profile": merged})
    return merged
```

> The implementer must adapt `resolve_current_user_id` to whatever the existing codebase actually calls the helper (it may be `get_current_user_id`, a `Depends` dependency, or inline). Likewise, `db.get_user` / `db.update_user` may need to be added to `src/db.py` if absent.

- [ ] **Step 4: Run and watch the tests pass**

```bash
pytest tests/test_sender_profile.py -v
```

Expected: 4 passed.

If the env doesn't have a real Supabase, tests may need to use `unittest.mock.patch` on `db.get_user` / `db.update_user`. Update the conftest fixture to patch these for the test session if local Supabase isn't reachable.

- [ ] **Step 5: Commit**

```bash
git add api/index.py src/db.py tests/test_sender_profile.py
git commit -m "feat(api): add sender profile GET/PATCH endpoints

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 5.4: `POST /api/invoices/generated`

**Files:**
- Modify: `api/index.py`
- Create: `tests/test_generated_invoice.py`

This endpoint accepts JSON describing an invoice that the frontend has *already uploaded to Supabase Storage* (the frontend handles the upload directly using an existing storage-write endpoint or signed URL — see Task 6.4). The endpoint validates the storage path belongs to the calling user and creates the `invoices` row.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_generated_invoice.py`:

```python
import pytest
from unittest.mock import patch


VALID_PAYLOAD = {
    "invoice_id": "INV-2026-001",
    "client_name": "BigCorp",
    "client_email": "ap@bigcorp.example",
    "invoice_amount_cents": 150000,
    "due_date": "2026-05-15",
    "jurisdiction": "California",
    "storage_path": "generated/{user_id}/INV-2026-001-abc123.pdf",
    "file_name": "INV-2026-001.pdf",
    "file_size": 12345,
}


@pytest.mark.asyncio
async def test_creates_invoice_row(client):
    # Get the auto-issued guest user id from cookies after first request.
    r0 = await client.get("/api/users/me/sender-profile")
    assert r0.status_code == 200
    user_id = next((c.value for c in client.cookies.jar if c.name == "guest_id"), None)
    assert user_id is not None

    payload = {**VALID_PAYLOAD, "storage_path": VALID_PAYLOAD["storage_path"].format(user_id=user_id)}
    r = await client.post("/api/invoices/generated", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["invoice_id"] == "INV-2026-001"
    assert body["escalation_level"] == 0
    assert body["invoice_file_path"] == payload["storage_path"]


@pytest.mark.asyncio
async def test_rejects_storage_path_for_other_user(client):
    payload = {**VALID_PAYLOAD, "storage_path": "generated/some-other-user/INV-abc.pdf"}
    r = await client.post("/api/invoices/generated", json=payload)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_rejects_duplicate_invoice_id(client):
    r0 = await client.get("/api/users/me/sender-profile")
    user_id = next((c.value for c in client.cookies.jar if c.name == "guest_id"), None)
    payload = {**VALID_PAYLOAD, "storage_path": VALID_PAYLOAD["storage_path"].format(user_id=user_id)}
    await client.post("/api/invoices/generated", json=payload)
    r = await client.post("/api/invoices/generated", json=payload)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_rejects_invalid_payload(client):
    r = await client.post("/api/invoices/generated", json={"client_name": "X"})
    assert r.status_code == 422
```

> The cookie name `guest_id` is a placeholder — the implementer must use whatever name `src/db.py:ensure_guest_user` actually sets. Adjust the tests accordingly when the actual cookie name is discovered.

- [ ] **Step 2: Run and watch the tests fail**

```bash
pytest tests/test_generated_invoice.py -v
```

- [ ] **Step 3: Implement the endpoint**

In `api/index.py`:

```python
from datetime import datetime
from fastapi import HTTPException
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional


class GenerateInvoiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invoice_id: str = Field(min_length=1, max_length=64)
    client_name: str = Field(min_length=1)
    client_email: EmailStr
    invoice_amount_cents: int = Field(ge=0)
    due_date: str  # yyyy-mm-dd
    jurisdiction: Optional[str] = None
    storage_path: str = Field(min_length=1)
    file_name: str = Field(min_length=1)
    file_size: int = Field(ge=0)


@app.post("/api/invoices/generated", status_code=201)
async def create_generated_invoice(request: Request, payload: GenerateInvoiceRequest):
    user_id = resolve_current_user_id(request)

    # Storage path ownership check: must be under generated/<user_id>/...
    prefix = f"generated/{user_id}/"
    if not payload.storage_path.startswith(prefix):
        raise HTTPException(
            status_code=403,
            detail=f"Storage path must be under {prefix}",
        )

    # Duplicate invoice_id check (app-level).
    existing = db.find_invoice_by_external_id(user_id, payload.invoice_id)
    if existing:
        raise HTTPException(status_code=409, detail="Invoice ID already exists")

    # Compute days_overdue at creation time (negative if due in the future).
    today = datetime.utcnow().date()
    due = datetime.strptime(payload.due_date, "%Y-%m-%d").date()
    days_overdue = max(0, (today - due).days)

    invoice = db.create_invoice({
        "user_id": user_id,
        "invoice_id_external": payload.invoice_id,  # if your db uses this column name
        "client_name": payload.client_name,
        "client_email": payload.client_email,
        "invoice_amount": payload.invoice_amount_cents / 100,  # existing schema is REAL
        "days_overdue": days_overdue,
        "jurisdiction": payload.jurisdiction,
        "escalation_level": 0,
        "status": "active",
        "invoice_file_path": payload.storage_path,
        "invoice_file_name": payload.file_name,
        "invoice_file_mime": "application/pdf",
        "invoice_file_size": payload.file_size,
    })
    return invoice
```

> **Implementer adapts to existing `db.py` API.** If `db.find_invoice_by_external_id` doesn't exist, add it (or use whatever uniqueness scheme matches the current upload flow). If the existing `invoices.id` column is what holds the user-facing invoice number, drop the separate `invoice_id_external` field and use `id` directly with a `(user_id, id)` uniqueness check.

- [ ] **Step 4: Run and watch the tests pass**

```bash
pytest tests/test_generated_invoice.py -v
```

- [ ] **Step 5: Commit**

```bash
git add api/index.py src/db.py tests/test_generated_invoice.py
git commit -m "feat(api): add POST /api/invoices/generated endpoint

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

# Phase 6 — Wire the page

## Task 6.1: `useSenderProfile` hook + API client methods

**Files:**
- Modify: `frontend/src/api.ts`
- Create: `frontend/src/hooks/useSenderProfile.ts`

No dedicated tests — covered by Task 6.4 (`InvoiceGeneratorPage.test.tsx`).

- [ ] **Step 1: Extend `api.ts`**

Add to the `api` object in `frontend/src/api.ts`:

```ts
getSenderProfile: () =>
  request<import('./types').SenderProfile>('/api/users/me/sender-profile'),

updateSenderProfile: (data: Partial<import('./types').SenderProfile>) =>
  request<import('./types').SenderProfile>('/api/users/me/sender-profile', {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),

createGeneratedInvoice: (data: import('./types').GenerateInvoiceRequest) =>
  request<import('./types').Invoice>('/api/invoices/generated', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

uploadGeneratedInvoicePdf: async (blob: Blob, invoiceId: string): Promise<{
  storage_path: string;
  file_name: string;
  file_size: number;
}> => {
  // Reuse the existing multipart upload flow if `parseInvoiceFile` / `createInvoiceFromUpload`
  // accepts a generated PDF — OR add a dedicated upload endpoint. For v1 we use a
  // dedicated multipart POST to `/api/invoices/generated/upload` that returns the
  // storage path.  Implementer: choose whichever fits the existing pattern best.
  const fd = new FormData();
  const file_name = `${invoiceId}.pdf`;
  fd.append('file', new File([blob], file_name, { type: 'application/pdf' }));
  fd.append('invoice_id', invoiceId);
  return requestForm<{ storage_path: string; file_name: string; file_size: number }>(
    '/api/invoices/generated/upload',
    fd,
  );
},
```

> The `uploadGeneratedInvoicePdf` endpoint contract is intentionally simple: accept multipart, store under `invoice-files/generated/<user_id>/<invoice_id>-<uuid>.pdf`, return the path. **This is a fifth backend route to add as part of this task.** Add the route in `api/index.py` and a test for it in `tests/test_generated_invoice.py`:
>
> ```python
> @pytest.mark.asyncio
> async def test_upload_generated_pdf_stores_under_user(client):
>     r = await client.post(
>         "/api/invoices/generated/upload",
>         files={"file": ("INV-1.pdf", b"%PDF-1.4 fake", "application/pdf")},
>         data={"invoice_id": "INV-1"},
>     )
>     assert r.status_code == 200
>     body = r.json()
>     assert body["storage_path"].startswith("generated/")
>     assert body["storage_path"].endswith(".pdf")
>     assert body["file_size"] > 0
> ```
>
> Add this test in the same commit as the upload endpoint. Use the existing Supabase Storage upload helper (`upload_invoice_file` or similar in `src/db.py`) — the prefix changes from `uploaded/` to `generated/`.

- [ ] **Step 2: Create `useSenderProfile.ts`**

```ts
import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';
import type { SenderProfile } from '../types';

export function useSenderProfile() {
  const [profile, setProfile] = useState<SenderProfile>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.getSenderProfile()
      .then(p => { if (!cancelled) setProfile(p ?? {}); })
      .catch(e => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const save = useCallback(async (next: SenderProfile) => {
    const saved = await api.updateSenderProfile(next);
    setProfile(saved);
    return saved;
  }, []);

  return { profile, loading, error, setProfile, save };
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api.ts frontend/src/hooks/useSenderProfile.ts api/index.py src/db.py tests/test_generated_invoice.py
git commit -m "feat(invoice-gen): add upload endpoint + frontend API + sender profile hook

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 6.2: `InvoiceGeneratorPage` — basic render + happy-path tests

**Files:**
- Create: `frontend/src/components/invoice-generator/InvoiceGeneratorPage.tsx`
- Create: `frontend/src/components/invoice-generator/__tests__/InvoiceGeneratorPage.test.tsx`

This is the keystone test file. We mock `@react-pdf/renderer`'s blob generator and the API client; we exercise the full path from form fill to save.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/invoice-generator/__tests__/InvoiceGeneratorPage.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { InvoiceGeneratorPage } from '../InvoiceGeneratorPage';

// Mock @react-pdf/renderer — PDFViewer needs an iframe (jsdom can't host it),
// and pdf() returns a stream we don't want to actually generate.
vi.mock('@react-pdf/renderer', async () => {
  const actual = await vi.importActual<typeof import('@react-pdf/renderer')>('@react-pdf/renderer');
  return {
    ...actual,
    PDFViewer: ({ children }: { children: React.ReactNode }) => <div data-testid="pdf-viewer">{children}</div>,
    pdf: () => ({
      toBlob: async () => new Blob(['%PDF-1.4 fake'], { type: 'application/pdf' }),
    }),
  };
});

// Mock the api module.
vi.mock('../../../api', () => ({
  api: {
    getSenderProfile: vi.fn(),
    updateSenderProfile: vi.fn(),
    uploadGeneratedInvoicePdf: vi.fn(),
    createGeneratedInvoice: vi.fn(),
  },
}));

import { api } from '../../../api';

function renderPage(initialPath = '/generate-invoice') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/generate-invoice" element={<InvoiceGeneratorPage />} />
        <Route path="/invoice/:invoiceId" element={<div data-testid="invoice-detail" />} />
        <Route path="/dashboard" element={<div data-testid="dashboard" />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  (api.getSenderProfile as ReturnType<typeof vi.fn>).mockResolvedValue({
    business_name: 'Acme', your_name: 'Jane', your_email: 'jane@acme.example',
  });
  (api.uploadGeneratedInvoicePdf as ReturnType<typeof vi.fn>).mockResolvedValue({
    storage_path: 'generated/u1/INV-1-abc.pdf',
    file_name: 'INV-1.pdf',
    file_size: 1234,
  });
  (api.createGeneratedInvoice as ReturnType<typeof vi.fn>).mockResolvedValue({
    id: 'inv-uuid-1', invoice_id: 'INV-1', client_name: 'Z', client_email: 'z@z.example',
    invoice_amount: 150, amount_paid: 0, balance_due: 150, days_overdue: 0,
    jurisdiction: 'CA', escalation_level: 0, communication_history: [], status: 'active',
  });
});

describe('InvoiceGeneratorPage', () => {
  it('pre-fills sender from profile and shows the form', async () => {
    renderPage();
    await waitFor(() => expect((api.getSenderProfile as ReturnType<typeof vi.fn>)).toHaveBeenCalled());
    expect(screen.getByDisplayValue('Acme')).toBeInTheDocument();
    expect(screen.getByDisplayValue('jane@acme.example')).toBeInTheDocument();
  });

  it('renders all three template options', async () => {
    renderPage();
    expect(await screen.findByRole('radio', { name: /modern/i })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /classic/i })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /minimal/i })).toBeInTheDocument();
  });

  it('disables Save when form is invalid', async () => {
    (api.getSenderProfile as ReturnType<typeof vi.fn>).mockResolvedValue({});
    renderPage();
    await waitFor(() => expect((api.getSenderProfile as ReturnType<typeof vi.fn>)).toHaveBeenCalled());
    const save = screen.getByRole('button', { name: /save & download/i });
    expect(save).toBeDisabled();
  });

  it('Save & Download — uploads, creates row, navigates to /invoice/:id', async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByDisplayValue('Acme');

    // Fill the rest of the form. Invoice number + dates are pre-seeded;
    // the single seeded line item has an empty description so we fill it.
    await user.type(screen.getByPlaceholderText(/client name/i), 'BigCorp');
    await user.type(screen.getByPlaceholderText(/client email/i), 'ap@bigcorp.example');
    await user.type(screen.getByLabelText(/^description$/i), 'Design work');
    const priceInput = screen.getByLabelText(/unit price/i);
    await user.clear(priceInput);
    await user.type(priceInput, '150.00');

    const save = screen.getByRole('button', { name: /save & download/i });
    await waitFor(() => expect(save).not.toBeDisabled());
    await user.click(save);

    await waitFor(() => {
      expect((api.uploadGeneratedInvoicePdf as ReturnType<typeof vi.fn>)).toHaveBeenCalledTimes(1);
    });
    expect((api.createGeneratedInvoice as ReturnType<typeof vi.fn>)).toHaveBeenCalledTimes(1);
    // Navigation happens to /invoice/inv-uuid-1
    expect(await screen.findByTestId('invoice-detail')).toBeInTheDocument();
  });

  it('does NOT call createGeneratedInvoice if upload fails', async () => {
    (api.uploadGeneratedInvoicePdf as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('upload failed'));
    const user = userEvent.setup();
    renderPage();
    await screen.findByDisplayValue('Acme');
    await user.type(screen.getByPlaceholderText(/client name/i), 'BigCorp');
    await user.type(screen.getByPlaceholderText(/client email/i), 'ap@bigcorp.example');
    await user.type(screen.getByLabelText(/^description$/i), 'Design work');
    const priceInput = screen.getByLabelText(/unit price/i);
    await user.clear(priceInput);
    await user.type(priceInput, '150.00');

    await user.click(screen.getByRole('button', { name: /save & download/i }));

    await waitFor(() => {
      expect(screen.getByText(/upload failed/i)).toBeInTheDocument();
    });
    expect((api.createGeneratedInvoice as ReturnType<typeof vi.fn>)).not.toHaveBeenCalled();
  });

  it('Download-only button does NOT call upload or create — pure local download', async () => {
    const user = userEvent.setup();
    // Stub URL.createObjectURL because jsdom doesn't implement it.
    const createUrl = vi.fn(() => 'blob:mock');
    URL.createObjectURL = createUrl;
    URL.revokeObjectURL = vi.fn();

    renderPage();
    await screen.findByDisplayValue('Acme');
    await user.type(screen.getByPlaceholderText(/client name/i), 'BigCorp');
    await user.type(screen.getByPlaceholderText(/client email/i), 'ap@bigcorp.example');
    await user.type(screen.getByLabelText(/^description$/i), 'Design work');
    const priceInput = screen.getByLabelText(/unit price/i);
    await user.clear(priceInput);
    await user.type(priceInput, '150.00');

    await user.click(screen.getByRole('button', { name: /^download pdf$/i }));

    await waitFor(() => expect(createUrl).toHaveBeenCalled());
    expect((api.uploadGeneratedInvoicePdf as ReturnType<typeof vi.fn>)).not.toHaveBeenCalled();
    expect((api.createGeneratedInvoice as ReturnType<typeof vi.fn>)).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run and watch them fail**

```bash
cd frontend && npm test -- InvoiceGeneratorPage
```

Expected: all fail with "Cannot find module".

- [ ] **Step 3: Implement the page**

Create `frontend/src/components/invoice-generator/InvoiceGeneratorPage.tsx`:

```tsx
import { useState, useCallback, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { pdf } from '@react-pdf/renderer';
import { useSenderProfile } from '../../hooks/useSenderProfile';
import { useInvoiceGeneratorForm } from '../../hooks/useInvoiceGeneratorForm';
import { InvoiceGeneratorForm } from './InvoiceGeneratorForm';
import { TemplatePicker } from './TemplatePicker';
import { PDFPreview } from './PDFPreview';
import { computeTotals } from './pdf/shared/computeTotals';
import { getTemplate } from './pdf';
import { api } from '../../api';
import type { InvoiceData, SenderProfile, LineItem, TemplateId } from '../../types';

const today = () => new Date().toISOString().slice(0, 10);
const addDays = (iso: string, days: number) => {
  const d = new Date(iso);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
};

function seed(sender: SenderProfile): InvoiceData {
  return {
    sender,
    client: { name: '', email: '' },
    meta: {
      invoice_number: `INV-${new Date().getFullYear()}-001`,
      issue_date: today(),
      due_date: addDays(today(), 14),
      currency: 'USD',
    },
    line_items: [{ description: '', quantity: 1, unit_price_cents: 0 }],
    template: 'modern',
  };
}

export function InvoiceGeneratorPage() {
  const navigate = useNavigate();
  const { profile, loading: loadingProfile, save: saveProfile } = useSenderProfile();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initial = useMemo(() => seed(profile), [profile]);
  const { data, errors, isValid, setField, setLineItems, setData } = useInvoiceGeneratorForm(initial);

  // Re-seed when profile loads.
  useEffect(() => {
    if (!loadingProfile) setData(seed(profile));
  }, [loadingProfile, profile, setData]);

  const setSender = useCallback((next: SenderProfile) => {
    setField('sender', next);
  }, [setField]);

  const setTemplate = useCallback((next: TemplateId) => {
    setField('template', next);
  }, [setField]);

  const setLineItemsCb = useCallback((items: LineItem[]) => {
    setLineItems(items);
  }, [setLineItems]);

  const buildBlob = useCallback(async (): Promise<Blob> => {
    const { Component } = getTemplate(data.template);
    return await pdf(<Component data={data} />).toBlob();
  }, [data]);

  const triggerDownload = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const onDownload = useCallback(async () => {
    setError(null);
    try {
      const blob = await buildBlob();
      triggerDownload(blob, `${data.meta.invoice_number}.pdf`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [buildBlob, data.meta.invoice_number]);

  const onSaveAndDownload = useCallback(async () => {
    setError(null);
    setSubmitting(true);
    try {
      // Persist sender profile changes so the next invoice pre-fills.
      await saveProfile(data.sender).catch(() => { /* non-blocking */ });

      const blob = await buildBlob();
      const { storage_path, file_name, file_size } =
        await api.uploadGeneratedInvoicePdf(blob, data.meta.invoice_number);
      const totals = computeTotals(data);
      const invoice = await api.createGeneratedInvoice({
        invoice_id: data.meta.invoice_number,
        client_name: data.client.name,
        client_email: data.client.email,
        invoice_amount_cents: totals.total_cents,
        due_date: data.meta.due_date,
        jurisdiction: undefined,
        storage_path, file_name, file_size,
      });
      triggerDownload(blob, file_name);
      navigate(`/invoice/${invoice.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }, [buildBlob, data, navigate, saveProfile]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Generate invoice</h1>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onDownload}
            disabled={!isValid || submitting}
            className="px-4 py-2 text-sm font-medium text-slate-700 border border-slate-300 rounded-md hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Download PDF
          </button>
          <button
            type="button"
            onClick={onSaveAndDownload}
            disabled={!isValid || submitting}
            className="px-4 py-2 text-sm font-medium text-white bg-violet-600 rounded-md hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? 'Saving…' : 'Save & Download'}
          </button>
        </div>
      </header>

      {error && <div role="alert" className="rounded border border-rose-300 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}

      <section className="space-y-3">
        <label className="text-xs uppercase font-semibold text-slate-500 tracking-wider">Template</label>
        <TemplatePicker value={data.template} onChange={setTemplate} />
      </section>

      <div className="grid lg:grid-cols-2 gap-8">
        <InvoiceGeneratorForm
          data={data}
          errors={errors}
          onSenderChange={setSender}
          onField={setField}
          onLineItemsChange={setLineItemsCb}
        />
        <div className="sticky top-4 h-[800px]">
          <PDFPreview data={data} className="w-full h-full border rounded-md overflow-hidden bg-white" />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run and watch the tests pass**

```bash
cd frontend && npm test -- InvoiceGeneratorPage
```

Expected: 6 passed.

If a test fails because the form's defaults make it invalid initially, adjust the seed (e.g., ensure invoice_number defaults to a non-empty value) — but **don't** change the form fields tests fill in. The test list defines the contract.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/invoice-generator/InvoiceGeneratorPage.tsx frontend/src/components/invoice-generator/__tests__/InvoiceGeneratorPage.test.tsx
git commit -m "feat(invoice-gen): add InvoiceGeneratorPage with full-flow tests

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 6.3: Add the route to `App.tsx`

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add the route**

Inside `<Routes>`, after the existing `/invoice/:invoiceId` route, add:

```tsx
<Route path="/generate-invoice" element={
  <ProtectedRoute>
    <Layout>
      <InvoiceGeneratorPage />
    </Layout>
  </ProtectedRoute>
} />
```

And add the import at the top:

```tsx
import { InvoiceGeneratorPage } from './components/invoice-generator/InvoiceGeneratorPage'
```

> Important: this route uses `<ProtectedRoute>`, the same gate as `/dashboard`. Guests can still create invoices because the existing `ProtectedRoute` may currently treat guests as authed (per the codebase's guest-session pattern). Verify behavior in the smoke phase. If guests are blocked by `ProtectedRoute`, drop the wrapper and rely on the guest cookie pattern.

- [ ] **Step 2: Build to confirm**

```bash
cd frontend && npm run build
```

Expected: build passes.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(invoice-gen): mount /generate-invoice route

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 6.4: Dashboard split CTA

**Files:**
- Modify: `frontend/src/components/Dashboard.tsx`

- [ ] **Step 1: Read the existing Dashboard and find the "+ New" CTA**

Use `Read` on `frontend/src/components/Dashboard.tsx`. Locate the existing primary CTA that opens `InvoiceForm` (likely a button with text like "+ New invoice" that toggles `setFormOpen(true)`).

- [ ] **Step 2: Replace it with a split CTA**

Replace the single button with a two-button group:

```tsx
<div className="flex items-center gap-2">
  <button
    onClick={() => navigate('/generate-invoice')}
    className="px-4 py-2 text-sm font-semibold text-white bg-violet-600 rounded-md hover:bg-violet-700 inline-flex items-center gap-1.5"
  >
    <Plus className="w-4 h-4" />
    Generate invoice
  </button>
  <button
    onClick={() => setFormOpen(true)}
    className="px-4 py-2 text-sm font-medium text-slate-700 border border-slate-300 rounded-md hover:bg-slate-50"
  >
    Chase an existing invoice
  </button>
</div>
```

Make sure `navigate` is already imported from `react-router-dom`; it should be (Dashboard already uses it).

- [ ] **Step 3: Build to confirm**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Dashboard.tsx
git commit -m "feat(invoice-gen): split Dashboard CTA — Generate vs Chase

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

# Phase 7 — Landing page

## Task 7.1: Add feature card + tweak hero subhead

**Files:**
- Modify: `frontend/src/components/LandingPage.tsx`

- [ ] **Step 1: Read the file**

`Read` the file. Find the `features` array (already located at line ~14 — see `LandingPage.tsx:14`).

- [ ] **Step 2: Add a new feature card at the start of the array**

Add this object as the first element of the `features` array (so it appears before "Just drop the invoice PDF"). Also add `FilePlus` to the `lucide-react` import at the top of the file.

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

- [ ] **Step 3: Tweak the hero subhead (one-line change)**

Find the hero subheadline in `LandingPage.tsx` (search for the existing tagline near the top of the component). Adjust it so the copy mentions creating AND chasing — exact wording is the implementer's call as long as it's one short sentence and reads well. Example: change "Chase unpaid invoices on autopilot" → "Create polished invoices, and chase the unpaid ones on autopilot."

- [ ] **Step 4: Build + visually inspect**

```bash
cd frontend && npm run build && npm run dev
```

Open `http://localhost:5173/` in an incognito window. Confirm: new feature card appears first; copy renders cleanly at desktop and 375px mobile (use DevTools device emulation).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/LandingPage.tsx
git commit -m "feat(landing): announce invoice generator + tweak hero subhead

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

# Phase 8 — Verification

## Task 8.1: Full verification pass (the success criteria)

**Goal:** Confirm every objective ship criterion from the spec is met.

- [ ] **Step 1: Lint**

```bash
cd frontend && npm run lint
```

Expected: zero errors. If errors exist, fix them — no `eslint-disable` shortcuts.

- [ ] **Step 2: TypeScript build**

```bash
cd frontend && npm run build
```

Expected: zero errors.

- [ ] **Step 3: Full Vitest suite**

```bash
cd frontend && npm test
```

Expected: all green. Note the total test count and assert it matches the count of tests defined across Phases 1–6 (computeTotals: 10, formatCurrency: 6, formatDate: 4, useInvoiceGeneratorForm: 16, ModernTemplate: 6, ClassicTemplate: 4, MinimalTemplate: 4, TemplatePicker: 6, LineItemsEditor: 8, InvoiceGeneratorPage: 6 → 70 frontend tests).

- [ ] **Step 4: Coverage gates**

```bash
cd frontend && npm run test:coverage
```

Expected: Vitest enforces the thresholds in `vitest.config.ts` (lines ≥90, branches ≥85, functions ≥90, statements ≥90) for the `src/components/invoice-generator/**` and the two hooks. If a threshold fails, add tests until it passes.

- [ ] **Step 5: Backend tests**

```bash
pytest tests/test_sender_profile.py tests/test_generated_invoice.py -v
```

Expected: all green.

- [ ] **Step 6: Manual smoke — happy path**

1. `cd frontend && npm run dev` and `uvicorn api.index:app --reload --port 8000` in parallel.
2. Open `http://localhost:5173/` in an incognito window. Click "Generate invoice" on the dashboard CTA.
3. Fill the form: business name, your name + email, client name + email, invoice number, dates, one line item ($150).
4. Cycle through all 3 templates — preview updates each time, no console errors.
5. Add a Stripe payment URL (`https://buy.stripe.com/test_abc`). Confirm a "Pay invoice" button appears in Modern, hyperlink in Classic, underlined link in Minimal.
6. Click "Download PDF" — file downloads. Open it in macOS Preview AND Chrome. Click the payment link — opens the Stripe URL.
7. Click "Save & Download" — file downloads, you're routed to `/invoice/<id>`, the invoice appears in `/dashboard`.

- [ ] **Step 7: Manual smoke — edge cases**

1. Empty client name → Save buttons disabled.
2. Due date before issue date → red error, Save disabled.
3. Payment URL `javascript:alert(1)` → red error, Save disabled.
4. Empty payment URL → preview omits the payment block, Save works.
5. 25 line items → preview still renders, scrollable.

- [ ] **Step 8: Mobile check**

Open `/` (landing) and `/generate-invoice` at 375px width (Chrome DevTools device emulation, iPhone SE). Confirm:
- No horizontal scroll.
- Form fields stack cleanly.
- PDF preview shifts below the form (it's the second column on desktop).

- [ ] **Step 9: Final commit if anything was tweaked during verification**

```bash
git add -A && git status
# If any unstaged changes, commit them with a descriptive message.
git commit -m "fix(invoice-gen): post-verification fixes

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 10: Open the PR**

```bash
gh pr create --base main --title "feat: invoice PDF generator with three templates" --body "$(cat <<'EOF'
## Summary

- New `/generate-invoice` route with a form, three templates (Modern/Classic/Minimal), live PDF preview, and payment-link support
- Sender profile persisted per-user via `users.sender_profile` JSONB
- Generated invoices land in the existing chase pipeline at escalation_level=0
- Landing page updated with a new feature card

Spec: `docs/superpowers/specs/2026-05-23-invoice-pdf-generator-design.md`
Plan: `docs/superpowers/plans/2026-05-23-invoice-pdf-generator.md`

## Test plan

- [x] `npm run lint` clean
- [x] `npm run build` clean
- [x] `npm test` — 70 tests passing
- [x] `npm run test:coverage` — thresholds met
- [x] `pytest tests/` — backend tests passing
- [x] Manual smoke: download PDF in all 3 templates, payment link clickable, Save & Download creates row + navigates
- [x] Mobile (375px) rendering verified

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-Review Notes

This plan was self-reviewed before handoff. Findings & fixes applied inline:

1. **Coverage gates** are wired into `vitest.config.ts` (Task 0.1, Step 4), so they're enforced automatically — no separate setup needed.
2. **Upload endpoint** (`POST /api/invoices/generated/upload`) was missing from the spec's task list — added inline in Task 6.1 with its own test, because without it the frontend can't get a real storage path before calling `createGeneratedInvoice`.
3. **Cookie name (`guest_id`)** in backend tests is marked as a placeholder — implementer must read `src/db.py:ensure_guest_user` to find the actual cookie name and adjust the tests in Task 5.4.
4. **`db.find_invoice_by_external_id`** is named generically and may need to be added — flagged in Task 5.4 Step 3 with explicit guidance on adapting to the existing column naming (the schema review showed `invoices.id` is the PK and there's no separate `invoice_id_external` column; the implementer needs to either use `id` directly or add the column).
5. **`react-pdf` font registration** is intentionally NOT included — both Modern and Minimal use the built-in Helvetica, Classic uses the built-in Times-Roman. Lora (mentioned in the spec) is replaced with Times-Roman to avoid font loading complexity for v1. This is a justified spec deviation and should be called out in the PR description.
6. **`structuredClone`** is used in `setNested` (Task 2.2) — available in Node 17+, fine for our toolchain.
