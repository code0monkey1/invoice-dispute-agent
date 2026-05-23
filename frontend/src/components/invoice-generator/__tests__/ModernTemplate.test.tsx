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
    // If it's a function component, call it to get the rendered output.
    if (typeof el.type === 'function') {
      const rendered = (el.type as (props: Record<string, unknown>) => React.ReactNode)(
        el.props as Record<string, unknown>
      );
      return serialize(rendered);
    }
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
    expect(tree).toContain('"type":"LINK"');
    expect(tree).toContain('https://buy.stripe.com/abc');
  });

  it('omits the payment block entirely when payment is undefined', () => {
    const data = validInvoice();
    delete data.payment;
    const tree = JSON.stringify(serialize(<ModernTemplate data={data} />));
    expect(tree).not.toContain('"type":"LINK"');
  });

  it('omits the logo block when sender.logo_url is undefined', () => {
    const data = validInvoice();
    const tree = JSON.stringify(serialize(<ModernTemplate data={data} />));
    expect(tree).not.toContain('"type":"IMAGE"');
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
