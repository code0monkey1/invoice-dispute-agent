import { useState } from 'react'
import { Check, X, Pencil, FileText, Mail } from 'lucide-react'
import type { Interrupt } from '../types'

interface Props {
  interrupt: Interrupt
  onApprove: () => void
  onReject: (message: string) => void
  onEdit: (editedText: string) => void
  loading: boolean
}

export default function DraftApproval({ interrupt, onApprove, onReject, onEdit, loading }: Props) {
  const [editing, setEditing] = useState(false)
  const [editText, setEditText] = useState('')
  const [rejectReason, setRejectReason] = useState('')
  const [showReject, setShowReject] = useState(false)

  const draftContent = interrupt.description || JSON.stringify(interrupt.args, null, 2)

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
          <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono leading-relaxed">
            {draftContent}
          </pre>
        </div>

        {/* Actions */}
        <div className="px-5 py-4 border-t border-amber-100 bg-amber-50/30 space-y-3">
          {editing ? (
            <div className="space-y-3">
              <textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                placeholder="Enter your edited version..."
                className="w-full bg-white border border-amber-200 rounded-xl px-4 py-3 text-sm text-gray-800 placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-amber-300 min-h-[120px] font-mono"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => { onEdit(editText); setEditing(false) }}
                  disabled={loading || !editText.trim()}
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
                onClick={() => setEditing(true)}
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
