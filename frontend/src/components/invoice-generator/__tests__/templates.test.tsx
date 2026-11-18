import { describe, expect, it } from 'vitest';
import React from 'react';
import { Image, Link, Text } from '@react-pdf/renderer';
import { ClassicTemplate } from '../pdf/ClassicTemplate';
import { MinimalTemplate } from '../pdf/MinimalTemplate';
import { ModernTemplate } from '../pdf/ModernTemplate';
import { validInvoice } from './fixtures';

// Read the document content passed to the PDF renderer. Styles and wrapper
// structure can change freely; these tests do not prove PDF layout or pagination.
function documentContent(node: React.ReactNode) {
  const texts: string[] = [];
  const links: { src: string; text: string }[] = [];
  const images: string[] = [];

  function visit(child: React.ReactNode): string {
    if (typeof child === 'string' || typeof child === 'number') return String(child);
    if (Array.isArray(child)) return child.map(visit).join('');
    if (!React.isValidElement<{ children?: React.ReactNode; src?: string }>(child)) return '';
    const props = child.props;
    // The renderer exports host primitives as strings at runtime, while its
    // public types describe them as components.
    const kind: unknown = child.type;
    if (typeof kind === 'function') {
      return visit((kind as (input: typeof props) => React.ReactNode)(props));
    }
    const text = visit(props.children);
    if (kind === Text) texts.push(text);
    if (kind === Link) links.push({ src: props.src!, text });
    if (kind === Image) images.push(props.src!);
    return text;
  }

  visit(node);
  return { texts, links, images };
}

describe.each([
  { name: 'Modern', Component: ModernTemplate, business: 'Acme Studio', paymentLabel: 'PAY', logo: true },
  { name: 'Classic', Component: ClassicTemplate, business: 'ACME STUDIO', paymentLabel: 'https://buy.stripe.com/invoice', logo: true },
  { name: 'Minimal', Component: MinimalTemplate, business: 'Acme Studio', paymentLabel: 'Pay this invoice →', logo: false },
])('$name invoice document', ({ name, Component, business, paymentLabel, logo }) => {
  it('includes invoice facts, calculated amounts and the correct payment destination', () => {
    const data = validInvoice();
    data.sender.logo_url = 'https://example.com/logo.png';
    data.sender.tax_id = 'TAX-123';
    data.client.address = '2 Client Road';
    data.discount = { kind: 'pct', value: 10 };
    data.tax_rate_pct = 10;
    data.payment = { url: 'https://buy.stripe.com/invoice', label: name === 'Modern' ? 'PAY' : undefined };
    data.payment_instructions = 'Bank transfer reference INV-2026-001';
    data.notes = 'Thank you 中文 العربية ñ';

    const { texts, links, images } = documentContent(<Component data={data} />);

    expect(texts).toEqual(expect.arrayContaining([
      business, 'jane@acme.example', '1 Main St\nSpringfield', 'Tax ID: TAX-123',
      'BigCorp', 'ap@bigcorp.example', '2 Client Road', 'INV-2026-001', 'Design work',
      'Subtotal', '$1,500.00', 'Discount', '− $150.00', 'Tax (10%)', '$135.00', 'Total', '$1,485.00',
      data.payment_instructions, data.notes,
    ]));
    expect(texts.some(text => text.includes('May 1, 2026'))).toBe(true);
    expect(texts.some(text => text.includes('May 15, 2026'))).toBe(true);
    expect(links).toEqual([{ src: data.payment.url, text: paymentLabel }]);
    expect(images).toEqual(logo ? [data.sender.logo_url] : []);
  });

  it('omits optional payment, logo, tax and discount when absent', () => {
    const data = validInvoice();
    delete data.sender.address;
    const { texts, links, images } = documentContent(<Component data={data} />);

    expect(links).toEqual([]);
    expect(images).toEqual([]);
    expect(texts).toContain('$1,500.00');
    expect(texts).not.toContain('Discount');
    expect(texts.some(text => text.startsWith('Tax'))).toBe(false);
  });

  it('keeps every line item and the total for a long invoice', () => {
    const data = validInvoice();
    data.line_items = Array.from({ length: 50 }, (_, i) => ({
      description: `Item ${i}`, quantity: 1, unit_price_cents: 100,
    }));
    const { texts } = documentContent(<Component data={data} />);

    expect(texts.filter(text => /^Item \d+$/.test(text))).toEqual(data.line_items.map(item => item.description));
    expect(texts).toContain('$50.00');
  });
});
