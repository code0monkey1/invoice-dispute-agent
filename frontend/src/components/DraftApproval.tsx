import { useState, useMemo } from 'react'
import { Check, X, Pencil, FileText, Mail, CreditCard, Clock } from 'lucide-react'
import type { Interrupt } from '../types'

// Header colours come from the status pairs: green only for paid, neutral otherwise.
const PAYMENT_TOOLS: Record<string, { label: string; description: string; icon: React.ReactNode; header: string }> = {
  mark_invoice_paid: {
    label: 'Mark Invoice as Paid',
    description: 'This will mark the invoice as fully paid and close the dispute.',
    icon: <CreditCard className="w-4 h-4" />,
    header: 'bg-green-bg text-green',
  },
  mark_invoice_pending: {
    label: 'Mark Invoice as Pending',
    description: 'This will mark the invoice as pending — client has agreed to pay.',
    icon: <Clock className="w-4 h-4" />,
    header: 'bg-tint text-ink',
  },
  record_partial_payment: {
    label: 'Record Partial Payment',
    description: 'This will reduce the remaining balance and continue the dispute if money is still owed.',
    icon: <CreditCard className="w-4 h-4" />,
    header: 'bg-tint text-ink',
  },
}

interface Props {
  interrupt: Interrupt
  onApprove: (approvedDraft?: string) => void
  onReject: (message: string) => void
  loading: boolean
}

/** Parse a draft email string into editable sections. */
function parseDraft(raw: string) {
  let subject = ''
  let body = ''
  let senderName = ''
  let business = ''
  let email = ''

  // Extract subject line
  const subjectMatch = raw.match(/^Subject:\s*(.+)/m)
  if (subjectMatch) {
    subject = subjectMatch[1].trim()
  }

  // Everything after "Subject: ...\n\n" is the rest
  const afterSubject = raw.replace(/^Subject:\s*.+\n\n?/, '')

  // Split off the signature block (last lines after the closing like "Best regards," / "Sincerely,")
  const closingPatterns = /\n(Best regards|Sincerely|Regards|Respectfully|Thank you),?\n/i
  const closingMatch = afterSubject.match(closingPatterns)

  if (closingMatch && closingMatch.index !== undefined) {
    body = afterSubject.slice(0, closingMatch.index + closingMatch[0].length).trim()
    const signatureBlock = afterSubject.slice(closingMatch.index + closingMatch[0].length).trim()
    const sigLines = signatureBlock.split('\n').map(l => l.trim()).filter(Boolean)

    // Signature lines: name, business, email (in order, email detected by @)
    for (const line of sigLines) {
      if (line.includes('@') && !email) {
        email = line
      } else if (!senderName) {
        senderName = line
      } else if (!business) {
        business = line
      }
    }
  } else {
    // No closing pattern found — try to split by last lines with @
    const lines = afterSubject.trim().split('\n')
    const sigStart = lines.findIndex(l => l.trim().includes('@'))
    if (sigStart > 0) {
      // Assume 1-3 lines before the email line are the signature
      const start = Math.max(0, sigStart - 2)
      body = lines.slice(0, start).join('\n').trim()
      const sigLines = lines.slice(start).map(l => l.trim()).filter(Boolean)
      for (const line of sigLines) {
        if (line.includes('@') && !email) {
          email = line
        } else if (!senderName) {
          senderName = line
        } else if (!business) {
          business = line
        }
      }
    } else {
      body = afterSubject.trim()
    }
  }

  return { subject, body, senderName, business, email }
}

function reassemble(parts: { subject: string; body: string; senderName: string; business: string; email: string }) {
  let result = `Subject: ${parts.subject}\n\n${parts.body}`
  const sig = [parts.senderName, parts.business, parts.email].filter(Boolean).join('\n')
  if (sig) {
    // If body already ends with a closing line, don't double-add
    if (!/,\s*$/.test(parts.body)) {
      result += '\n'
    }
    result += '\n' + sig
  }
  return result
}

