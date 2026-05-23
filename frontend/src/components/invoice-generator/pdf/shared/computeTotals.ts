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
