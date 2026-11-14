import { useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { conversationQuery } from './queries'

// Prefetch only the saved summary/current state; full history requires consent.
export function usePrefetchConversation() {
  const qc = useQueryClient()
  return useCallback((invoiceId: string) => {
    void qc.prefetchQuery(conversationQuery(invoiceId))
  }, [qc])
}
