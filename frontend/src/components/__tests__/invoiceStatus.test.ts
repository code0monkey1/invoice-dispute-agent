import { describe, expect, it } from 'vitest';
import { invoiceStatus } from '../invoiceStatus';
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
});
