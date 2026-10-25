import type { Invoice } from '../types'

// What the agent is doing with an invoice, in the user's terms. `you` is the
// only kind that needs the user, and the dashboard colours it orange.
export type InvoiceStatusKind = 'you' | 'agent' | 'client' | 'paid'

export interface InvoiceStatus {
  kind: InvoiceStatusKind
  label: string
}

const DRAFT_LABELS: Record<string, string> = {
  draft_polite_reminder: 'Friendly reminder ready for you',
  draft_formal_demand_letter: 'Formal demand ready for you',
  draft_final_notice: 'Final notice ready for you',
  draft_invoice_delivery_email: 'Invoice email ready for you',
  mark_invoice_paid: 'Payment update to confirm',
  record_partial_payment: 'Payment update to confirm',
  mark_invoice_pending: 'Status change to confirm',
}

export function invoiceStatus(invoice: Invoice): InvoiceStatus {
  if (invoice.status === 'paid') return { kind: 'paid', label: 'Settled' }

  if (invoice.awaiting_approval) {
    const label = (invoice.pending_action && DRAFT_LABELS[invoice.pending_action]) || 'Draft ready for you'
    return { kind: 'you', label }
  }

  const history = invoice.communication_history ?? []
  const last = history[history.length - 1]
  if (last?.direction === 'inbound') return { kind: 'client', label: 'Client replied' }
  if (last?.direction === 'outbound') return { kind: 'agent', label: 'Waiting for the client' }
  return { kind: 'agent', label: 'Agent is preparing the first email' }
}
