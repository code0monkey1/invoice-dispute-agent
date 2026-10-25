import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ChatResponse, Invoice } from '../../types'
import { createTestQueryClient, withQueryClient } from '../../test/queryClient'
import { qk, HISTORY_POLL_MS } from '../queries'
import { useInvoices } from '../useInvoices'
import { useChat } from '../useChat'

const api = vi.hoisted(() => ({
  getInvoices: vi.fn(),
  getHistory: vi.fn(),
  settle: vi.fn(),
  chat: vi.fn(),
  resume: vi.fn(),
  escalate: vi.fn(),
  createInvoice: vi.fn(),
  createInvoiceFromUpload: vi.fn(),
}))
vi.mock('../../api', () => ({ api }))

const idb = vi.hoisted(() => ({ get: vi.fn(), set: vi.fn(), del: vi.fn() }))
vi.mock('idb-keyval', () => idb)

const ID = 'u1__inv__SU5WLTE'

function row(overrides: Partial<Invoice> = {}): Invoice {
  return {
    id: ID, invoice_id: 'INV-1', client_name: 'Acme Corp', client_email: 'ap@acme.example',
    invoice_amount: 1200, amount_paid: 0, balance_due: 1200, days_overdue: 14, jurisdiction: 'Oregon',
    escalation_level: 1, communication_history: [], status: 'active', ...overrides,
  }
}

function history(overrides: Partial<ChatResponse> = {}): ChatResponse {
  const r = row()
  return {
    messages: [{ type: 'AIMessage', content: 'Hello' }],
    interrupt: null,
    state: { ...r, communication_history: [] },
    communications: [],
    ...overrides,
  }
}

const never = () => new Promise<never>(() => {})

beforeEach(() => {
  Object.values(api).forEach((fn) => fn.mockReset())
  idb.del.mockReset().mockResolvedValue(undefined)
})

describe('shared invoice cache', () => {
  it('fetches the invoice list once for every screen that shows it', async () => {
    api.getInvoices.mockResolvedValue([row()])
    const client = createTestQueryClient()
    const wrapper = withQueryClient(client)

    const first = renderHook(() => useInvoices(), { wrapper })
    await waitFor(() => expect(first.result.current.invoices).toHaveLength(1))
    first.unmount()
    // Back to the dashboard later: served from cache, no second request.
    const again = renderHook(() => useInvoices(), { wrapper })
    expect(again.result.current.invoices).toHaveLength(1)
    expect(again.result.current.loading).toBe(false)
    expect(api.getInvoices).toHaveBeenCalledTimes(1)
  })

  it('opens a chat with the invoice details from the dashboard before history arrives', () => {
    api.getHistory.mockImplementation(never)
    const client = createTestQueryClient()
    client.setQueryData(qk.invoices, [row()])

    const { result } = renderHook(() => useChat(ID), { wrapper: withQueryClient(client) })

    expect(result.current.agentState?.client_name).toBe('Acme Corp')
    expect(result.current.agentState?.balance_due).toBe(1200)
    expect(result.current.historyLoaded).toBe(false)
  })

  it('shows a chat opened earlier straight from cache', () => {
    api.getHistory.mockImplementation(never)
    const client = createTestQueryClient()
    client.setQueryData(qk.history(ID), history())

    const { result } = renderHook(() => useChat(ID), { wrapper: withQueryClient(client) })

    expect(result.current.messages).toEqual([{ type: 'AIMessage', content: 'Hello' }])
    expect(result.current.historyLoaded).toBe(true)
  })
})

