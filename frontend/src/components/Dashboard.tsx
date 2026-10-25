import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Plus, FilePlus2, FileUp, Info, CheckCircle2, Mail } from 'lucide-react'
import StatsCards from './StatsCards'
import InvoiceTable from './InvoiceTable'
import InvoiceForm from './InvoiceForm'
import EscalationBadge from './EscalationBadge'
import { invoiceStatus } from './invoiceStatus'
import { formatMoney } from './format'
import { useInvoices } from '../hooks/useInvoices'
import { useAuth } from '../contexts/AuthContext'
import { usePrefetchHistory } from '../hooks/usePrefetchHistory'
import type { Invoice } from '../types'

const primaryButton =
  'inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-[#FF6B35] to-[#FF8F65] text-white font-semibold text-[15px] px-4 py-2.5 shadow-lg shadow-orange-300/40 hover:from-[#F2551C] hover:to-[#FF6B35]'
const secondaryButton =
  'inline-flex items-center justify-center gap-2 rounded-lg bg-white border border-[#F1E4D8] text-[#111827] font-semibold text-[15px] px-4 py-2.5 hover:border-[#111827]'

// ─── Waiting for you ─────────────────────────────────────────────────────────

function ApprovalQueue({ invoices }: { invoices: Invoice[] }) {
  const waiting = invoices.filter((inv) => invoiceStatus(inv).kind === 'you')
  const prefetch = usePrefetchHistory()

  return (
    <section aria-labelledby="queue-title">
      <h2 id="queue-title" className="text-[20px] font-semibold flex items-center gap-2.5">
        Waiting for you
        {waiting.length > 0 && (
          <span className="rounded-full bg-[#FF6B35] text-white text-[13px] font-semibold px-2 py-0.5 tabular-nums">{waiting.length}</span>
        )}
      </h2>

      {waiting.length === 0 ? (
        <p className="mt-3 flex items-center gap-2.5 text-[16px] text-[#6B7280]">
          <CheckCircle2 className="w-5 h-5 text-[#1F7A55]" />
          Nothing needs you right now. The agent is handling the rest.
        </p>
      ) : (
        <ul className="mt-4 space-y-3">
          {waiting.map((inv) => {
            const status = invoiceStatus(inv)
            const isDraft = inv.pending_action?.startsWith('draft_') ?? true
            return (
              <li
                key={inv.id}
                className="rounded-[14px] bg-white border border-[#FFCFB8] border-l-4 border-l-[#FF6B35] px-5 py-4 grid sm:grid-cols-[1fr_auto] gap-3 sm:gap-6 items-center"
              >
                <div className="min-w-0">
                  <p className="text-[16px] font-semibold">{status.label}</p>
                  <p className="mt-0.5 text-[15px] text-[#6B7280] truncate">
                    <span className="font-medium text-[#374151]">{inv.client_name}</span>
                    {`, ${inv.invoice_id}, ${formatMoney(inv.balance_due ?? inv.invoice_amount)} outstanding`}
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  <EscalationBadge level={inv.escalation_level} />
                  <Link
                    to={`/invoice/${inv.id}`}
                    onMouseEnter={() => prefetch(inv.id)}
                    onFocus={() => prefetch(inv.id)}
                    className={primaryButton}
                  >
                    {isDraft ? 'Review draft' : 'Review'}
                  </Link>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

// ─── First run ───────────────────────────────────────────────────────────────

function EmptyState({ onChase, onCreate }: { onChase: () => void; onCreate: () => void }) {
  return (
    <section className="rounded-[16px] bg-white border border-[#F1E4D8] p-6 sm:p-10 grid lg:grid-cols-[1fr_1fr] gap-8 items-center">
      <div>
        <h2 className="text-[28px] sm:text-[34px] font-bold leading-[1.1] tracking-[-0.02em] max-w-[18ch]">
          Start with the invoice you already sent
        </h2>
        <p className="mt-3 text-[17px] leading-[1.6] text-[#6B7280] max-w-[44ch]">
          Drop in the PDF and the agent fills in the client, amount and due date, then starts chasing. You approve every email before it's sent.
        </p>
        <div className="mt-6 flex flex-col sm:flex-row gap-3">
          <button onClick={onChase} className={primaryButton}>
            <Plus className="w-4 h-4" strokeWidth={2.5} />
            Chase an invoice
          </button>
          <button onClick={onCreate} className={secondaryButton}>
            <FilePlus2 className="w-4 h-4" />
            Create an invoice
          </button>
        </div>
      </div>
      <button
        onClick={onChase}
        className="rounded-[14px] border-2 border-dashed border-[#FF6B35]/50 bg-[#FFFAF5] hover:bg-[#FFF1E6] px-6 py-12 flex flex-col items-center text-center gap-3 transition-colors"
      >
        <span className="w-12 h-12 rounded-[10px] bg-white border border-[#F1E4D8] flex items-center justify-center">
          <FileUp className="w-5 h-5 text-[#FF6B35]" />
        </span>
        <span className="text-[17px] font-semibold">Drop in an invoice PDF</span>
        <span className="text-[14px] text-[#6B7280]">PDF or DOCX, up to 10 MB</span>
      </button>
    </section>
  )
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const { invoices, loading: fetchLoading, createInvoice, settleInvoice } = useInvoices()
  const { user, isGuest, signIn, connectGmail } = useAuth()
  const [formOpen, setFormOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const navigate = useNavigate()

  const firstName = user?.name?.trim().split(/\s+/)[0]

  const openForm = () => {
    setCreateError(null)
    setFormOpen(true)
  }
  const openGenerator = () => navigate('/generate-invoice')

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
      setCreateError(err instanceof Error ? err.message : 'Could not start chasing this invoice.')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="space-y-10">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-[34px] sm:text-[40px] font-bold leading-[1.1] tracking-[-0.025em]">
            {firstName ? `Hi ${firstName}.` : 'Hi there.'}
          </h1>
          <p className="mt-2 text-[17px] text-[#6B7280]">Here's where your invoices stand.</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <button onClick={openForm} className={primaryButton}>
            <Plus className="w-4 h-4" strokeWidth={2.5} />
            Chase an invoice
          </button>
          <button onClick={openGenerator} className={secondaryButton}>
            <FilePlus2 className="w-4 h-4" />
            Create an invoice
          </button>
        </div>
      </header>

      {isGuest && (
        <div className="rounded-[12px] bg-white border border-[#F1E4D8] px-5 py-3.5 flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-6">
          <p className="flex items-start gap-2.5 text-[15px] leading-[1.5] text-[#374151] flex-1">
            <Info className="w-4 h-4 mt-1 shrink-0 text-[#6B7280]" />
            You're trying the demo. Your invoices stay in this browser session, and no emails are sent.
          </p>
          <button onClick={() => signIn()} className={`${secondaryButton} shrink-0`}>
            Sign in with Google to send for real
          </button>
        </div>
      )}

      {!isGuest && user && !user.gmail_connected && (
        <div className="rounded-[12px] bg-white border border-[#F1E4D8] px-5 py-3.5 flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-6">
          <p className="flex items-start gap-2.5 text-[15px] leading-[1.5] text-[#374151] flex-1">
            <Mail className="w-4 h-4 mt-1 shrink-0 text-[#6B7280]" />
            Connect Gmail so approved emails go out from your own address. InvoiceChaser only asks permission to send, never to read your inbox.
          </p>
          <button onClick={() => connectGmail()} className={`${primaryButton} shrink-0`}>
            Connect Gmail
          </button>
        </div>
      )}

      {fetchLoading ? (
        <div className="py-16 text-center" role="status">
          <div className="w-8 h-8 mx-auto mb-3 rounded-full border-2 border-[#F1E4D8] border-t-[#FF6B35] animate-spin motion-reduce:animate-none" />
          <p className="text-[15px] text-[#6B7280]">Loading your invoices…</p>
        </div>
      ) : invoices.length === 0 ? (
        <EmptyState onChase={openForm} onCreate={openGenerator} />
      ) : (
        <>
          <ApprovalQueue invoices={invoices} />
          <StatsCards invoices={invoices} />
          <InvoiceTable invoices={invoices} onSettle={settleInvoice} />
        </>
      )}

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
