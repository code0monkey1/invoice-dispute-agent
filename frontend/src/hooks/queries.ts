import { queryOptions } from '@tanstack/react-query'
import { api } from '../api'
import type { ChatResponse, Invoice, SupabaseCommEntry } from '../types'

// One place for cache keys, so every screen reads and updates the same entries.
export const qk = {
  me: ['me'] as const,
  invoices: ['invoices'] as const,
  invoice: (id: string) => ['invoice', id] as const,
  history: (id: string) => ['invoice', id, 'history'] as const,
  sender: (id: string) => ['invoice', id, 'sender'] as const,
  senderProfile: ['senderProfile'] as const,
}

export const invoicesQuery = () =>
  queryOptions({ queryKey: qk.invoices, queryFn: () => api.getInvoices() })

export const HISTORY_POLL_MS = 30_000

export const historyQuery = (invoiceId: string) =>
  queryOptions({
    queryKey: qk.history(invoiceId),
    queryFn: () => api.getHistory(invoiceId),
    // Client replies arrive by webhook, so a chat is re-checked often.
    staleTime: 10_000,
  })

export const senderQuery = (invoiceId: string) =>
  queryOptions({
    queryKey: qk.sender(invoiceId),
    queryFn: () => api.getSender(invoiceId),
    staleTime: 5 * 60_000,
  })

export const senderProfileQuery = () =>
  queryOptions({
    queryKey: qk.senderProfile,
    queryFn: async () => (await api.getSenderProfile()) ?? {},
    staleTime: 5 * 60_000,
  })

// What the dashboard row already knows about an invoice, shaped like a chat
// response, so the invoice page can render its details before /history returns.
export function historyPlaceholder(invoice: Invoice): ChatResponse {
  const communications = (invoice.communication_history ?? []) as unknown as SupabaseCommEntry[]
  return {
    messages: [],
    interrupt: null,
    state: {
      escalation_level: invoice.escalation_level,
      client_name: invoice.client_name,
      client_email: invoice.client_email,
      invoice_amount: invoice.invoice_amount,
      amount_paid: invoice.amount_paid,
      balance_due: invoice.balance_due ?? invoice.invoice_amount - invoice.amount_paid,
      invoice_id: invoice.invoice_id,
      days_overdue: invoice.days_overdue,
      jurisdiction: invoice.jurisdiction,
      status: invoice.status,
      communication_history: invoice.communication_history ?? [],
    },
    communications,
  }
}
