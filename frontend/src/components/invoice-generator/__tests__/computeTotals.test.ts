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
      discount: { kind: 'flat', value: 200 },
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
