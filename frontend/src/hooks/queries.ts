import { infiniteQueryOptions, queryOptions, replaceEqualDeep } from '@tanstack/react-query'
import { api } from '../api'
import type { ChatResponse, Invoice, SupabaseCommEntry } from '../types'

// One place for cache keys, so every screen reads and updates the same entries.
export const qk = {
  me: ['me'] as const,
  invoices: ['invoices'] as const,
  invoice: (id: string) => ['invoice', id] as const,
  conversation: (id: string) => ['invoice', id, 'conversation'] as const,
  history: (id: string) => ['invoice', id, 'history'] as const,
  sender: (id: string) => ['invoice', id, 'sender'] as const,
  senderProfile: ['senderProfile'] as const,
  // Debug data: never saved to the device (see shouldPersistQuery).
  traces: (id: string) => ['invoice', id, 'traces'] as const,
}

export const invoicesQuery = () =>
  queryOptions({ queryKey: qk.invoices, queryFn: () => api.getInvoices() })

export const HISTORY_POLL_MS = 30_000

// An older in-flight GET or a temporarily unavailable summary store must not
// replace a successful saved generation already present on this device.
export function mergeHistorySummary(previous: ChatResponse | undefined, incoming: ChatResponse): ChatResponse {
  if (!previous || previous.summary == null) return incoming
  const old = previous.summary_metadata
  const next = incoming.summary_metadata
  if (incoming.summary === undefined) {
    return { ...incoming, summary: previous.summary, summary_metadata: old }
  }
  const unavailable = next?.status === 'unavailable' && incoming.summary === null
  const older = old?.generated_at && (!next?.generated_at || Date.parse(old.generated_at) > Date.parse(next.generated_at))
  if (!unavailable && !older) return incoming
  return {
    ...incoming,
    summary: previous.summary,
    summary_metadata: {
      source_version: old?.source_version ?? null,
      generated_at: old?.generated_at ?? null,
      status: unavailable ? 'unavailable' : next?.is_stale ? 'pending' : old?.status ?? 'pending',
      is_stale: unavailable || Boolean(next?.is_stale || old?.is_stale),
    },
  }
}

export const conversationQuery = (invoiceId: string) =>
  queryOptions({
    queryKey: qk.conversation(invoiceId),
    queryFn: () => api.getConversation(invoiceId),
    structuralSharing: (previous, incoming) => replaceEqualDeep(previous,
      mergeHistorySummary(previous as ChatResponse | undefined, incoming as ChatResponse)),
    staleTime: 10_000,
  })

export const historyQuery = (invoiceId: string) =>
  queryOptions({
    queryKey: qk.history(invoiceId),
    queryFn: () => api.getHistory(invoiceId),
    structuralSharing: (previous, incoming) => replaceEqualDeep(previous,
      mergeHistorySummary(previous as ChatResponse | undefined, incoming as ChatResponse)),
    // Client replies arrive by webhook, so a chat is re-checked often.
    staleTime: 10_000,
  })

export const tracesQuery = (invoiceId: string) =>
  infiniteQueryOptions({
    queryKey: qk.traces(invoiceId),
    queryFn: ({ pageParam }) => api.getTraces(invoiceId, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.next_before ?? undefined,
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
