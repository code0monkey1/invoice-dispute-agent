import { useState, useCallback } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import type { Message, Interrupt, AgentState, ChatResponse, Invoice } from '../types'
import { conversationQuery, historyPlaceholder, historyQuery, HISTORY_POLL_MS, qk } from './queries'
import { useSettleInvoice } from './useSettleInvoice'
import { useConversationSummary } from './useConversationSummary'

function mergeMessages(current: Message[], incoming?: Message[]) {
  if (!incoming) return current
  return incoming.length >= current.length ? incoming : current
}

interface ChatAction {
  invoiceId: string
  visit: number
  call: () => Promise<ChatResponse>
  // Shown in the thread while the request runs.
  optimistic?: Message
}

export function useChat(invoiceId: string) {
  const qc = useQueryClient()
  const [pending, setPending] = useState<{ invoiceId: string; visit: number; message: Message } | null>(null)
  const [lastEmailSent, setLastEmailSent] = useState<{ sent: boolean; id?: string; status?: string; note?: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [visitMessages, setVisitMessages] = useState<{ id: string; visit: number; messages: Message[] }>({ id: invoiceId, visit: 0, messages: [] })
  const [historyVisit, setHistoryVisit] = useState<{ id: string; visible: boolean }>({ id: invoiceId, visible: false })
  // A different invoice starts a new visit; returning later must not opt in
  // to prior history or show a previous visit's current-session messages.
  if (visitMessages.id !== invoiceId) {
    setVisitMessages({ id: invoiceId, visit: visitMessages.visit + 1, messages: [] })
    setHistoryVisit({ id: invoiceId, visible: false })
  }
  const visit = visitMessages.visit
  const fullHistoryVisible = historyVisit.id === invoiceId && historyVisit.visible

  const threadId = `invoice-${invoiceId}`

  // Write an agent response into the cached history, so a revisit or a reload
  // shows it without asking the server again.
  const writeResponse = useCallback((res: ChatResponse, targetId: string, targetVisit: number) => {
    setVisitMessages(prev => prev.id === targetId && prev.visit === targetVisit ? { id: targetId, visit: targetVisit, messages: [...prev.messages, ...res.messages] } : prev)
    qc.setQueryData<ChatResponse>(qk.history(targetId), prev => prev ? {
      ...prev, ...res, messages: [...prev.messages, ...res.messages],
    } : prev)
    const rest: ChatResponse = { messages: [], interrupt: res.interrupt, state: res.state, has_history: true }
    if (res.communications) rest.communications = res.communications
    qc.setQueryData<ChatResponse>(qk.conversation(targetId), (prev) => ({
      ...prev,
      ...rest,
      messages: mergeMessages(prev?.messages ?? [], rest.messages),
      communications: rest.communications ?? prev?.communications ?? [],
    }))
  }, [qc])

  const action = useMutation({
    mutationKey: qk.invoice(invoiceId),
    mutationFn: ({ call }: ChatAction) => call(),
    onMutate: async ({ optimistic, invoiceId: targetId, visit: targetVisit }: ChatAction) => {
      // A poll landing mid-request must not overwrite the reply.
      await Promise.all([qc.cancelQueries({ queryKey: qk.conversation(targetId) }), qc.cancelQueries({ queryKey: qk.history(targetId) })])
      if (optimistic) setPending({ invoiceId: targetId, visit: targetVisit, message: optimistic })
    },
    onSuccess: (res, variables) => writeResponse(res, variables.invoiceId, variables.visit),
    onSettled: (_res, _error, { invoiceId: targetId, visit: targetVisit }) => {
      setPending(prev => prev?.invoiceId === targetId && prev.visit === targetVisit ? null : prev)
      void qc.invalidateQueries({ queryKey: qk.invoices })
      // Every chat, escalation or decision is a new agent run.
      void qc.invalidateQueries({ queryKey: qk.traces(targetId) })
      void qc.invalidateQueries({ queryKey: qk.history(targetId) })
    },
  })
  const settleMutation = useSettleInvoice()
  const busy = action.isPending || settleMutation.isPending

  const history = useQuery({
    ...conversationQuery(invoiceId),
    enabled: Boolean(invoiceId),
    // Until history arrives, show what the dashboard already knows.
    placeholderData: () => {
      const row = qc.getQueryData<Invoice[]>(qk.invoices)?.find((inv) => inv.id === invoiceId)
      return row ? historyPlaceholder(row) : undefined
    },
    // Picks up client replies that arrive by webhook; pauses in hidden tabs.
    refetchInterval: busy ? false : HISTORY_POLL_MS,
    refetchIntervalInBackground: false,
  })

  const fullHistory = useQuery({
    ...historyQuery(invoiceId),
    enabled: Boolean(invoiceId && fullHistoryVisible),
    refetchInterval: fullHistoryVisible && !busy ? HISTORY_POLL_MS : false,
    refetchIntervalInBackground: false,
  })

  useConversationSummary(invoiceId, !history.isPlaceholderData && history.data !== undefined)

  const data = history.data
  const serverMessages = fullHistoryVisible && fullHistory.data ? fullHistory.data.messages
    : visitMessages.id === invoiceId ? visitMessages.messages : []
  const messages = pending?.invoiceId === invoiceId && pending.visit === visit ? [...serverMessages, pending.message] : serverMessages
  const historyLoaded = !history.isPlaceholderData && data !== undefined

  const showError = useCallback((err: unknown, fallback: string) => {
    setError(err instanceof Error ? err.message : fallback)
    setTimeout(() => setError(null), 10000)
  }, [])

  const { mutateAsync: run } = action
  const { mutateAsync: settleAsync } = settleMutation
  const { refetch } = history

  const sendMessage = useCallback(async (text: string) => {
    try {
      await run({ invoiceId, visit, call: () => api.chat(threadId, text), optimistic: { type: 'HumanMessage', content: text } })
    } catch (err) {
      console.error('Chat error:', err)
      showError(err, 'Your message could not be sent.')
    }
  }, [run, invoiceId, visit, threadId, showError])

  // Escalation changes the level on the server directly, then the agent
  // drafts the next email, which comes back as a normal approval.
  const escalate = useCallback(async () => {
    setError(null)
    try {
      await run({ invoiceId, visit, call: () => api.escalate(invoiceId) })
    } catch (err) {
      console.error('Escalate error:', err)
      showError(err, 'Could not escalate this invoice.')
    }
  }, [run, invoiceId, visit, showError])

  const settle = useCallback(async () => {
    setError(null)
    try {
      await settleAsync(invoiceId)
    } catch (err) {
      console.error('Settle error:', err)
      showError(err, 'Could not mark this invoice as settled.')
    }
  }, [settleAsync, invoiceId, showError])

  const approve = useCallback(async (approvedDraft?: string) => {
    setLastEmailSent(null)
    setError(null)
    try {
      const res = await run({ invoiceId, visit, call: () => api.resume(invoiceId, 'approve', approvedDraft) })
      if (res.email_sent !== undefined) {
        setLastEmailSent({ sent: res.email_sent, id: res.email_id, status: res.email_status, note: res.email_note })
        // A confirmation can go quickly; an explanation of why nothing was sent stays longer.
        setTimeout(() => setLastEmailSent(null), res.email_sent ? 8000 : 20000)
      }
      // Sending adds to the communication log.
      void qc.invalidateQueries({ queryKey: qk.conversation(invoiceId) })
      void qc.invalidateQueries({ queryKey: qk.history(invoiceId) })
    } catch (err) {
      console.error('Approve error:', err)
      showError(err, 'Something went wrong')
    }
  }, [run, invoiceId, visit, qc, showError])

  const reject = useCallback(async (message: string) => {
    setError(null)
    try {
      await run({ invoiceId, visit, call: () => api.resume(invoiceId, 'reject', message || 'Please revise.') })
    } catch (err) {
      console.error('Reject error:', err)
      showError(err, 'Something went wrong')
    }
  }, [run, invoiceId, visit, showError])

  const initMessages = useCallback((msgs: Message[], inter: Interrupt | null, state: AgentState) => {
    setVisitMessages(prev => prev.id === invoiceId && prev.visit === visit ? { id: invoiceId, visit, messages: msgs } : prev)
    qc.setQueryData<ChatResponse>(qk.conversation(invoiceId), (prev) => ({ ...prev, messages: [], interrupt: inter, state }))
    void qc.invalidateQueries({ queryKey: qk.invoices })
  }, [qc, invoiceId, visit])

  const refreshHistory = useCallback(async () => {
    await refetch()
  }, [refetch])

  return {
    messages,
    summary: data?.summary ?? null,
    summaryMetadata: data?.summary_metadata ?? null,
    interrupt: data?.interrupt ?? null,
    agentState: data?.state ?? null,
    communications: fullHistoryVisible ? fullHistory.data?.communications ?? [] : [],
    loading: busy,
    historyLoaded,
    hasHistory: data?.has_history ?? false,
    hasOutbound: data?.has_outbound ?? false,
    fullHistoryVisible,
    fullHistoryLoading: fullHistoryVisible && fullHistory.isPending,
    fullHistoryError: fullHistoryVisible && fullHistory.isError,
    viewHistory: () => setHistoryVisit({ id: invoiceId, visible: true }),
    hideHistory: () => setHistoryVisit({ id: invoiceId, visible: false }),
    retryHistory: () => fullHistory.refetch(),
    lastEmailSent,
    error,
    sendMessage,
    escalate,
    settle,
    approve,
    reject,
    initMessages,
    refreshHistory,
  }
}
