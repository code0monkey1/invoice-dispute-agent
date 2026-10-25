import { useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { historyQuery } from './queries'

// Start loading an invoice's chat when the user points at it, so it is
// usually ready by the time they click. Skipped while the cached copy is fresh.
export function usePrefetchHistory() {
  const qc = useQueryClient()
  return useCallback((invoiceId: string) => {
    void qc.prefetchQuery(historyQuery(invoiceId))
  }, [qc])
}
