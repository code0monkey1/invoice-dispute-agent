import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import type { ChatResponse, ConversationSummary } from '../types'
import { qk } from './queries'

/** A visit is distinct from history fetches: polling or new messages never post. */
export function useConversationSummary(invoiceId: string, historyReady: boolean) {
  const qc = useQueryClient()
  const visit = useRef<{ id: string; request?: Promise<ConversationSummary> }>({ id: '' })

  useEffect(() => {
    if (visit.current.id !== invoiceId) visit.current = { id: invoiceId }
    if (!invoiceId || !historyReady) return
    const current = visit.current
    // Reuse the promise when StrictMode replays this effect. Its second setup
    // attaches a live callback; the first setup's cleanup suppresses its callback.
    current.request ??= api.refreshSummary(invoiceId)
    let active = true
    void current.request.then(({ summary, ...metadata }) => {
      if (!active || visit.current !== current) return
      qc.setQueryData<ChatResponse>(qk.history(invoiceId), prev => prev ? {
        ...prev, summary, summary_metadata: metadata,
      } : prev)
    }).catch(() => {
      // The saved summary and chat still work. A later opening can retry.
    })
    return () => { active = false }
  }, [invoiceId, historyReady, qc])
}
