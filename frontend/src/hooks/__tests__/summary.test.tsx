import { StrictMode, type ReactNode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ChatResponse } from '../../types'
import { createTestQueryClient, withQueryClient } from '../../test/queryClient'
import { useChat } from '../useChat'
import { historyQuery, HISTORY_POLL_MS, qk } from '../queries'

const api = vi.hoisted(() => ({ getHistory: vi.fn(), refreshSummary: vi.fn(), chat: vi.fn(), getInvoices: vi.fn() }))
vi.mock('../../api', () => ({ api }))

const history = {
  messages: [{ type: 'HumanMessage', content: 'Promise to pay tomorrow' }], interrupt: null,
  state: { escalation_level: 1, client_name: 'Acme', client_email: 'ap@example.com', invoice_id: 'A', invoice_amount: 100, amount_paid: 0, balance_due: 100, days_overdue: 3, jurisdiction: 'CA', status: 'active', communication_history: [] },
} satisfies ChatResponse
const summary = { invoice_id: 'A', summary: 'Payment was promised tomorrow.', source_version: 'source-1', generated_at: '2026-11-14T10:00:00Z', status: 'current', is_stale: false }

beforeEach(() => {
  Object.values(api).forEach(f => f.mockReset())
  api.getHistory.mockResolvedValue(history)
  api.refreshSummary.mockResolvedValue(summary)
  api.chat.mockResolvedValue({ ...history, messages: [...history.messages, { type: 'AIMessage', content: 'Noted' }] })
  api.getInvoices.mockResolvedValue([])
})
afterEach(() => vi.useRealTimers())

describe('invoice opening summaries', () => {
  it('requests once after real history loads and exposes saved text without a chat message', async () => {
    let loaded!: (h: ChatResponse) => void
    api.getHistory.mockImplementation(() => new Promise(r => { loaded = r }))
    const client = createTestQueryClient()
    const { result, rerender } = renderHook(() => useChat('A'), { wrapper: withQueryClient(client) })
    expect(api.refreshSummary).not.toHaveBeenCalled()
    await act(async () => loaded(history))
    await waitFor(() => expect(result.current.summary).toBe(summary.summary))
    expect(result.current.messages).toEqual(history.messages)
    rerender()
    expect(api.refreshSummary).toHaveBeenCalledTimes(1)
    expect(api.refreshSummary).toHaveBeenCalledWith('A')
    expect(client.getQueryData<ChatResponse>(qk.history('A'))?.summary).toBe(summary.summary)
  })

  it('does not double-post in StrictMode', async () => {
    const client = createTestQueryClient()
    client.setQueryData(qk.history('A'), history)
    function Wrapper({ children }: { children: ReactNode }) {
      return <StrictMode><QueryClientProvider client={client}>{children}</QueryClientProvider></StrictMode>
    }
    const { result } = renderHook(() => useChat('A'), { wrapper: Wrapper })
    await waitFor(() => expect(result.current.summary).toBe(summary.summary))
    expect(api.refreshSummary).toHaveBeenCalledTimes(1)
  })

  it('does not refresh on prefetch, polling, manual history refresh or chat', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const client = createTestQueryClient()
    await client.prefetchQuery(historyQuery('A'))
    expect(api.refreshSummary).not.toHaveBeenCalled()
    const { result } = renderHook(() => useChat('A'), { wrapper: withQueryClient(client) })
    await waitFor(() => expect(result.current.summary).toBe(summary.summary))
    api.getHistory.mockResolvedValue({ ...history, summary: summary.summary, summary_metadata: { ...summary, is_stale: true, status: 'pending' } })
    await act(async () => { await vi.advanceTimersByTimeAsync(HISTORY_POLL_MS + 50) })
    await act(async () => { await result.current.refreshHistory() })
    await act(async () => { await result.current.sendMessage('Another invoice update') })
    expect(api.refreshSummary).toHaveBeenCalledTimes(1)
    expect(result.current.summary).toBe(summary.summary)
    expect(result.current.summaryMetadata?.is_stale).toBe(true)
  })

  it('requests again on a new opening and when switching invoices', async () => {
    const client = createTestQueryClient()
    const wrapper = withQueryClient(client)
    const first = renderHook(({ id }) => useChat(id), { initialProps: { id: 'A' }, wrapper })
    await waitFor(() => expect(api.refreshSummary).toHaveBeenCalledTimes(1))
    first.rerender({ id: 'B' })
    await waitFor(() => expect(api.refreshSummary).toHaveBeenLastCalledWith('B'))
    first.rerender({ id: 'A' })
    await waitFor(() => expect(api.refreshSummary).toHaveBeenCalledTimes(3))
    first.unmount()
    renderHook(() => useChat('A'), { wrapper })
    await waitFor(() => expect(api.refreshSummary).toHaveBeenCalledTimes(4))
  })

  it('keeps saved summary and chat usable when opening refresh fails', async () => {
    const client = createTestQueryClient()
    client.setQueryData(qk.history('A'), { ...history, summary: 'Earlier saved summary' })
    api.refreshSummary.mockRejectedValue(new Error('unavailable'))
    const { result } = renderHook(() => useChat('A'), { wrapper: withQueryClient(client) })
    await waitFor(() => expect(api.refreshSummary).toHaveBeenCalledTimes(1))
    await act(async () => { await result.current.sendMessage('invoice update') })
    expect(result.current.summary).toBe('Earlier saved summary')
    expect(result.current.error).toBeNull()
    expect(api.refreshSummary).toHaveBeenCalledTimes(1)
  })

  it('ignores a previous invoices late response after navigation', async () => {
    let old!: (v: typeof summary) => void
    api.refreshSummary.mockImplementation((id: string) => id === 'A' ? new Promise(r => { old = r }) : Promise.resolve({ ...summary, invoice_id: 'B', summary: 'B summary' }))
    const { result, rerender } = renderHook(({ id }) => useChat(id), { initialProps: { id: 'A' }, wrapper: withQueryClient() })
    await waitFor(() => expect(api.refreshSummary).toHaveBeenCalledWith('A'))
    rerender({ id: 'B' })
    await waitFor(() => expect(result.current.summary).toBe('B summary'))
    await act(async () => old(summary))
    expect(result.current.summary).toBe('B summary')
  })
})
