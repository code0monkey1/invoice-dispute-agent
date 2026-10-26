import { describe, expect, it } from 'vitest';
import { invoiceStatus } from '../invoiceStatus';
import { formatPromiseDate } from '../format';
import type { Invoice } from '../../types';

function invoice(overrides: Partial<Invoice> = {}): Invoice {
  return {
    id: 'u__inv__SU5WLTE',
    invoice_id: 'INV-1',
    client_name: 'Client Co.',
    client_email: 'sam@clientco.com',
    invoice_amount: 5000,
    amount_paid: 0,
    balance_due: 5000,
    days_overdue: 14,
    jurisdiction: 'Oregon',
    escalation_level: 1,
    communication_history: [],
    status: 'active',
    ...overrides,
  };
}

describe('invoiceStatus', () => {
  it('puts a waiting draft first, named by what it is', () => {
    const s = invoiceStatus(invoice({ awaiting_approval: true, pending_action: 'draft_formal_demand_letter' }));
    expect(s.kind).toBe('you');
    expect(s.label).toBe('Formal demand ready for you');
  });

  it('falls back to a generic label for unknown draft tools', () => {
    const s = invoiceStatus(invoice({ awaiting_approval: true, pending_action: 'something_new' }));
    expect(s).toEqual({ kind: 'you', label: 'Draft ready for you' });
  });

  it('reports paid invoices as paid even if a draft was pending', () => {
    const s = invoiceStatus(invoice({ status: 'paid', awaiting_approval: true }));
    expect(s.kind).toBe('paid');
  });

  it('says the agent is waiting on the client after an email went out', () => {
    const history = [{ direction: 'outbound', type: 'email', content: '', timestamp: '2026-04-16' }];
    expect(invoiceStatus(invoice({ communication_history: history })).label).toBe('Waiting for the client');
  });

  it('flags a fresh client reply', () => {
    const history = [
      { direction: 'outbound', type: 'email', content: '', timestamp: '2026-04-16' },
      { direction: 'inbound', type: 'email', content: '', timestamp: '2026-04-18' },
    ];
    expect(invoiceStatus(invoice({ communication_history: history })).label).toBe('Client replied');
  });

  it('describes a new invoice with no emails yet', () => {
    expect(invoiceStatus(invoice()).label).toBe('Agent is preparing the first email');
  });

  describe('promise to pay', () => {
    const today = new Date(2026, 9, 26); // 26 Oct 2026, local time

    it('shows the promised date', () => {
      const s = invoiceStatus(invoice({ status: 'pending', follow_up_date: '2026-11-15' }), today);
      expect(s).toEqual({ kind: 'promised', label: 'Promised to pay by Nov 15, 2026' });
    });

    it('still counts the promise on its due day', () => {
      const s = invoiceStatus(invoice({ status: 'pending', follow_up_date: '2026-10-26' }), today);
      expect(s.label).toBe('Promised to pay by Oct 26, 2026');
    });

    it('calls out a promise whose date has passed', () => {
      const s = invoiceStatus(invoice({ status: 'pending', follow_up_date: '2026-10-20' }), today);
      expect(s).toEqual({ kind: 'promised', label: 'Promise missed (Oct 20, 2026)' });
    });

    it('works without a date', () => {
      expect(invoiceStatus(invoice({ status: 'pending' }), today).label).toBe('Client promised to pay');
    });

    it('lets a waiting draft and a fresh reply take priority', () => {
      const promised = { status: 'pending', follow_up_date: '2026-11-15' };
      expect(invoiceStatus(invoice({ ...promised, awaiting_approval: true }), today).kind).toBe('you');
      const history = [{ direction: 'inbound', type: 'email', content: '', timestamp: '2026-10-25' }];
      expect(invoiceStatus(invoice({ ...promised, communication_history: history }), today).kind).toBe('client');
    });

    it('is overridden by settling', () => {
      const s = invoiceStatus(invoice({ status: 'paid', follow_up_date: '2026-11-15' }), today);
      expect(s.kind).toBe('paid');
    });
  });
});

describe('formatPromiseDate', () => {
  it('formats a YYYY-MM-DD date without shifting it across time zones', () => {
    expect(formatPromiseDate('2026-01-01')).toBe('Jan 1, 2026');
  });

  it('returns the raw value when it is not a date', () => {
    expect(formatPromiseDate('soon')).toBe('soon');
  });
});
