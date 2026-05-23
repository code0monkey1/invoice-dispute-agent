import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Sparkles, Info, FileText } from 'lucide-react'
import StatsCards from './StatsCards'
import InvoiceTable from './InvoiceTable'
import InvoiceForm from './InvoiceForm'
import TelegramConnect from './TelegramConnect'
import { useInvoices } from '../hooks/useInvoices'
import { useAuth } from '../contexts/AuthContext'

export default function Dashboard() {
  const { invoices, loading: fetchLoading, createInvoice } = useInvoices()
  const { user, isGuest, signIn } = useAuth()
  const [formOpen, setFormOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const navigate = useNavigate()

  const handleCreate = async (data: {
    invoice_id: string
    client_name: string
    client_email: string
    invoice_amount: number
    amount_paid?: number
    days_overdue: number
    jurisdiction: string
  }, file?: File) => {
    setCreating(true)
    setCreateError(null)
    try {
      const res = await createInvoice(data, file)
      setFormOpen(false)
      navigate(`/invoice/${res.invoice.id}`)
    } catch (err) {
      console.error('Failed to create invoice:', err)
      setCreateError(err instanceof Error ? err.message : 'Could not create the dispute.')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="space-y-8">
      {/* Hero Header */}
      <div className="flex items-end justify-between animate-fade-up">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-violet-600 bg-violet-50 px-3 py-1 rounded-full border border-violet-100">
              <Sparkles className="w-3 h-3" />
              AI-Powered
            </span>
          </div>
          <h2 className="text-3xl font-extrabold text-gray-900 font-[family-name:var(--font-heading)] tracking-tight">
            Payment Recovery Dashboard
          </h2>
          <p className="text-sm text-gray-400 mt-1.5 font-medium">
            Track, escalate, and resolve overdue invoice disputes with AI assistance
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/generate-invoice')}
            className="inline-flex items-center gap-2 text-white font-bold rounded-xl px-5 py-3 text-sm transition-all bg-violet-600 hover:bg-violet-700 shadow-lg shadow-violet-300/40 hover:shadow-violet-400/50 font-[family-name:var(--font-heading)]"
          >
            <FileText className="w-4 h-4" strokeWidth={3} />
            Generate Invoice
          </button>
          <button
            onClick={() => {
              setCreateError(null)
              setFormOpen(true)
            }}
            className="btn-gradient inline-flex items-center gap-2 text-white font-bold rounded-xl px-5 py-3 text-sm transition-all shadow-lg shadow-orange-300/40 hover:shadow-orange-400/50 font-[family-name:var(--font-heading)]"
          >
            <Plus className="w-4 h-4" strokeWidth={3} />
            Chase Existing
          </button>
        </div>
      </div>

      {/* Guest-mode banner — visible only when running without Google sign-in */}
      {isGuest && (
        <div className="bg-gradient-to-r from-violet-50 to-orange-50 border border-violet-200/60 rounded-2xl p-4 flex items-start gap-3">
          <div className="w-9 h-9 rounded-xl bg-white border border-violet-200 flex items-center justify-center text-violet-600 shrink-0">
            <Info className="w-4 h-4" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-bold text-gray-900">
              You're in demo mode{user?.name ? `, ${user.name}` : ''}.
            </p>
            <p className="text-xs text-gray-600 mt-0.5">
              Create invoices, chat with the AI agent, and review escalation drafts — all your data is private to this browser session. To actually send emails from your Gmail and get Telegram alerts, sign in with Google.
            </p>
          </div>
          <button
            onClick={() => signIn()}
            className="shrink-0 text-xs font-bold text-white bg-gray-900 hover:bg-gray-800 px-3 py-2 rounded-lg transition"
          >
            Sign in
          </button>
        </div>
      )}

      {/* Stats */}
      <StatsCards invoices={invoices} />

      {/* Telegram connect — real users only (guests can't connect Telegram without auth) */}
      {user && !isGuest && <TelegramConnect />}

      {/* Table */}
      <div>
        <div className="flex items-center gap-3 mb-4">
          <h3 className="text-sm font-bold text-gray-500 uppercase tracking-widest font-[family-name:var(--font-heading)]">
            Active Disputes
          </h3>
          <div className="flex-1 h-px bg-gradient-to-r from-gray-200 to-transparent" />
        </div>
        {fetchLoading ? (
          <div className="bg-white border border-gray-100 rounded-2xl p-16 text-center">
            <div className="w-8 h-8 mx-auto mb-3 rounded-full border-2 border-orange-200 border-t-[#FF6B35] animate-spin" />
            <p className="text-gray-400 font-medium">Loading invoices...</p>
          </div>
        ) : (
          <InvoiceTable invoices={invoices} />
        )}
      </div>

      {/* Form Modal */}
      <InvoiceForm
        open={formOpen}
        onClose={() => {
          setCreateError(null)
          setFormOpen(false)
        }}
        onSubmit={handleCreate}
        loading={creating}
        error={createError}
      />
    </div>
  )
}