describe('settling updates every screen at once', () => {
  it('marks the invoice settled in the list and the chat immediately', async () => {
    let finish!: (v: unknown) => void
    api.settle.mockImplementation(() => new Promise((r) => { finish = r }))
    api.getInvoices.mockResolvedValue([row({ status: 'paid' })])
    api.getHistory.mockResolvedValue(history({ state: { ...history().state, status: 'paid' } }))
    const client = createTestQueryClient()
    client.setQueryData(qk.invoices, [row()])
    client.setQueryData(qk.history(ID), history())

    const { result } = renderHook(() => useInvoices(), { wrapper: withQueryClient(client) })
    act(() => { void result.current.settleInvoice(ID) })

    await waitFor(() => expect(client.getQueryData<Invoice[]>(qk.invoices)?.[0].status).toBe('paid'))
    expect(client.getQueryData<ChatResponse>(qk.history(ID))?.state.status).toBe('paid')
    expect(client.getQueryData<ChatResponse>(qk.history(ID))?.interrupt).toBeNull()
    await act(async () => { finish({ invoice: row({ status: 'paid' }) }) })
  })

  it('puts everything back if settling fails', async () => {
    api.settle.mockRejectedValue(new Error('network down'))
    api.getInvoices.mockImplementation(never)
    api.getHistory.mockImplementation(never)
    const client = createTestQueryClient()
    client.setQueryData(qk.invoices, [row()])
    client.setQueryData(qk.history(ID), history({ interrupt: { tool: 'draft_polite_reminder', args: {}, description: 'Hi' } }))

    const { result } = renderHook(() => useInvoices(), { wrapper: withQueryClient(client) })
    await act(async () => { await result.current.settleInvoice(ID).catch(() => {}) })

    expect(client.getQueryData<Invoice[]>(qk.invoices)?.[0].status).toBe('active')
    expect(client.getQueryData<ChatResponse>(qk.history(ID))?.interrupt?.tool).toBe('draft_polite_reminder')
  })

  it('settling from the chat uses the same update', async () => {
    api.settle.mockImplementation(never)
    api.getHistory.mockImplementation(never)
    const client = createTestQueryClient()
    client.setQueryData(qk.invoices, [row()])
    client.setQueryData(qk.history(ID), history())

    const { result } = renderHook(() => useChat(ID), { wrapper: withQueryClient(client) })
    act(() => { void result.current.settle() })

    await waitFor(() => expect(result.current.agentState?.status).toBe('paid'))
    expect(client.getQueryData<Invoice[]>(qk.invoices)?.[0].status).toBe('paid')
  })
})

describe('chat mutations write into the cache', () => {
  it('shows the sent message at once, then the agent reply, and refreshes the dashboard', async () => {
    let reply!: (v: ChatResponse) => void
    api.chat.mockImplementation(() => new Promise((r) => { reply = r }))
    api.getHistory.mockImplementation(never)
    api.getInvoices.mockResolvedValue([row()])
    const client = createTestQueryClient()
    client.setQueryData(qk.invoices, [row()])
    client.setQueryData(qk.history(ID), history())

    const { result } = renderHook(() => useChat(ID), { wrapper: withQueryClient(client) })
    act(() => { void result.current.sendMessage('Draft a reminder') })

    await waitFor(() => expect(result.current.messages.at(-1)).toEqual({ type: 'HumanMessage', content: 'Draft a reminder' }))
    expect(result.current.loading).toBe(true)

    const done = history({
      messages: [...history().messages, { type: 'HumanMessage', content: 'Draft a reminder' }, { type: 'AIMessage', content: 'Here it is' }],
      interrupt: { tool: 'draft_polite_reminder', args: {}, description: 'Hi Acme' },
    })
    await act(async () => { reply(done) })

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.messages.at(-1)).toEqual({ type: 'AIMessage', content: 'Here it is' })
    expect(result.current.interrupt?.tool).toBe('draft_polite_reminder')
    expect(client.getQueryData<ChatResponse>(qk.history(ID))?.interrupt?.tool).toBe('draft_polite_reminder')
    // The dashboard list is marked stale, so it refetches when next shown.
    expect(client.getQueryState(qk.invoices)?.isInvalidated).toBe(true)
  })
})

describe('polling for client replies', () => {
  afterEach(() => vi.useRealTimers())

  it('re-checks an open chat every 30 seconds', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    api.getHistory.mockResolvedValue(history())
    const client = createTestQueryClient()

    renderHook(() => useChat(ID), { wrapper: withQueryClient(client) })
    await waitFor(() => expect(api.getHistory).toHaveBeenCalledTimes(1))
    await act(async () => { await vi.advanceTimersByTimeAsync(HISTORY_POLL_MS + 50) })
    await waitFor(() => expect(api.getHistory).toHaveBeenCalledTimes(2))
  })
})

describe('signing out', () => {
  it('clears the in-memory and on-device cache', async () => {
    const { clearCache, CACHE_KEY } = await import('../../queryClient')
    const client = createTestQueryClient()
    client.setQueryData(qk.invoices, [row()])

    await clearCache(client)

    expect(client.getQueryData(qk.invoices)).toBeUndefined()
    expect(idb.del).toHaveBeenCalledWith(CACHE_KEY)
  })
})
