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
    { description: 'Design work', quantity: 10, unit_price_cents: 15000 },
  ],
  template: 'modern',
});
