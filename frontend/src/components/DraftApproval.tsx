import { useState, useMemo } from 'react'
import { Check, X, Pencil, FileText, Mail } from 'lucide-react'
import type { Interrupt } from '../types'

interface Props {
  interrupt: Interrupt
  onApprove: () => void
  onReject: (message: string) => void
  onEdit: (editedText: string) => void
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

export default function DraftApproval({ interrupt, onApprove, onReject, onEdit, loading }: Props) {
  const draftContent = interrupt.description || JSON.stringify(interrupt.args, null, 2)
  const parsed = useMemo(() => parseDraft(draftContent), [draftContent])

  const [editing, setEditing] = useState(false)
  const [subject, setSubject] = useState(parsed.subject)
  const [body, setBody] = useState(parsed.body)
  const [senderName, setSenderName] = useState(parsed.senderName)
  const [business, setBusiness] = useState(parsed.business)
  const [email, setEmail] = useState(parsed.email)
  const [rejectReason, setRejectReason] = useState('')
  const [showReject, setShowReject] = useState(false)

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
    onEdit(assembled)
    setEditing(false)
  }

  return (
    <div className="mx-5 my-4 animate-fade-up">
      <div className="bg-white rounded-2xl overflow-hidden border-2 border-amber-200 shadow-lg shadow-amber-100/40">
        {/* Header */}
        <div className="bg-gradient-to-r from-amber-400 to-orange-400 px-5 py-3.5 flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center">
            <Mail className="w-4 h-4 text-white" />
          </div>
          <div className="flex-1">
            <span className="text-sm font-bold text-white font-[family-name:var(--font-heading)]">
              Draft Pending Your Approval
            </span>
            <p className="text-white/70 text-[11px] font-medium">{interrupt.tool}</p>
          </div>
          <FileText className="w-5 h-5 text-white/40" />
        </div>

        {/* Draft Content */}
        <div className="px-5 py-4 bg-gradient-to-b from-amber-50/50 to-white">
          {editing ? (
            <div className="space-y-4">
              {/* Subject */}
              <div>
                <label className="block text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-1.5">Subject</label>
                <input
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="w-full bg-white border border-amber-200 rounded-xl px-4 py-2.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-amber-300"
                />
              </div>
              {/* Body */}
              <div>
                <label className="block text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-1.5">Body</label>
                <textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  className="w-full bg-white border border-amber-200 rounded-xl px-4 py-3 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-amber-300 min-h-[140px] font-mono leading-relaxed"
                />
              </div>
              {/* Signature fields */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-1.5">Sent By</label>
                  <input
                    value={senderName}
                    onChange={(e) => setSenderName(e.target.value)}
                    className="w-full bg-white border border-amber-200 rounded-xl px-4 py-2.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-amber-300"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-1.5">Business</label>
                  <input
                    value={business}
                    onChange={(e) => setBusiness(e.target.value)}
                    className="w-full bg-white border border-amber-200 rounded-xl px-4 py-2.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-amber-300"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-1.5">Email</label>
                  <input
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-white border border-amber-200 rounded-xl px-4 py-2.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-amber-300"
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
        <div className="px-5 py-4 border-t border-amber-100 bg-amber-50/30 space-y-3">
          {editing ? (
            <div className="flex gap-2">
              <button
                onClick={handleSendEdit}
                disabled={loading || !subject.trim() || !body.trim()}
                className="flex-1 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 disabled:opacity-50 text-white text-sm font-bold rounded-xl py-2.5 transition-all shadow-md shadow-amber-200/40"
              >
                Send Edited Version
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
                className="w-full bg-white border border-rose-200 rounded-xl px-4 py-3 text-sm text-gray-800 placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-rose-300"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => { onReject(rejectReason); setShowReject(false) }}
                  disabled={loading}
                  className="flex-1 bg-gradient-to-r from-rose-500 to-red-500 disabled:opacity-50 text-white text-sm font-bold rounded-xl py-2.5 transition-all shadow-md shadow-rose-200/40"
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
                onClick={onApprove}
                disabled={loading}
                className="flex-1 inline-flex items-center justify-center gap-2 bg-gradient-to-r from-emerald-500 to-green-500 hover:from-emerald-600 hover:to-green-600 disabled:opacity-50 text-white text-sm font-bold rounded-xl py-3 transition-all shadow-md shadow-emerald-200/40 font-[family-name:var(--font-heading)]"
              >
                <Check className="w-4 h-4" strokeWidth={3} />
                Approve & Send
              </button>
              <button
                onClick={handleStartEdit}
                disabled={loading}
                className="flex-1 inline-flex items-center justify-center gap-2 bg-gradient-to-r from-amber-400 to-orange-400 hover:from-amber-500 hover:to-orange-500 disabled:opacity-50 text-white text-sm font-bold rounded-xl py-3 transition-all shadow-md shadow-amber-200/40 font-[family-name:var(--font-heading)]"
              >
                <Pencil className="w-4 h-4" />
                Edit Draft
              </button>
              <button
                onClick={() => setShowReject(true)}
                disabled={loading}
                className="flex-1 inline-flex items-center justify-center gap-2 bg-white hover:bg-rose-50 disabled:opacity-50 text-rose-500 text-sm font-bold rounded-xl py-3 transition-all border-2 border-rose-200 font-[family-name:var(--font-heading)]"
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
