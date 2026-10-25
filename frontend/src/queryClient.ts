import { QueryClient } from '@tanstack/react-query'
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister'
import { del, get, set } from 'idb-keyval'

const DAY = 1000 * 60 * 60 * 24
export const CACHE_KEY = 'invoicechaser_cache'
export const CACHE_MAX_AGE = DAY

// Shown from cache straight away, refetched in the background once stale.
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        // Must be at least the persisted maxAge, or restored data is dropped early.
        gcTime: DAY,
        retry: 1,
        refetchOnWindowFocus: true,
      },
    },
  })
}

export const queryClient = createQueryClient()

// IndexedDB rather than localStorage: no 5 MB cap, and writes don't block the page.
export const persister = createAsyncStoragePersister({
  key: CACHE_KEY,
  storage: {
    getItem: async (key: string) => (await get<string>(key)) ?? null,
    setItem: (key: string, value: string) => set(key, value),
    removeItem: (key: string) => del(key),
  },
})

// A cache saved for one account is discarded when another account (or a
// guest) opens the app in the same browser.
export function cacheBuster(): string {
  try {
    const saved = localStorage.getItem('invoicechaser_user')
    return saved ? `user:${JSON.parse(saved).id}` : 'anonymous'
  } catch {
    return 'anonymous'
  }
}

// Called on sign-out, leaving the demo and expired sessions, so invoice data
// doesn't stay in the browser.
export async function clearCache(client: QueryClient = queryClient) {
  client.clear()
  try {
    await del(CACHE_KEY)
  } catch {
    // IndexedDB unavailable (private mode): nothing was persisted.
  }
}
