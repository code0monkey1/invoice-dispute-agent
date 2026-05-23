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
