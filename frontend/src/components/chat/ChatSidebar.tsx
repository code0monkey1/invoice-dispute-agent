import { FileText, Shield, MessageSquare, ChevronUp, Pencil, Check, X, User } from 'lucide-react'
import EscalationBadge from '../EscalationBadge'
import { formatPromiseDate } from '../format'
import type { useChatPanel } from '../../hooks/useChatPanel'
import { SettleConfirmation } from './SettleConfirmation'

export function ChatSidebar({ panel }: { panel: ReturnType<typeof useChatPanel> }) {
  const {
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
    interrupt,
    agentState,
    communications,
    loading,
    settle,
    sender,
    senderLoaded,
    startEditingSender,
    handleEscalate,
    confirmingSettle,
    setConfirmingSettle,
    settled,
    saveDetails,
    saveSender,
  } = panel
  const settleConfirmation = <SettleConfirmation loading={loading} onConfirm={() => { setConfirmingSettle(null); settle() }} onCancel={() => setConfirmingSettle(null)} />
  return (
    <>
      {/* Sidebar */}
      <div className="w-72 flex-shrink-0 space-y-4">
        {/* Invoice Details */}
        <div className="bg-white border border-gray-200/80 rounded-xl overflow-hidden shadow-card animate-fade-up">
          <div className="bg-gradient-to-r from-coral/10 to-orange-50 px-5 py-3 border-b border-orange-100/50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-coral to-coral-2 flex items-center justify-center">
                <FileText className="w-3 h-3 text-ink" />
              </div>
              <h3 className="text-xs font-bold text-gray-600 uppercase tracking-widest">Invoice Details</h3>
            </div>
            {agentState && agentState.invoice_id && !editingDetails && (
              <button
                onClick={() => {
                  setEditName(agentState.client_name)
                  setEditEmail(agentState.client_email)
                  setEditingDetails(true)
                }}
                className="text-gray-400 hover:text-coral-text transition-colors p-1 rounded-lg hover:bg-orange-50"
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
                    <label className="block text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">Client Name</label>
                    <input
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-coral/30 focus:border-coral/50"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">Client Email</label>
                    <input
                      type="email"
                      value={editEmail}
                      onChange={(e) => setEditEmail(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-coral/30 focus:border-coral/50"
                    />
                  </div>
                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={saveDetails}
                      disabled={savingDetails || !editName.trim() || !editEmail.trim()}
                      className="flex-1 inline-flex items-center justify-center gap-1.5 btn-coral text-xs font-bold rounded-lg py-2"
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
                    ['Status', STATUS_LABELS[agentState.status] ?? agentState.status],
                    ...(agentState.status === 'pending' && agentState.follow_up_date
                      ? [['Promised by', formatPromiseDate(agentState.follow_up_date)]]
                      : []),
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
          <div className="bg-white border border-gray-200/80 rounded-xl overflow-hidden shadow-card animate-fade-up" style={{ animationDelay: '30ms' }}>
            <div className="bg-tint px-5 py-3 border-b border-line flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-lg bg-ink flex items-center justify-center">
                  <User className="w-3 h-3 text-white" />
                </div>
                <h3 className="text-xs font-bold text-gray-600 uppercase tracking-widest">Sender Details</h3>
              </div>
              {!editingSender && (
                <button
                  onClick={startEditingSender}
                  className="text-gray-400 hover:text-ink transition-colors p-1 rounded-lg hover:bg-tint"
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
                    <label className="block text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">Your Name</label>
                    <input
                      value={senderName}
                      onChange={(e) => setSenderName(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-coral/30 focus:border-coral/50"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">Business Name</label>
                    <input
                      value={senderBusiness}
                      onChange={(e) => setSenderBusiness(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-coral/30 focus:border-coral/50"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">Your Email</label>
                    <input
                      type="email"
                      value={senderEmail}
                      onChange={(e) => setSenderEmail(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-coral/30 focus:border-coral/50"
                    />
                  </div>
                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={saveSender}
                      disabled={savingSender || !senderName.trim()}
                      className="flex-1 inline-flex items-center justify-center gap-1.5 btn-coral text-xs font-bold rounded-lg py-2"
                    >
                      <Check className="w-3 h-3" />
                      {savingSender ? 'Saving...' : 'Save'}
                    </button>
                    <button
                      onClick={() => setEditingSender(false)}
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
                    ['Name', sender.data?.freelancer_name ?? ''],
                    ['Business', sender.data?.business_name ?? ''],
                    ['Email', sender.data?.freelancer_email ?? ''],
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
        <div className="bg-white border border-gray-200/80 rounded-xl overflow-hidden shadow-card animate-fade-up" style={{ animationDelay: '60ms' }}>
          <div className="bg-tint px-5 py-3 border-b border-line flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-ink flex items-center justify-center">
              <Shield className="w-3 h-3 text-white" />
            </div>
            <h3 className="text-xs font-bold text-gray-600 uppercase tracking-widest">Escalation</h3>
          </div>
          <div className="p-5">
            {agentState && (
              <>
                <div className="mb-4">
                  <EscalationBadge level={agentState.escalation_level} size="md" />
                </div>
                <div className="space-y-2.5 text-xs mb-4">
                  <div className={`flex items-center gap-2.5 font-medium ${agentState.escalation_level >= 1 ? 'text-body' : 'text-gray-300'}`}>
                    <span className={`w-2.5 h-2.5 rounded-full ${agentState.escalation_level >= 1 ? 'bg-muted' : 'bg-gray-200'}`} />
                    Level 1: Friendly reminders
                  </div>
                  <div className={`flex items-center gap-2.5 font-medium ${agentState.escalation_level >= 2 ? 'text-amber-600' : 'text-gray-300'}`}>
                    <span className={`w-2.5 h-2.5 rounded-full ${agentState.escalation_level >= 2 ? 'bg-amber' : 'bg-gray-200'}`} />
                    Level 2: Formal demands
                  </div>
                  <div className={`flex items-center gap-2.5 font-medium ${agentState.escalation_level >= 3 ? 'text-rose-600' : 'text-gray-300'}`}>
                    <span className={`w-2.5 h-2.5 rounded-full ${agentState.escalation_level >= 3 ? 'bg-red' : 'bg-gray-200'}`} />
                    Level 3: Legal action + court filing
                  </div>
                </div>
                {settled ? (
                  <p className="flex items-center gap-2 rounded-xl bg-green-bg px-3 py-2.5 text-xs font-semibold text-green">
                    <Check className="w-3.5 h-3.5 shrink-0" />
                    Settled. The agent has stopped work on this invoice.
                  </p>
                ) : (
                <>
                {agentState.escalation_level < 3 && (
                  <button
                    onClick={handleEscalate}
                    disabled={loading || !!interrupt}
                    className="w-full inline-flex items-center justify-center gap-2 btn-coral text-xs font-bold rounded-xl py-2.5 shadow-card"
                  >
                    <ChevronUp className="w-3.5 h-3.5" />
                    Escalate to {NEXT_LEVEL_NAMES[agentState.escalation_level + 1] ?? `Level ${agentState.escalation_level + 1}`}
                  </button>
                )}
                {confirmingSettle === 'sidebar' ? (
                  <div className="mt-2">{settleConfirmation}</div>
                ) : (
                  <button
                    onClick={() => setConfirmingSettle('sidebar')}
                    disabled={loading}
                    className="mt-2 w-full inline-flex items-center justify-center gap-2 border border-line-2 bg-white hover:bg-green-bg disabled:opacity-50 text-green text-xs font-bold rounded-xl py-2.5 transition-colors"
                  >
                    <Check className="w-3.5 h-3.5" />
                    Mark as settled
                  </button>
                )}
                </>
                )}
              </>
            )}
          </div>
        </div>

        {/* Communication Log */}
        <div className="bg-white border border-gray-200/80 rounded-xl overflow-hidden shadow-card animate-fade-up" style={{ animationDelay: '120ms' }}>
          <div className="bg-tint px-5 py-3 border-b border-line flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-ink flex items-center justify-center">
              <MessageSquare className="w-3 h-3 text-white" />
            </div>
            <h3 className="text-xs font-bold text-gray-600 uppercase tracking-widest">Communication Log</h3>
          </div>
          <div className="p-5">
            {communications.length ? (
              <div className="space-y-3">
                {communications.slice().reverse().map((entry) => {
                  const isInbound = entry.direction === 'inbound'
                  return (
                    <div key={entry.id} className={`text-xs border-l-2 pl-3 py-1.5 ${isInbound ? 'border-ink' : 'border-line-2'}`}>
                      <div className="flex items-center justify-between gap-2">
                        <span className={`font-bold uppercase tracking-wider text-xs ${isInbound ? 'text-ink' : 'text-muted'}`}>
                          {isInbound ? '📩 Client Reply' : `📤 ${entry.type}`}
                        </span>
                        <span className="text-gray-300 text-xs font-medium">
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
    </>
  )
}
