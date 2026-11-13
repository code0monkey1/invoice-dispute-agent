import { describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { Query, QueryClient } from '@tanstack/react-query'
import { createTestQueryClient, withQueryClient } from '../../test/queryClient'
import { qk } from '../queries'
import { useChat } from '../useChat'
import { shouldPersistQuery } from '../../queryClient'

const api = vi.hoisted(() => ({
  getHistory: vi.fn(),
  refreshSummary: vi.fn().mockResolvedValue({ summary: null, status: 'empty', is_stale: false }),
  chat: vi.fn(),
  resume: vi.fn(),
  escalate: vi.fn(),
  getTraces: vi.fn(),
}))
vi.mock('../../api', () => ({ api }))
vi.mock('idb-keyval', () => ({ get: vi.fn(), set: vi.fn(), del: vi.fn() }))

const ID = 'u1__inv__SU5WLTE'
const response = { messages: [], interrupt: null, state: { escalation_level: 1, status: 'active' } }

describe('trace cache', () => {
  it('marks the trace stale after every agent action, so an open Trace tab refetches', async () => {
    api.getHistory.mockResolvedValue(response)
    api.chat.mockResolvedValue(response)
    api.resume.mockResolvedValue(response)
    const client = createTestQueryClient()
    client.setQueryData(qk.traces(ID), { pages: [], pageParams: [] })
    const { result } = renderHook(() => useChat(ID), { wrapper: withQueryClient(client) })

    await act(() => result.current.sendMessage('How overdue is this invoice?'))
    await waitFor(() => expect(client.getQueryState(qk.traces(ID))?.isInvalidated).toBe(true))

    client.setQueryData(qk.traces(ID), { pages: [], pageParams: [] })
    await act(() => result.current.reject('Softer please'))
    await waitFor(() => expect(client.getQueryState(qk.traces(ID))?.isInvalidated).toBe(true))
  })

  it('never saves traces to the device, but still saves invoices and chats', () => {
    const client = new QueryClient()
    client.setQueryData(qk.traces(ID), { pages: [], pageParams: [] })
    client.setQueryData(qk.history(ID), response)
    const byKey = (key: readonly unknown[]) =>
      client.getQueryCache().find({ queryKey: key, exact: true }) as Query
    expect(shouldPersistQuery(byKey(qk.traces(ID)))).toBe(false)
    expect(shouldPersistQuery(byKey(qk.history(ID)))).toBe(true)
  })
})
