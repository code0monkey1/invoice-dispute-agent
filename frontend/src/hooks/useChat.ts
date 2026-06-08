import { useState, useCallback, useEffect } from 'react'
import { api } from '../api'
import type { Message, Interrupt, AgentState, SupabaseCommEntry } from '../types'

export function useChat(invoiceId: string) {
  const [messages, setMessages] = useState<Message[]>([])
  const [interrupt, setInterrupt] = useState<Interrupt | null>(null)
  const [agentState, setAgentState] = useState<AgentState | null>(null)
  const [communications, setCommunications] = useState<SupabaseCommEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const [lastEmailSent, setLastEmailSent] = useState<{ sent: boolean; id?: string } | null>(null)
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
      setMessages(res.messages)
      setInterrupt(res.interrupt)
      setAgentState(res.state)
    } catch (err) {
      console.error('Chat error:', err)
    } finally {
      setLoading(false)
    }
  }, [threadId])

  const approve = useCallback(async (approvedDraft?: string) => {
    setLoading(true)
    setLastEmailSent(null)
    setError(null)
    try {
      const res = await api.resume(invoiceId, 'approve', approvedDraft)
      setMessages(res.messages)
      setInterrupt(res.interrupt)
      setAgentState(res.state)
      if (res.email_sent !== undefined) {
        setLastEmailSent({ sent: res.email_sent, id: res.email_id })
        // Auto-clear after 8 seconds
        setTimeout(() => setLastEmailSent(null), 8000)
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
      setMessages(res.messages)
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
      if (res.messages) setMessages(res.messages)
      setInterrupt(res.interrupt)
      if (res.state) setAgentState(res.state)
      if (res.communications) setCommunications(res.communications)
    } catch (err) {
      console.error('Failed to refresh history:', err)
    }
  }, [invoiceId])

  return { messages, interrupt, agentState, communications, loading, lastEmailSent, error, sendMessage, approve, reject, initMessages, refreshHistory }
}
