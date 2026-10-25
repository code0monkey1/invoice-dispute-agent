import { useState, useCallback, useEffect } from 'react'
import { api } from '../api'
import type { Message, Interrupt, AgentState, SupabaseCommEntry } from '../types'

function mergeMessages(current: Message[], incoming?: Message[]) {
  if (!incoming) return current
  return incoming.length >= current.length ? incoming : current
}

function mergeHistoryMessages(current: Message[], incoming?: Message[]) {
  if (!incoming) return current
  if (current.length === 0 || incoming.length > current.length) return incoming
  return current
}

export function useChat(invoiceId: string) {
  const [messages, setMessages] = useState<Message[]>([])
  const [interrupt, setInterrupt] = useState<Interrupt | null>(null)
  const [agentState, setAgentState] = useState<AgentState | null>(null)
  const [communications, setCommunications] = useState<SupabaseCommEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const [lastEmailSent, setLastEmailSent] = useState<{ sent: boolean; id?: string; status?: string; note?: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const threadId = `invoice-${invoiceId}`

  // Load existing conversation history when the component mounts
  useEffect(() => {
    if (!invoiceId || historyLoaded) return
    let cancelled = false

    async function loadHistory() {
      try {
        const res = await api.getHistory(invoiceId)
        if (cancelled) return
        if (res.messages) setMessages(res.messages)
        setInterrupt(res.interrupt)
        if (res.state) setAgentState(res.state)
        if (res.communications) setCommunications(res.communications)
      } catch (err) {
        console.error('Failed to load history:', err)
      } finally {
        if (!cancelled) setHistoryLoaded(true)
      }
    }

    loadHistory()
    return () => { cancelled = true }
  }, [invoiceId, historyLoaded])

  const sendMessage = useCallback(async (text: string) => {
    setLoading(true)
    try {
      // Add user message optimistically
      const userMsg: Message = { type: 'HumanMessage', content: text }
      setMessages(prev => [...prev, userMsg])

      const res = await api.chat(threadId, text)
      setMessages(prev => mergeMessages(prev, res.messages))
      setInterrupt(res.interrupt)
      setAgentState(res.state)
    } catch (err) {
      console.error('Chat error:', err)
    } finally {
      setLoading(false)
    }
  }, [threadId])

  // Escalation changes the level on the server directly, then the agent
  // drafts the next email, which comes back as a normal approval.
  const escalate = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.escalate(invoiceId)
      setMessages(prev => mergeMessages(prev, res.messages))
      setInterrupt(res.interrupt)
      setAgentState(res.state)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Could not escalate this invoice.'
      setError(msg)
      setTimeout(() => setError(null), 10000)
      console.error('Escalate error:', err)
    } finally {
      setLoading(false)
    }
  }, [invoiceId])

  // Settling stops the agent; reload so the draft and status reflect it.
  const settle = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      await api.settle(invoiceId)
      setInterrupt(null)
      setAgentState(prev => (prev ? { ...prev, status: 'paid' } : prev))
      const res = await api.getHistory(invoiceId)
      if (res.state) setAgentState(res.state)
      if (res.communications) setCommunications(res.communications)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Could not mark this invoice as settled.'
      setError(msg)
      setTimeout(() => setError(null), 10000)
      console.error('Settle error:', err)
    } finally {
      setLoading(false)
    }
  }, [invoiceId])

  const approve = useCallback(async (approvedDraft?: string) => {
    setLoading(true)
    setLastEmailSent(null)
    setError(null)
    try {
      const res = await api.resume(invoiceId, 'approve', approvedDraft)
      setMessages(prev => mergeMessages(prev, res.messages))
      setInterrupt(res.interrupt)
      setAgentState(res.state)
      if (res.email_sent !== undefined) {
        setLastEmailSent({ sent: res.email_sent, id: res.email_id, status: res.email_status, note: res.email_note })
        // A confirmation can go quickly; an explanation of why nothing was sent stays longer.
        setTimeout(() => setLastEmailSent(null), res.email_sent ? 8000 : 20000)
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Something went wrong'
      setError(msg)
      setTimeout(() => setError(null), 10000)
      console.error('Approve error:', err)
    } finally {
      setLoading(false)
    }
  }, [invoiceId])

  const reject = useCallback(async (message: string) => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.resume(invoiceId, 'reject', message || 'Please revise.')
      setMessages(prev => mergeMessages(prev, res.messages))
      setInterrupt(res.interrupt)
      setAgentState(res.state)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Something went wrong'
      setError(msg)
      setTimeout(() => setError(null), 10000)
      console.error('Reject error:', err)
    } finally {
      setLoading(false)
    }
  }, [invoiceId])

  const initMessages = useCallback((msgs: Message[], inter: Interrupt | null, state: AgentState) => {
    setMessages(msgs)
    setInterrupt(inter)
    setAgentState(state)
  }, [])

  const refreshHistory = useCallback(async () => {
    if (!invoiceId) return
    try {
      const res = await api.getHistory(invoiceId)
      if (res.messages) setMessages(prev => mergeHistoryMessages(prev, res.messages))
      setInterrupt(res.interrupt)
      if (res.state) setAgentState(res.state)
      if (res.communications) setCommunications(res.communications)
    } catch (err) {
      console.error('Failed to refresh history:', err)
    }
  }, [invoiceId])

  return { messages, interrupt, agentState, communications, loading, lastEmailSent, error, sendMessage, escalate, settle, approve, reject, initMessages, refreshHistory }
}
