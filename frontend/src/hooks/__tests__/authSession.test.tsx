import { beforeEach, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { useAuthSession } from '../useAuthSession'
import { withQueryClient } from '../../test/queryClient'

const api = vi.hoisted(() => ({ getMe: vi.fn() }))
vi.mock('../../api', () => ({ api }))
vi.mock('../../queryClient', () => ({ clearCache: vi.fn().mockResolvedValue(undefined) }))

beforeEach(() => { localStorage.clear(); vi.clearAllMocks() })

it('renders the saved guest immediately without an authenticated profile request', () => {
  localStorage.setItem('invoicechaser_user', JSON.stringify({ id: 'guest', name: 'Dana', email: '', picture: '' }))
  const { result } = renderHook(() => useAuthSession(), { wrapper: withQueryClient() })
  expect(result.current.user?.name).toBe('Dana')
  expect(result.current.isGuest).toBe(true)
  expect(api.getMe).not.toHaveBeenCalled()
})

it('refreshes and persists the signed-in profile', async () => {
  localStorage.setItem('invoicechaser_token', 'test-token')
  const user = { id: 'owner', name: 'Dana', email: 'dana@example.com', picture: '', gmail_connected: true }
  api.getMe.mockResolvedValue({ user })
  const { result } = renderHook(() => useAuthSession(), { wrapper: withQueryClient() })
  await waitFor(() => expect(result.current.user).toEqual(user))
  expect(JSON.parse(localStorage.getItem('invoicechaser_user')!)).toEqual(user)
  expect(result.current.isGuest).toBe(false)
})

it('stores a new guest and updates the session', () => {
  const { result } = renderHook(() => useAuthSession(), { wrapper: withQueryClient() })
  act(() => result.current.enterAsGuest('Lee'))
  expect(result.current.user?.name).toBe('Lee')
  expect(result.current.isGuest).toBe(true)
  expect(JSON.parse(localStorage.getItem('invoicechaser_user')!).id).toBe('guest')
})
