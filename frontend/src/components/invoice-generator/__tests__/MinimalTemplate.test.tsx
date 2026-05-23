import { describe, it, expect } from 'vitest';
import React from 'react';
import { MinimalTemplate } from '../pdf/MinimalTemplate';
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

describe('MinimalTemplate', () => {
  it('matches the snapshot for a full invoice', () => {
    const tree = serialize(<MinimalTemplate data={validInvoice()} />);
    expect(tree).toMatchSnapshot();
  });

  it('NEVER renders a logo, even if one is provided (by design)', () => {
    const data = validInvoice();
    data.sender.logo_url = 'https://example.com/logo.png';
    const tree = JSON.stringify(serialize(<MinimalTemplate data={data} />));
    expect(tree).not.toContain('"type":"IMAGE"');
  });

  it('renders payment as an underlined link at the bottom when provided', () => {
    const data = validInvoice();
    data.payment = { url: 'https://buy.stripe.com/abc' };
    const tree = JSON.stringify(serialize(<MinimalTemplate data={data} />));
    expect(tree).toContain('"type":"LINK"');
    expect(tree).toContain('Pay this invoice');
  });

  it('omits the payment block when payment is undefined', () => {
    const data = validInvoice();
    delete data.payment;
    const tree = JSON.stringify(serialize(<MinimalTemplate data={data} />));
    expect(tree).not.toContain('"type":"LINK"');
  });
});
