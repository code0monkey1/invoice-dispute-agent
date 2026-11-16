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
                      onClick={saveDetails}
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
                  onClick={startEditingSender}
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
                      onClick={saveSender}
                      disabled={savingSender || !senderName.trim()}
                      className="flex-1 inline-flex items-center justify-center gap-1.5 bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600 hover:to-indigo-600 disabled:opacity-50 text-white text-xs font-bold rounded-lg py-2 transition-all"
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
                    Level 2: Formal demands
                  </div>
                  <div className={`flex items-center gap-2.5 font-medium ${agentState.escalation_level >= 3 ? 'text-rose-600' : 'text-gray-300'}`}>
                    <span className={`w-2.5 h-2.5 rounded-full ${agentState.escalation_level >= 3 ? 'bg-gradient-to-br from-rose-400 to-red-500 shadow-sm shadow-rose-200' : 'bg-gray-200'}`} />
                    Level 3: Legal action + court filing
                  </div>
                </div>
                {settled ? (
                  <p className="flex items-center gap-2 rounded-xl bg-emerald-50 px-3 py-2.5 text-xs font-semibold text-emerald-700">
                    <Check className="w-3.5 h-3.5 shrink-0" />
                    Settled. The agent has stopped work on this invoice.
                  </p>
                ) : (
                <>
                {agentState.escalation_level < 3 && (
                  <button
                    onClick={handleEscalate}
                    disabled={loading || !!interrupt}
                    className="w-full inline-flex items-center justify-center gap-2 bg-gradient-to-r from-violet-500 to-purple-500 hover:from-violet-600 hover:to-purple-600 disabled:opacity-50 text-white text-xs font-bold rounded-xl py-2.5 transition-all shadow-md shadow-violet-200/40 font-[family-name:var(--font-heading)]"
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
                    className="mt-2 w-full inline-flex items-center justify-center gap-2 border border-emerald-200 bg-white hover:bg-emerald-50 disabled:opacity-50 text-emerald-700 text-xs font-bold rounded-xl py-2.5 transition-colors"
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
    </>
  )
}
