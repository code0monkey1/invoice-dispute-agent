import { useState, useRef, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import { useChat } from './useChat'
import { qk, senderQuery } from './queries'

const DRAFT_TOOLS = ['draft_invoice_delivery_email', 'draft_polite_reminder', 'draft_formal_demand_letter', 'draft_final_notice']
const APPROVAL_TOOLS = [...DRAFT_TOOLS, 'mark_invoice_pending', 'mark_invoice_paid', 'record_partial_payment']
const INVOICE_DELIVERY_PROMPT = 'Please draft the first invoice delivery email for this invoice. The email should tell the client the invoice is attached, reference the invoice number and amount due, and ask them to review and pay it.'
// Asks only for what the agent can see: invoice figures, a count of emails sent, and this chat.
const SUMMARY_PROMPT = "Give me a summary of this invoice: client, amount and balance due, status, days overdue, escalation level, how many emails have been sent, what has happened so far in this chat, and what you'd suggest doing next."

const NEXT_LEVEL_NAMES: Record<number, string> = { 1: 'Friendly', 2: 'Formal', 3: 'Legal' }
const STATUS_LABELS: Record<string, string> = { active: 'Active', pending: 'Promised to pay', paid: 'Settled' }

export function useChatPanel() {
  const { invoiceId } = useParams<{ invoiceId: string }>()
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [chatFocused, setChatFocused] = useState(false)
  const [view, setView] = useState<'chat' | 'trace'>('chat')
  const [editingDetails, setEditingDetails] = useState(false)
  const [editName, setEditName] = useState('')
  const [editEmail, setEditEmail] = useState('')
  const [savingDetails, setSavingDetails] = useState(false)

  const [editingSender, setEditingSender] = useState(false)
  const [senderName, setSenderName] = useState('')
  const [senderEmail, setSenderEmail] = useState('')
  const [senderBusiness, setSenderBusiness] = useState('')
  const [savingSender, setSavingSender] = useState(false)

  const {
    messages,
    interrupt,
    agentState,
    communications,
    summary,
    summaryMetadata,
    hasHistory,
    hasOutbound,
    fullHistoryVisible,
    fullHistoryLoading,
    fullHistoryError,
    viewHistory,
    hideHistory,
    retryHistory,
    loading,
    lastEmailSent,
    historyLoaded,
    error,
    sendMessage,
    escalate,
    settle,
    approve,
    reject,
    initMessages,
  } = useChat(invoiceId || '')

  const queryClient = useQueryClient()
  const sender = useQuery({ ...senderQuery(invoiceId || ''), enabled: Boolean(invoiceId && agentState?.invoice_id) })
  const senderLoaded = sender.isSuccess || sender.isError

  const startEditingSender = () => {
    setSenderName(sender.data?.freelancer_name ?? '')
    setSenderEmail(sender.data?.freelancer_email ?? '')
    setSenderBusiness(sender.data?.business_name ?? '')
    setEditingSender(true)
  }

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, interrupt])

  const displayInvoiceId = agentState?.invoice_id || invoiceId
  const hasOutboundCommunication = hasOutbound || communications.some(entry => entry.direction === 'outbound')
  const hasSavedConversation = hasHistory || messages.length > 0 || hasOutboundCommunication
  const showFirstOpenActions = Boolean(
    agentState?.invoice_id &&
    historyLoaded &&
    agentState.status !== 'paid' &&
    !interrupt &&
    messages.length === 0 &&
    !hasSavedConversation
  )

  // Auto-approve non-draft interrupts silently (e.g. mark_invoice_pending)
  useEffect(() => {
    if (interrupt && !APPROVAL_TOOLS.includes(interrupt.tool) && !loading) {
      approve()
    }
  }, [approve, interrupt, loading])

  const handleSend = () => {
    if (!input.trim() || loading) return
    sendMessage(input.trim())
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleEscalate = () => {
    escalate()
  }

  // Which control opened the settle confirmation; one confirmation serves both.
  const [confirmingSettle, setConfirmingSettle] = useState<'sidebar' | 'bar' | null>(null)
  const settled = agentState?.status === 'paid'
  const draftWaiting = !!(interrupt && APPROVAL_TOOLS.includes(interrupt.tool))
  const showQuickActions = Boolean(agentState && !showFirstOpenActions && !settled)
  const quickActionsBusy = loading || draftWaiting
  const atHighestLevel = (agentState?.escalation_level ?? 0) >= 3

  const quickActionClass = 'shrink-0 inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs font-semibold text-gray-600 hover:border-[#FF6B35]/50 hover:bg-orange-50 hover:text-[#FF6B35] disabled:opacity-50 disabled:pointer-events-none transition-colors'

  const handleCreateDeliveryDraft = () => {
    if (loading || interrupt) return
    sendMessage(INVOICE_DELIVERY_PROMPT)
  }

  const handleChatAboutInvoice = () => {
    setChatFocused(true)
    inputRef.current?.focus()
  }

  const saveDetails = async () => {
  if (!invoiceId) return
  setSavingDetails(true)
  try {
    const res = await api.updateDetails(invoiceId, {
      client_name: editName.trim(),
      client_email: editEmail.trim(),
    })
    if (res.state) {
      initMessages(messages, interrupt, res.state)
    }
    setEditingDetails(false)
    // If there's a pending draft, regenerate it with updated details
    if (interrupt) {
      reject('Client details were updated. Please regenerate the draft with the new details.')
    }
  } catch (err) {
    console.error('Failed to update details:', err)
  } finally {
    setSavingDetails(false)
  }
  }

  const saveSender = async () => {
  if (!invoiceId) return
  setSavingSender(true)
  try {
    const res = await api.updateSender(invoiceId, {
      freelancer_name: senderName.trim(),
      freelancer_email: senderEmail.trim(),
      business_name: senderBusiness.trim(),
    })
    queryClient.setQueryData(qk.sender(invoiceId), res)
    setEditingSender(false)
    // If there's a pending draft, regenerate it with updated sender
    if (interrupt) {
      reject('Sender details were updated. Please regenerate the draft with the new sender information.')
    }
  } catch (err) {
    console.error('Failed to update sender:', err)
  } finally {
    setSavingSender(false)
  }
  }

  return {
    APPROVAL_TOOLS,
    SUMMARY_PROMPT,
    invoiceId,
    input,
    setInput,
    messagesEndRef,
    inputRef,
    chatFocused,
    view,
    setView,
    messages,
    interrupt,
    agentState,
    communications,
    summary,
    summaryMetadata,
    fullHistoryVisible,
    fullHistoryLoading,
    fullHistoryError,
    viewHistory,
    hideHistory,
    retryHistory,
    loading,
    lastEmailSent,
    error,
    sendMessage,
    settle,
    approve,
    reject,
    displayInvoiceId,
    hasSavedConversation,
    showFirstOpenActions,
    handleSend,
    handleKeyDown,
    handleEscalate,
    confirmingSettle,
    setConfirmingSettle,
    showQuickActions,
    quickActionsBusy,
    atHighestLevel,
    quickActionClass,
    handleCreateDeliveryDraft,
    handleChatAboutInvoice,
    NEXT_LEVEL_NAMES,
    STATUS_LABELS,
    editingDetails,
    setEditingDetails,
    editName,
    setEditName,
    editEmail,
    setEditEmail,
    savingDetails,
    editingSender,
    setEditingSender,
    senderName,
    setSenderName,
    senderEmail,
    setSenderEmail,
    senderBusiness,
    setSenderBusiness,
    savingSender,
    sender,
    senderLoaded,
    startEditingSender,
    settled,
    saveDetails,
    saveSender,
  }
}