export default function DraftApproval({ interrupt, onApprove, onReject, loading }: Props) {
  const paymentAction = PAYMENT_TOOLS[interrupt.tool]
  const initialDraft = interrupt.description || JSON.stringify(interrupt.args, null, 2)
  const [draftContent, setDraftContent] = useState(initialDraft)
  const parsed = useMemo(() => parseDraft(draftContent), [draftContent])

  const [editing, setEditing] = useState(false)
  const [subject, setSubject] = useState(parsed.subject)
  const [body, setBody] = useState(parsed.body)
  const [senderName, setSenderName] = useState(parsed.senderName)
  const [business, setBusiness] = useState(parsed.business)
  const [email, setEmail] = useState(parsed.email)
  const [rejectReason, setRejectReason] = useState('')
  const [showReject, setShowReject] = useState(false)

  // A new draft arrived: start over from it (adjusting state while rendering
  // instead of in an effect, so there's no extra render with the stale draft).
  const [shownDraft, setShownDraft] = useState(initialDraft)
  if (shownDraft !== initialDraft) {
    setShownDraft(initialDraft)
    setDraftContent(initialDraft)
    setEditing(false)
    setShowReject(false)
  }

  const handleStartEdit = () => {
    setSubject(parsed.subject)
    setBody(parsed.body)
    setSenderName(parsed.senderName)
    setBusiness(parsed.business)
    setEmail(parsed.email)
    setEditing(true)
  }

  const handleSendEdit = () => {
    const assembled = reassemble({ subject, body, senderName, business, email })
    setDraftContent(assembled)
    setEditing(false)
  }

  // Payment action confirmation card
  if (paymentAction) {
    return (
      <div className="mx-5 my-4 animate-fade-up">
        <div className="bg-white rounded-xl overflow-hidden border-2 border-line shadow-card">
          <div className={`${paymentAction.header} px-5 py-3.5 flex items-center gap-2.5`}>
            <div className="w-8 h-8 rounded-lg bg-white/60 flex items-center justify-center">
              {paymentAction.icon}
            </div>
            <div className="flex-1">
              <span className="text-sm font-bold">
                Action Required
              </span>
              <p className="text-xs font-medium">{paymentAction.label}</p>
            </div>
          </div>
          <div className="px-5 py-4">
            <p className="text-sm text-gray-600">{paymentAction.description}</p>
            {interrupt.args?.follow_up_date != null && (
              <p className="text-xs text-gray-400 mt-1">Follow-up: {String(interrupt.args.follow_up_date)}</p>
            )}
            {interrupt.args?.amount_paid != null && (
              <p className="text-xs text-gray-400 mt-1">Payment: ${String(interrupt.args.amount_paid)}</p>
            )}
            {interrupt.args?.payment_date != null && (
              <p className="text-xs text-gray-400 mt-1">Date: {String(interrupt.args.payment_date)}</p>
            )}
          </div>
          <div className="px-5 py-4 border-t border-gray-100 flex gap-3">
            <button
              onClick={() => onApprove()}
              disabled={loading}
              className="btn-coral flex-1 inline-flex items-center justify-center gap-2 text-sm font-bold rounded-xl py-3 shadow-card"
            >
              <Check className="w-4 h-4" strokeWidth={3} /> Confirm
            </button>
            <button
              onClick={() => onReject('Not now')}
              disabled={loading}
              className="flex-1 inline-flex items-center justify-center gap-2 bg-white hover:bg-red-bg disabled:opacity-50 text-red text-sm font-bold rounded-xl py-3 border-2 border-line-2 transition-all"
            >
              <X className="w-4 h-4" strokeWidth={3} /> Dismiss
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-5 my-4 animate-fade-up">
      <div className="bg-white rounded-xl overflow-hidden border-2 border-line-2 shadow-card">
        {/* Header */}
        <div className="bg-tint border-b border-line px-5 py-3.5 flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-coral flex items-center justify-center">
            <Mail className="w-4 h-4 text-ink" />
          </div>
          <div className="flex-1">
            <span className="text-sm font-bold text-coral-text">
              Draft Pending Your Approval
            </span>
          </div>
          <FileText className="w-5 h-5 text-muted" />
        </div>

        {interrupt.notes && interrupt.notes.length > 0 && (
          <aside aria-label="Before sending" className="px-5 py-3 border-b border-line bg-amber-bg">
            <p className="text-xs font-bold text-amber uppercase tracking-wider">Before sending</p>
            <ul className="mt-2 space-y-1 list-disc pl-4 text-xs text-amber leading-relaxed">
              {interrupt.notes.map((note, index) => <li key={index}>{note}</li>)}
            </ul>
          </aside>
        )}

        {/* Draft Content */}
        <div className="px-5 py-4 bg-card">
          {editing ? (
            <div className="space-y-4">
              {/* Subject */}
              <div>
                <label className="block text-xs font-bold text-muted uppercase tracking-wider mb-1.5">Subject</label>
                <input
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="w-full bg-white border border-line-2 rounded-xl px-4 py-2.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-coral"
                />
              </div>
              {/* Body */}
              <div>
                <label className="block text-xs font-bold text-muted uppercase tracking-wider mb-1.5">Body</label>
                <textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  className="w-full bg-white border border-line-2 rounded-xl px-4 py-3 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-coral min-h-[140px] font-mono leading-relaxed"
                />
              </div>
              {/* Signature fields */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-bold text-muted uppercase tracking-wider mb-1.5">Sent By</label>
                  <input
                    value={senderName}
                    onChange={(e) => setSenderName(e.target.value)}
                    className="w-full bg-white border border-line-2 rounded-xl px-4 py-2.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-coral"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-muted uppercase tracking-wider mb-1.5">Business</label>
                  <input
                    value={business}
                    onChange={(e) => setBusiness(e.target.value)}
                    className="w-full bg-white border border-line-2 rounded-xl px-4 py-2.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-coral"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-muted uppercase tracking-wider mb-1.5">Email</label>
                  <input
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-white border border-line-2 rounded-xl px-4 py-2.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-coral"
                  />
                </div>
              </div>
            </div>
          ) : (
            <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono leading-relaxed">
              {draftContent}
            </pre>
          )}
        </div>

        {/* Actions */}
        <div className="px-5 py-4 border-t border-line bg-tint space-y-3">
          {editing ? (
            <div className="flex gap-2">
              <button
                onClick={handleSendEdit}
                disabled={loading || !subject.trim() || !body.trim()}
                className="btn-coral flex-1 text-sm font-bold rounded-xl py-2.5 shadow-card"
              >
                Save Edits
              </button>
              <button
                onClick={() => setEditing(false)}
                className="px-4 text-gray-400 hover:text-gray-600 text-sm font-medium transition-colors"
              >
                Cancel
              </button>
            </div>
          ) : showReject ? (
            <div className="space-y-3">
              <input
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Reason for rejection (optional)..."
                className="w-full bg-white border border-line-2 rounded-xl px-4 py-3 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-coral"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => { onReject(rejectReason); setShowReject(false) }}
                  disabled={loading}
                  className="flex-1 bg-red disabled:opacity-50 text-white text-sm font-bold rounded-xl py-2.5 transition-all shadow-card"
                >
                  Confirm Rejection
                </button>
                <button
                  onClick={() => setShowReject(false)}
                  className="px-4 text-gray-400 hover:text-gray-600 text-sm font-medium transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex gap-3">
              <button
                onClick={() => onApprove(draftContent)}
                disabled={loading}
                className="flex-1 btn-coral inline-flex items-center justify-center gap-2 text-sm font-bold rounded-xl py-3 shadow-card"
              >
                <Check className="w-4 h-4" strokeWidth={3} />
                Approve & Send
              </button>
              <button
                onClick={handleStartEdit}
                disabled={loading}
                className="flex-1 inline-flex items-center justify-center gap-2 bg-white hover:bg-tint disabled:opacity-50 disabled:cursor-not-allowed text-ink text-sm font-bold rounded-xl py-3 border-2 border-line-2 transition-all"
              >
                <Pencil className="w-4 h-4" />
                Edit Draft
              </button>
              <button
                onClick={() => setShowReject(true)}
                disabled={loading}
                className="flex-1 inline-flex items-center justify-center gap-2 bg-white hover:bg-red-bg disabled:opacity-50 disabled:cursor-not-allowed text-red text-sm font-bold rounded-xl py-3 transition-all border-2 border-line-2"
              >
                <X className="w-4 h-4" strokeWidth={3} />
                Reject
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
