import { Link } from 'react-router-dom'
import { ArrowLeft, Send, ArrowUpCircle, FileText, MessageSquare, Check, MailCheck, MailX, AlertCircle, Activity } from 'lucide-react'
import MessageBubble from '../MessageBubble'
import Markdown from '../Markdown'
import DraftApproval from '../DraftApproval'
import EscalationBadge from '../EscalationBadge'
import TracePanel from '../TracePanel'
import type { useChatPanel } from '../../hooks/useChatPanel'
import { SettleConfirmation } from './SettleConfirmation'

export function ChatConversation({ panel }: { panel: ReturnType<typeof useChatPanel> }) {
  const {
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
  } = panel
  const settleConfirmation = <SettleConfirmation loading={loading} onConfirm={() => { setConfirmingSettle(null); settle() }} onCancel={() => setConfirmingSettle(null)} />
  return (
    <>
      {/* Chat Area */}
      <div className="flex-1 min-w-0 flex flex-col min-h-[70dvh] lg:min-h-0 bg-white border border-gray-200/80 rounded-xl overflow-hidden shadow-card">
        {/* Chat Header */}
        <div className="flex items-center gap-3 px-5 py-3.5 border-b border-gray-100 bg-gradient-to-r from-white to-orange-50/30">
          <Link to="/" className="text-muted hover:text-coral-text transition-colors p-1 rounded-lg hover:bg-orange-50">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="flex-1">
            <h2 className="text-sm font-bold text-ink">
              Invoice <span className="font-mono text-coral-text bg-orange-50 px-1.5 py-0.5 rounded-md">#{displayInvoiceId}</span>
              {agentState?.client_name && (
                <span className="text-muted font-normal font-sans"> — {agentState.client_name}</span>
              )}
            </h2>
          </div>
          {agentState && <EscalationBadge level={agentState.escalation_level} />}
        </div>

        {/* Chat | Trace */}
        <div role="tablist" aria-label="Invoice view" className="flex gap-1 px-4 pt-2 border-b border-gray-100 bg-white">
          {([
            { id: 'chat', label: 'Chat', icon: MessageSquare },
            { id: 'trace', label: 'Trace', icon: Activity },
          ] as const).map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              role="tab"
              id={`tab-${id}`}
              aria-selected={view === id}
              aria-controls={`panel-${id}`}
              onClick={() => setView(id)}
              className={`inline-flex items-center gap-1.5 px-3 py-2 text-xs font-bold border-b-2 -mb-px transition-colors ${
                view === id ? 'border-coral text-coral-text' : 'border-transparent text-muted hover:text-body'
              }`}
            >
              <Icon className="w-3.5 h-3.5" aria-hidden />
              {label}
              {id === 'chat' && view !== 'chat' && interrupt && APPROVAL_TOOLS.includes(interrupt.tool) && (
                <span className="rounded-full bg-amber-100 text-amber-700 px-1.5 text-xs">1 waiting</span>
              )}
            </button>
          ))}
        </div>

        {view === 'trace' ? (
          <div role="tabpanel" id="panel-trace" aria-labelledby="tab-trace" className="flex-1 flex flex-col min-h-0">
            <TracePanel invoiceId={invoiceId || ''} />
          </div>
        ) : (
        <div role="tabpanel" id="panel-chat" aria-labelledby="tab-chat" className="flex-1 flex flex-col min-h-0">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto py-4 space-y-1 bg-gradient-to-b from-orange-50/20 to-white">
          <section aria-labelledby="conversation-summary-title" className="mx-5 mb-5 pb-4 border-b border-gray-100">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <h3 id="conversation-summary-title" className="text-sm font-semibold text-ink">Conversation summary</h3>
              <button type="button" onClick={fullHistoryVisible ? hideHistory : viewHistory}
                aria-expanded={Boolean(fullHistoryVisible)} aria-controls="conversation-history"
                disabled={!hasSavedConversation}
                className="text-xs font-semibold text-coral-text hover:text-ink underline underline-offset-4 disabled:text-muted disabled:no-underline focus-visible:outline-2 focus-visible:outline-offset-4">
                {fullHistoryVisible ? 'Hide conversation history' : 'View conversation history'}
              </button>
            </div>
            {summary ? <div className="text-sm leading-relaxed text-body max-w-[75ch]"><Markdown>{summary}</Markdown></div> : (
              <p className="text-sm text-muted">{hasSavedConversation ? 'Your saved summary will appear here. You can also view the full conversation history.' : 'Your summary will appear here after the conversation begins.'}</p>
            )}
            {summary && summaryMetadata?.is_stale && <p className="text-xs text-muted mt-3">New updates will be included when you next open this invoice.</p>}
          </section>
          {fullHistoryLoading && <p role="status" className="mx-5 text-sm text-muted">Loading conversation history…</p>}
          {fullHistoryError && <div role="alert" className="mx-5 text-sm text-body">
            Could not load conversation history. <button type="button" onClick={() => void retryHistory()} className="underline text-coral-text">Retry history</button>
          </div>}
          {messages.length === 0 && !loading && !showFirstOpenActions && !hasSavedConversation && (
            <div className="flex flex-col items-center justify-center h-full text-center px-8">
              <div className="w-14 h-14 bg-gradient-to-br from-coral to-coral-2 rounded-xl flex items-center justify-center mb-4 shadow-card">
                <ArrowUpCircle className="w-7 h-7 text-ink" />
              </div>
              <p className="text-body text-sm font-semibold">
                Send a message to start working on this invoice dispute.
              </p>
              <p className="text-muted text-xs mt-2 font-medium">
                Try: "Help me chase this payment" or "Draft a reminder"
              </p>
            </div>
          )}
          {showFirstOpenActions && (
            <div className="mx-5 mb-4 rounded-xl border border-orange-200 bg-white shadow-card overflow-hidden animate-fade-up">
              <div className="px-5 py-4 bg-gradient-to-r from-orange-50 to-amber-50 border-b border-orange-100">
                <p className="text-sm font-bold text-ink">
                  Start with this invoice
                </p>
                <p className="text-xs text-muted mt-1">
                  Create the first email for this invoice or ask invoice-specific questions.
                </p>
              </div>
              <div className="p-4 grid sm:grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={handleCreateDeliveryDraft}
                  disabled={loading}
                  className="inline-flex items-center justify-center gap-2 btn-coral rounded-xl px-4 py-3 text-sm font-bold shadow-card"
                >
                  <FileText className="w-4 h-4" />
                  Create invoice email draft
                </button>
                <button
                  type="button"
                  onClick={handleChatAboutInvoice}
                  disabled={loading}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border-2 border-gray-200 bg-white px-4 py-3 text-sm font-bold text-body hover:bg-gray-50 disabled:opacity-50"
                >
                  <MessageSquare className="w-4 h-4" />
                  Chat about this invoice
                </button>
              </div>
            </div>
          )}
          <div id="conversation-history">
          {messages
            .filter(msg => msg.type !== 'ToolMessage' && !(msg.type === 'AIMessage' && !msg.content && msg.tool_calls?.length))
            .map((msg, i) => (
              <MessageBubble key={i} message={msg} />
            ))}
          {fullHistoryVisible && communications.length > 0 && (
            <section aria-label="Email and communication history" className="mx-5 mt-5 mb-4 space-y-3">
              <h3 className="text-sm font-semibold text-body">Email and communication history</h3>
              {communications.map(entry => <details key={entry.id} className="border border-gray-200 rounded-lg px-3 py-2 text-sm">
                <summary className="cursor-pointer text-body">{entry.subject || entry.type} <span className="text-xs text-muted">{entry.timestamp}</span></summary>
                <p className="whitespace-pre-wrap break-words mt-3 text-body">{entry.content}</p>
              </details>)}
            </section>
          )}
          </div>
          {interrupt && APPROVAL_TOOLS.includes(interrupt.tool) && (
            <DraftApproval
              interrupt={interrupt}
              onApprove={approve}
              onReject={reject}
              loading={loading}
              recipient={agentState?.client_email}
              level={agentState?.escalation_level}
            />
          )}
          {loading && !interrupt && (
            <div className="flex items-center gap-2.5 px-5 py-3">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-coral animate-pulse motion-reduce:animate-none" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 rounded-full bg-coral animate-pulse motion-reduce:animate-none" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 rounded-full bg-coral animate-pulse motion-reduce:animate-none" style={{ animationDelay: '300ms' }} />
              </div>
              <span className="text-muted text-sm font-medium">Agent is thinking...</span>
            </div>
          )}
          {lastEmailSent && (
            <div className={`mx-5 my-3 animate-fade-up`}>
              <div role="status" className={`inline-flex items-start gap-2.5 px-4 py-2.5 rounded-xl text-sm font-semibold ${
                lastEmailSent.sent
                  ? 'bg-green-bg text-green border border-green/20'
                  : lastEmailSent.status === 'demo'
                    ? 'bg-white text-body border border-line'
                    : 'bg-rose-50 text-rose-700 border border-rose-200/60'
              }`}>
                {lastEmailSent.sent ? (
                  <>
                    <MailCheck className="w-4 h-4 mt-0.5 shrink-0" />
                    Sent to {agentState?.client_email} from your Gmail.
                  </>
                ) : (
                  <>
                    <MailX className="w-4 h-4 mt-0.5 shrink-0" />
                    {lastEmailSent.note || "The draft was approved, but Gmail couldn't send it."}
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
          {showQuickActions && (
            <div className="mb-2.5">
              {confirmingSettle === 'bar' ? settleConfirmation : (
                <div className="flex gap-2 overflow-x-auto pb-0.5" aria-label="Quick actions">
                  <button
                    onClick={() => sendMessage(SUMMARY_PROMPT)}
                    disabled={quickActionsBusy}
                    className={quickActionClass}
                  >
                    <FileText className="w-3.5 h-3.5" />
                    Give me a summary
                  </button>
                  <button
                    onClick={handleEscalate}
                    disabled={quickActionsBusy || atHighestLevel}
                    title={atHighestLevel ? 'Already at the highest level (Legal)' : undefined}
                    className={quickActionClass}
                  >
                    <ArrowUpCircle className="w-3.5 h-3.5" />
                    Write next escalation email
                  </button>
                  <button
                    onClick={() => setConfirmingSettle('bar')}
                    disabled={quickActionsBusy}
                    className={quickActionClass}
                  >
                    <Check className="w-3.5 h-3.5" />
                    End dispute
                  </button>
                </div>
              )}
            </div>
          )}
          <div className="flex gap-2">
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={interrupt && APPROVAL_TOOLS.includes(interrupt.tool) ? 'Approve or reject the draft above...' : chatFocused ? 'Ask about this invoice or your other invoices...' : 'Type your message...'}
              disabled={loading || !!(interrupt && APPROVAL_TOOLS.includes(interrupt.tool))}
              className="flex-1 bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-coral/30 focus:border-coral/50 disabled:opacity-50 transition-colors"
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim() || !!(interrupt && APPROVAL_TOOLS.includes(interrupt.tool))}
              className="btn-coral rounded-xl px-4 py-2.5 shadow-card"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
        </div>
        )}
      </div>
    </>
  )
}
