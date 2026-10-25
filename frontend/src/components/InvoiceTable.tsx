import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import EscalationBadge from './EscalationBadge'
import { invoiceStatus } from './invoiceStatus'
import type { InvoiceStatusKind } from './invoiceStatus'
import { formatMoney, formatOverdue } from './format'
import type { Invoice } from '../types'

type Filter = 'all' | 'you' | 'active' | 'paid'

const FILTERS: { id: Filter; label: string; match: (kind: InvoiceStatusKind) => boolean }[] = [
  { id: 'all', label: 'All', match: () => true },
  { id: 'you', label: 'Waiting for you', match: (k) => k === 'you' },
  { id: 'active', label: 'Being chased', match: (k) => k === 'agent' || k === 'client' },
  { id: 'paid', label: 'Paid', match: (k) => k === 'paid' },
]

const STATUS_STYLE: Record<InvoiceStatusKind, { dot: string; text: string }> = {
  you: { dot: 'bg-[#FF6B35]', text: 'text-[#B4410E] font-semibold' },
  client: { dot: 'bg-[#111827]', text: 'text-[#111827] font-semibold' },
  agent: { dot: 'bg-[#C9B8A6]', text: 'text-[#6B7280]' },
  paid: { dot: 'bg-[#1F7A55]', text: 'text-[#1F7A55] font-semibold' },
}

export default function InvoiceTable({ invoices }: { invoices: Invoice[] }) {
  const navigate = useNavigate()
  const [filter, setFilter] = useState<Filter>('all')

  const rows = invoices.map((inv) => ({ inv, status: invoiceStatus(inv) }))
  const active = FILTERS.find((f) => f.id === filter) ?? FILTERS[0]
  const visible = rows.filter((r) => active.match(r.status.kind))

  return (
    <section aria-labelledby="invoices-title">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h2 id="invoices-title" className="text-[20px] font-semibold">Invoices</h2>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter invoices">
          {FILTERS.map((f) => {
            const count = rows.filter((r) => f.match(r.status.kind)).length
            const selected = f.id === filter
            return (
              <button
                key={f.id}
                onClick={() => setFilter(f.id)}
                aria-pressed={selected}
                className={`rounded-full px-3.5 py-1.5 text-[14px] font-semibold border transition-colors ${
                  selected ? 'bg-[#111827] text-white border-[#111827]' : 'bg-white border-[#F1E4D8] text-[#374151] hover:border-[#111827]'
                }`}
              >
                {f.label} <span className={`tabular-nums ${selected ? 'text-white/70' : 'text-[#6B7280]'}`}>{count}</span>
              </button>
            )
          })}
        </div>
      </div>

      <div className="mt-4 rounded-[16px] bg-white border border-[#F1E4D8] overflow-hidden">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-[#F1E4D8] text-[14px] text-[#6B7280]">
              <th className="font-medium px-5 py-3">Client</th>
              <th className="font-medium px-5 py-3 hidden md:table-cell">Invoice</th>
              <th className="font-medium px-5 py-3 text-right">Balance</th>
              <th className="font-medium px-5 py-3 text-right hidden md:table-cell">Overdue</th>
              <th className="font-medium px-5 py-3 hidden lg:table-cell">Tone</th>
              <th className="font-medium px-5 py-3 hidden sm:table-cell">Status</th>
              <th className="px-3 py-3 w-8"><span className="sr-only">Open</span></th>
            </tr>
          </thead>
          <tbody>
            {visible.map(({ inv, status }) => {
              const style = STATUS_STYLE[status.kind]
              return (
                <tr
                  key={inv.id}
                  onClick={() => navigate(`/invoice/${inv.id}`)}
                  className="border-b last:border-b-0 border-[#F6EDE3] hover:bg-[#FFFAF5] cursor-pointer group"
                >
                  <td className="px-5 py-4">
                    <Link
                      to={`/invoice/${inv.id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="text-[16px] font-semibold hover:underline underline-offset-4"
                    >
                      {inv.client_name}
                    </Link>
                    <p className="text-[14px] text-[#6B7280] truncate max-w-[26ch]">{inv.client_email}</p>
                    <p className={`sm:hidden mt-1 text-[14px] flex items-center gap-1.5 ${style.text}`}>
                      <span className={`w-2 h-2 rounded-full ${style.dot}`} />
                      {status.label}
                    </p>
                  </td>
                  <td className="px-5 py-4 hidden md:table-cell text-[15px] text-[#374151] tabular-nums">{inv.invoice_id || inv.id}</td>
                  <td className="px-5 py-4 text-right">
                    <span className="text-[16px] font-semibold tabular-nums">{formatMoney(inv.balance_due ?? inv.invoice_amount)}</span>
                    {inv.amount_paid > 0 && (
                      <p className="text-[13px] text-[#6B7280] tabular-nums">{formatMoney(inv.amount_paid)} paid</p>
                    )}
                  </td>
                  <td className="px-5 py-4 text-right hidden md:table-cell text-[15px] text-[#374151] tabular-nums">
                    {formatOverdue(inv.days_overdue)}
                  </td>
                  <td className="px-5 py-4 hidden lg:table-cell">
                    <EscalationBadge level={inv.escalation_level} />
                  </td>
                  <td className="px-5 py-4 hidden sm:table-cell">
                    <span className={`inline-flex items-center gap-2 text-[15px] ${style.text}`}>
                      <span className={`w-2 h-2 rounded-full shrink-0 ${style.dot}`} />
                      {status.label}
                    </span>
                  </td>
                  <td className="px-3 py-4 text-[#C9B8A6] group-hover:text-[#111827]">
                    <ChevronRight className="w-5 h-5" />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {visible.length === 0 && (
          <p className="px-5 py-8 text-center text-[15px] text-[#6B7280]">No invoices here.</p>
        )}
      </div>
    </section>
  )
}
