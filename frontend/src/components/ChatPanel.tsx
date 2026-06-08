import { useState, useRef, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Send, ArrowUpCircle, FileText, Shield, MessageSquare, ChevronUp, Pencil, Check, X, MailCheck, MailX, User, AlertCircle } from 'lucide-react'
import MessageBubble from './MessageBubble'
import DraftApproval from './DraftApproval'
import EscalationBadge from './EscalationBadge'
import { useChat } from '../hooks/useChat'
import { api } from '../api'

const DRAFT_TOOLS = ['draft_invoice_delivery_email', 'draft_polite_reminder', 'draft_formal_demand_letter', 'draft_final_notice']
const APPROVAL_TOOLS = [...DRAFT_TOOLS, 'mark_invoice_pending', 'mark_invoice_paid', 'record_partial_payment']
const INVOICE_DELIVERY_PROMPT = 'Please draft the first invoice delivery email for this invoice. The email should tell the client the invoice is attached, reference the invoice number and amount due, and ask them to review and pay it.'

export default function ChatPanel() {
  const { invoiceId } = useParams<{ invoiceId: string }>()
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [chatFocused, setChatFocused] = useState(false)
  const [editingDetails, setEditingDetails] = useState(false)
  const [editName, setEditName] = useState('')
  const [editEmail, setEditEmail] = useState('')
  const [savingDetails, setSavingDetails] = useState(false)

  const [editingSender, setEditingSender] = useState(false)
  const [senderName, setSenderName] = useState('')
  const [senderEmail, setSenderEmail] = useState('')
  const [senderBusiness, setSenderBusiness] = useState('')
  const [savingSender, setSavingSender] = useState(false)
  const [senderLoaded, setSenderLoaded] = useState(false)

  const {
    messages,
    interrupt,
    agentState,
    communications,
    loading,
    lastEmailSent,
    error,
    sendMessage,
    approve,
    reject,
    initMessages,
    refreshHistory,
  } = useChat(invoiceId || '')

  // Load sender details once
  useEffect(() => {
    if (!invoiceId || senderLoaded || !agentState?.invoice_id) return
    api.getSender(invoiceId).then((res) => {
      setSenderName(res.freelancer_name)
      setSenderEmail(res.freelancer_email)
      setSenderBusiness(res.business_name)
      setSenderLoaded(true)
    }).catch(() => setSenderLoaded(true))
  }, [invoiceId, senderLoaded, agentState?.invoice_id])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, interrupt])

  const displayInvoiceId = agentState?.invoice_id || invoiceId
  const hasOutboundCommunication = communications.some(entry => entry.direction === 'outbound')
  const showFirstOpenActions = Boolean(
    agentState?.invoice_id &&
    agentState.status !== 'paid' &&
    !interrupt &&
    !hasOutboundCommunication
  )

  // Auto-approve non-draft interrupts silently (e.g. mark_invoice_pending)
  useEffect(() => {
    if (interrupt && !APPROVAL_TOOLS.includes(interrupt.tool) && !loading) {
      approve()
    }
  }, [approve, interrupt, loading])

  // Periodic refresh to pick up webhook-injected messages (e.g. inbound client emails)
  useEffect(() => {
    if (!invoiceId) return
    const interval = setInterval(() => {
      if (!loading) refreshHistory()
    }, 30000)
    return () => clearInterval(interval)
  }, [invoiceId, loading, refreshHistory])

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
    sendMessage('Please escalate this dispute to the next level.')
  }

  const handleCreateDeliveryDraft = () => {
    if (loading || interrupt) return
    sendMessage(INVOICE_DELIVERY_PROMPT)
  }

  const handleChatAboutInvoice = () => {
    setChatFocused(true)
    inputRef.current?.focus()
  }

  return (
    <div className="flex gap-6 h-[calc(100vh-7rem)] animate-fade-up">
      {/* Chat Area */}
      <div className="flex-1 flex flex-col bg-white border border-gray-200/80 rounded-2xl overflow-hidden shadow-sm">
        {/* Chat Header */}
        <div className="flex items-center gap-3 px-5 py-3.5 border-b border-gray-100 bg-gradient-to-r from-white to-orange-50/30">
          <Link to="/" className="text-gray-400 hover:text-[#FF6B35] transition-colors p-1 rounded-lg hover:bg-orange-50">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="flex-1">
            <h2 className="text-sm font-bold text-gray-800 font-[family-name:var(--font-heading)]">
              Invoice <span className="font-mono text-[#FF6B35] bg-orange-50 px-1.5 py-0.5 rounded-md">#{displayInvoiceId}</span>
              {agentState?.client_name && (
                <span className="text-gray-400 font-normal font-sans"> — {agentState.client_name}</span>
              )}
            </h2>
          </div>
          {agentState && <EscalationBadge level={agentState.escalation_level} />}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto py-4 space-y-1 bg-gradient-to-b from-orange-50/20 to-white">
          {messages.length === 0 && !loading && !showFirstOpenActions && (
            <div className="flex flex-col items-center justify-center h-full text-center px-8">
              <div className="w-14 h-14 bg-gradient-to-br from-[#FF6B35] to-[#FF8F65] rounded-2xl flex items-center justify-center mb-4 shadow-lg shadow-orange-200/40">
                <ArrowUpCircle className="w-7 h-7 text-white" />
              </div>
              <p className="text-gray-600 text-sm font-semibold font-[family-name:var(--font-heading)]">
                Send a message to start working on this invoice dispute.
              </p>
              <p className="text-gray-400 text-xs mt-2 font-medium">
                Try: "Help me chase this payment" or "Draft a reminder"
              </p>
            </div>
          )}
          {showFirstOpenActions && (
            <div className="mx-5 mb-4 rounded-2xl border border-orange-200 bg-white shadow-sm overflow-hidden animate-fade-up">
              <div className="px-5 py-4 bg-gradient-to-r from-orange-50 to-amber-50 border-b border-orange-100">
                <p className="text-sm font-bold text-gray-800 font-[family-name:var(--font-heading)]">
                  Start with this invoice
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Create the first email for this invoice or ask invoice-specific questions.
                </p>
              </div>
              <div className="p-4 grid sm:grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={handleCreateDeliveryDraft}
                  disabled={loading}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#FF6B35] to-[#FF8F65] px-4 py-3 text-sm font-bold text-white shadow-md shadow-orange-200/40 disabled:opacity-50 font-[family-name:var(--font-heading)]"
                >
                  <FileText className="w-4 h-4" />
                  Create invoice email draft
                </button>
                <button
                  type="button"
                  onClick={handleChatAboutInvoice}
                  disabled={loading}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border-2 border-gray-200 bg-white px-4 py-3 text-sm font-bold text-gray-700 hover:bg-gray-50 disabled:opacity-50 font-[family-name:var(--font-heading)]"
                >
                  <MessageSquare className="w-4 h-4" />
                  Chat about this invoice
                </button>
              </div>
            </div>
          )}
          {messages
            .filter(msg => msg.type !== 'ToolMessage' && !(msg.type === 'AIMessage' && !msg.content && msg.tool_calls?.length))
            .map((msg, i) => (
              <MessageBubble key={i} message={msg} />
            ))}
          {interrupt && APPROVAL_TOOLS.includes(interrupt.tool) && (
            <DraftApproval
              interrupt={interrupt}
              onApprove={approve}
              onReject={reject}
              loading={loading}
            />
          )}
          {loading && !interrupt && (
            <div className="flex items-center gap-2.5 px-5 py-3">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#FF6B35] animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 rounded-full bg-[#FF6B35] animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 rounded-full bg-[#FF6B35] animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span className="text-gray-400 text-sm font-medium">Agent is thinking...</span>
            </div>
          )}
          {lastEmailSent && (
            <div className={`mx-5 my-3 animate-fade-up`}>
              <div className={`inline-flex items-center gap-2.5 px-4 py-2.5 rounded-xl text-sm font-semibold ${
                lastEmailSent.sent
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200/60'
                  : 'bg-rose-50 text-rose-700 border border-rose-200/60'
              }`}>
                {lastEmailSent.sent ? (
                  <>
                    <MailCheck className="w-4 h-4" />
                    Email sent successfully to {agentState?.client_email}
                  </>
                ) : (
                  <>
                    <MailX className="w-4 h-4" />
                    Email could not be sent — draft was approved but delivery failed
                  </>
                )}
              </div>
            </div>
          )}
          {error && (
            <div className="mx-5 my-3 animate-fade-up">
              <div className="inline-flex items-center gap-2.5 px-4 py-2.5 rounded-xl text-sm font-semibold bg-amber-50 text-amber-700 border border-amber-200/60">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-100 px-4 py-3 bg-white">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={interrupt && APPROVAL_TOOLS.includes(interrupt.tool) ? 'Approve or reject the draft above...' : chatFocused ? 'Ask about this invoice or your other invoices...' : 'Type your message...'}
              disabled={loading || !!(interrupt && APPROVAL_TOOLS.includes(interrupt.tool))}
              className="flex-1 bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm text-gray-800 placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[#FF6B35]/30 focus:border-[#FF6B35]/50 disabled:opacity-50 transition-all"
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim() || !!(interrupt && APPROVAL_TOOLS.includes(interrupt.tool))}
              className="btn-gradient disabled:opacity-50 text-white rounded-xl px-4 py-2.5 transition-all shadow-md shadow-orange-200/40"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Sidebar */}
      <div className="w-72 flex-shrink-0 space-y-4">
        {/* Invoice Details */}
        <div className="bg-white border border-gray-200/80 rounded-2xl overflow-hidden shadow-sm animate-fade-up">
          <div className="bg-gradient-to-r from-[#FF6B35]/10 to-orange-50 px-5 py-3 border-b border-orange-100/50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-[#FF6B35] to-[#FF8F65] flex items-center justify-center">
                <FileText className="w-3 h-3 text-white" />
              </div>
              <h3 className="text-xs font-bold text-gray-600 uppercase tracking-widest font-[family-name:var(--font-heading)]">Invoice Details</h3>
            </div>
            {agentState && agentState.invoice_id && !editingDetails && (
              <button
                onClick={() => {
                  setEditName(agentState.client_name)
                  setEditEmail(agentState.client_email)
                  setEditingDetails(true)
                }}
                className="text-gray-400 hover:text-[#FF6B35] transition-colors p-1 rounded-lg hover:bg-orange-50"
                title="Edit client details"
              >
                <Pencil className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          <div className="p-5">
            {agentState && agentState.invoice_id ? (
              editingDetails ? (
                <div className="space-y-3">
                  <div>
                    <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Client Name</label>
                    <input
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-[#FF6B35]/30 focus:border-[#FF6B35]/50"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Client Email</label>
                    <input
                      type="email"
                      value={editEmail}
                      onChange={(e) => setEditEmail(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-[#FF6B35]/30 focus:border-[#FF6B35]/50"
                    />
                  </div>
                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={async () => {
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
                      }}
                      disabled={savingDetails || !editName.trim() || !editEmail.trim()}
                      className="flex-1 inline-flex items-center justify-center gap-1.5 bg-gradient-to-r from-emerald-500 to-green-500 hover:from-emerald-600 hover:to-green-600 disabled:opacity-50 text-white text-xs font-bold rounded-lg py-2 transition-all"
                    >
                      <Check className="w-3 h-3" />
                      {savingDetails ? 'Saving...' : 'Save'}
                    </button>
                    <button
                      onClick={() => setEditingDetails(false)}
                      className="inline-flex items-center justify-center gap-1 text-gray-400 hover:text-gray-600 text-xs font-medium px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      <X className="w-3 h-3" />
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <dl className="space-y-3 text-sm">
                  {[
                    ['Client', agentState.client_name],
                    ['Email', agentState.client_email],
                    ['Original', `$${agentState.invoice_amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}`],
                    ['Paid', `$${agentState.amount_paid.toLocaleString('en-US', { minimumFractionDigits: 2 })}`],
                    ['Balance', `$${agentState.balance_due.toLocaleString('en-US', { minimumFractionDigits: 2 })}`],
                    ['Status', agentState.status],
                    ['Overdue', `${agentState.days_overdue} days`],
                    ['Jurisdiction', agentState.jurisdiction],
                  ].map(([label, value]) => (
                    <div key={label} className="flex justify-between items-baseline">
                      <dt className="text-gray-400 text-xs font-semibold uppercase tracking-wider">{label}</dt>
                      <dd className="text-gray-800 font-semibold text-right">{value}</dd>
                    </div>
                  ))}
                </dl>
              )
            ) : (
              <p className="text-gray-400 text-sm font-medium">Send a message to load invoice details.</p>
            )}
          </div>
        </div>

        {/* Sender Details */}
        {agentState && agentState.invoice_id && senderLoaded && (
          <div className="bg-white border border-gray-200/80 rounded-2xl overflow-hidden shadow-sm animate-fade-up" style={{ animationDelay: '30ms' }}>
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50/50 px-5 py-3 border-b border-blue-100/50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center">
                  <User className="w-3 h-3 text-white" />
                </div>
                <h3 className="text-xs font-bold text-gray-600 uppercase tracking-widest font-[family-name:var(--font-heading)]">Sender Details</h3>
              </div>
              {!editingSender && (
                <button
                  onClick={() => setEditingSender(true)}
                  className="text-gray-400 hover:text-blue-500 transition-colors p-1 rounded-lg hover:bg-blue-50"
                  title="Edit sender details"
                >
                  <Pencil className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            <div className="p-5">
              {editingSender ? (
                <div className="space-y-3">
                  <div>
                    <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Your Name</label>
                    <input
                      value={senderName}
                      onChange={(e) => setSenderName(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-400/30 focus:border-blue-400/50"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Business Name</label>
                    <input
                      value={senderBusiness}
                      onChange={(e) => setSenderBusiness(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-400/30 focus:border-blue-400/50"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Your Email</label>
                    <input
                      type="email"
                      value={senderEmail}
                      onChange={(e) => setSenderEmail(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-400/30 focus:border-blue-400/50"
                    />
                  </div>
                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={async () => {
                        if (!invoiceId) return
                        setSavingSender(true)
                        try {
                          const res = await api.updateSender(invoiceId, {
                            freelancer_name: senderName.trim(),
                            freelancer_email: senderEmail.trim(),
                            business_name: senderBusiness.trim(),
                          })
                          setSenderName(res.freelancer_name)
                          setSenderEmail(res.freelancer_email)
                          setSenderBusiness(res.business_name)
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
                      }}
                      disabled={savingSender || !senderName.trim()}
                      className="flex-1 inline-flex items-center justify-center gap-1.5 bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600 hover:to-indigo-600 disabled:opacity-50 text-white text-xs font-bold rounded-lg py-2 transition-all"
                    >
                      <Check className="w-3 h-3" />
                      {savingSender ? 'Saving...' : 'Save'}
                    </button>
                    <button
                      onClick={() => {
                        // Reset to saved values
                        if (invoiceId) {
                          api.getSender(invoiceId).then((res) => {
                            setSenderName(res.freelancer_name)
                            setSenderEmail(res.freelancer_email)
                            setSenderBusiness(res.business_name)
                          })
                        }
                        setEditingSender(false)
                      }}
                      className="inline-flex items-center justify-center gap-1 text-gray-400 hover:text-gray-600 text-xs font-medium px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      <X className="w-3 h-3" />
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <dl className="space-y-3 text-sm">
                  {[
                    ['Name', senderName],
                    ['Business', senderBusiness],
                    ['Email', senderEmail],
                  ].map(([label, value]) => (
                    <div key={label} className="flex justify-between items-baseline">
                      <dt className="text-gray-400 text-xs font-semibold uppercase tracking-wider">{label}</dt>
                      <dd className="text-gray-800 font-semibold text-right">{value}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>
          </div>
        )}

        {/* Escalation Control */}
        <div className="bg-white border border-gray-200/80 rounded-2xl overflow-hidden shadow-sm animate-fade-up" style={{ animationDelay: '60ms' }}>
          <div className="bg-gradient-to-r from-violet-50 to-purple-50/50 px-5 py-3 border-b border-violet-100/50 flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-violet-500 to-purple-500 flex items-center justify-center">
              <Shield className="w-3 h-3 text-white" />
            </div>
            <h3 className="text-xs font-bold text-gray-600 uppercase tracking-widest font-[family-name:var(--font-heading)]">Escalation</h3>
          </div>
          <div className="p-5">
            {agentState && (
              <>
                <div className="mb-4">
                  <EscalationBadge level={agentState.escalation_level} size="md" />
                </div>
                <div className="space-y-2.5 text-xs mb-4">
                  <div className={`flex items-center gap-2.5 font-medium ${agentState.escalation_level >= 1 ? 'text-emerald-600' : 'text-gray-300'}`}>
                    <span className={`w-2.5 h-2.5 rounded-full ${agentState.escalation_level >= 1 ? 'bg-gradient-to-br from-emerald-400 to-green-500 shadow-sm shadow-emerald-200' : 'bg-gray-200'}`} />
                    Level 1: Friendly reminders
                  </div>
                  <div className={`flex items-center gap-2.5 font-medium ${agentState.escalation_level >= 2 ? 'text-amber-600' : 'text-gray-300'}`}>
                    <span className={`w-2.5 h-2.5 rounded-full ${agentState.escalation_level >= 2 ? 'bg-gradient-to-br from-amber-400 to-orange-500 shadow-sm shadow-amber-200' : 'bg-gray-200'}`} />
                    Level 2: Formal demands + late fees
                  </div>
                  <div className={`flex items-center gap-2.5 font-medium ${agentState.escalation_level >= 3 ? 'text-rose-600' : 'text-gray-300'}`}>
                    <span className={`w-2.5 h-2.5 rounded-full ${agentState.escalation_level >= 3 ? 'bg-gradient-to-br from-rose-400 to-red-500 shadow-sm shadow-rose-200' : 'bg-gray-200'}`} />
                    Level 3: Legal action + court filing
                  </div>
                </div>
                {agentState.escalation_level < 3 && (
                  <button
                    onClick={handleEscalate}
                    disabled={loading || !!interrupt}
                    className="w-full inline-flex items-center justify-center gap-2 bg-gradient-to-r from-violet-500 to-purple-500 hover:from-violet-600 hover:to-purple-600 disabled:opacity-50 text-white text-xs font-bold rounded-xl py-2.5 transition-all shadow-md shadow-violet-200/40 font-[family-name:var(--font-heading)]"
                  >
                    <ChevronUp className="w-3.5 h-3.5" />
                    Escalate to Level {agentState.escalation_level + 1}
                  </button>
                )}
              </>
            )}
          </div>
        </div>

        {/* Communication Log */}
        <div className="bg-white border border-gray-200/80 rounded-2xl overflow-hidden shadow-sm animate-fade-up" style={{ animationDelay: '120ms' }}>
          <div className="bg-gradient-to-r from-teal-50 to-emerald-50/50 px-5 py-3 border-b border-teal-100/50 flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-teal-500 to-emerald-500 flex items-center justify-center">
              <MessageSquare className="w-3 h-3 text-white" />
            </div>
            <h3 className="text-xs font-bold text-gray-600 uppercase tracking-widest font-[family-name:var(--font-heading)]">Communication Log</h3>
          </div>
          <div className="p-5">
            {communications.length ? (
              <div className="space-y-3">
                {communications.slice().reverse().map((entry) => {
                  const isInbound = entry.direction === 'inbound'
                  return (
                    <div key={entry.id} className={`text-xs border-l-2 pl-3 py-1.5 ${isInbound ? 'border-blue-400/70' : 'border-teal-400/50'}`}>
                      <div className="flex items-center justify-between gap-2">
                        <span className={`font-bold uppercase tracking-wider text-[10px] ${isInbound ? 'text-blue-500' : 'text-teal-600'}`}>
                          {isInbound ? '📩 Client Reply' : `📤 ${entry.type}`}
                        </span>
                        <span className="text-gray-300 text-[10px] font-medium">
                          {new Date(entry.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      {entry.subject && (
                        <p className="text-gray-600 mt-0.5 font-medium leading-snug">{entry.subject}</p>
                      )}
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="text-gray-400 text-xs font-medium italic">Communications will appear here as you approve drafts.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
