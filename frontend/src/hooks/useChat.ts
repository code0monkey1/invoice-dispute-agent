import { useState, useCallback } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import type { Message, Interrupt, AgentState, ChatResponse, Invoice } from '../types'
import { historyPlaceholder, historyQuery, HISTORY_POLL_MS, qk } from './queries'
import { useSettleInvoice } from './useSettleInvoice'

function mergeMessages(current: Message[], incoming?: Message[]) {
  if (!incoming) return current
  return incoming.length >= current.length ? incoming : current
}

interface ChatAction {
  call: () => Promise<ChatResponse>
  // Shown in the thread while the request runs.
  optimistic?: Message
}

export function useChat(invoiceId: string) {
  const qc = useQueryClient()
  const [pending, setPending] = useState<Message | null>(null)
  const [lastEmailSent, setLastEmailSent] = useState<{ sent: boolean; id?: string; status?: string; note?: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const threadId = `invoice-${invoiceId}`

  // Write an agent response into the cached history, so a revisit or a reload
  // shows it without asking the server again.
  const writeResponse = useCallback((res: ChatResponse) => {
    const rest: ChatResponse = { messages: res.messages, interrupt: res.interrupt, state: res.state }
    if (res.communications) rest.communications = res.communications
    qc.setQueryData<ChatResponse>(qk.history(invoiceId), (prev) => ({
      ...prev,
      ...rest,
      messages: mergeMessages(prev?.messages ?? [], rest.messages),
      communications: rest.communications ?? prev?.communications ?? [],
    }))
  }, [qc, invoiceId])

  const action = useMutation({
    mutationKey: qk.invoice(invoiceId),
    mutationFn: ({ call }: ChatAction) => call(),
    onMutate: async ({ optimistic }: ChatAction) => {
      // A poll landing mid-request must not overwrite the reply.
      await qc.cancelQueries({ queryKey: qk.history(invoiceId) })
      if (optimistic) setPending(optimistic)
    },
    onSuccess: writeResponse,
    onSettled: () => {
      setPending(null)
      void qc.invalidateQueries({ queryKey: qk.invoices })
    },
  })
  const settleMutation = useSettleInvoice()
  const busy = action.isPending || settleMutation.isPending

  const history = useQuery({
    ...historyQuery(invoiceId),
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

  const data = history.data
  const serverMessages = data?.messages ?? []
  const messages = pending ? [...serverMessages, pending] : serverMessages
  const historyLoaded = !history.isPlaceholderData && (data !== undefined || history.isError)

  const showError = useCallback((err: unknown, fallback: string) => {
    setError(err instanceof Error ? err.message : fallback)
    setTimeout(() => setError(null), 10000)
  }, [])

  const { mutateAsync: run } = action
  const { mutateAsync: settleAsync } = settleMutation
  const { refetch } = history

  const sendMessage = useCallback(async (text: string) => {
    try {
      await run({ call: () => api.chat(threadId, text), optimistic: { type: 'HumanMessage', content: text } })
    } catch (err) {
      console.error('Chat error:', err)
      showError(err, 'Your message could not be sent.')
    }
  }, [run, threadId, showError])

  // Escalation changes the level on the server directly, then the agent
  // drafts the next email, which comes back as a normal approval.
  const escalate = useCallback(async () => {
    setError(null)
    try {
      await run({ call: () => api.escalate(invoiceId) })
    } catch (err) {
      console.error('Escalate error:', err)
      showError(err, 'Could not escalate this invoice.')
    }
  }, [run, invoiceId, showError])

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
      const res = await run({ call: () => api.resume(invoiceId, 'approve', approvedDraft) })
      if (res.email_sent !== undefined) {
        setLastEmailSent({ sent: res.email_sent, id: res.email_id, status: res.email_status, note: res.email_note })
        // A confirmation can go quickly; an explanation of why nothing was sent stays longer.
        setTimeout(() => setLastEmailSent(null), res.email_sent ? 8000 : 20000)
      }
      // Sending adds to the communication log.
      void qc.invalidateQueries({ queryKey: qk.history(invoiceId) })
    } catch (err) {
      console.error('Approve error:', err)
      showError(err, 'Something went wrong')
    }
  }, [run, invoiceId, qc, showError])

  const reject = useCallback(async (message: string) => {
    setError(null)
    try {
      await run({ call: () => api.resume(invoiceId, 'reject', message || 'Please revise.') })
    } catch (err) {
      console.error('Reject error:', err)
      showError(err, 'Something went wrong')
    }
  }, [run, invoiceId, showError])

  const initMessages = useCallback((msgs: Message[], inter: Interrupt | null, state: AgentState) => {
    qc.setQueryData<ChatResponse>(qk.history(invoiceId), (prev) => ({ ...prev, messages: msgs, interrupt: inter, state }))
    void qc.invalidateQueries({ queryKey: qk.invoices })
  }, [qc, invoiceId])

  const refreshHistory = useCallback(async () => {
    await refetch()
  }, [refetch])

  return {
    messages,
    interrupt: data?.interrupt ?? null,
    agentState: data?.state ?? null,
    communications: data?.communications ?? [],
    loading: busy,
    historyLoaded,
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
