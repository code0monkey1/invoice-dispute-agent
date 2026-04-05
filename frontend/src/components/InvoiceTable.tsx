import { useNavigate } from 'react-router-dom'
import { MessageSquare, ArrowRight } from 'lucide-react'
import EscalationBadge from './EscalationBadge'
import type { Invoice } from '../types'

export default function InvoiceTable({ invoices }: { invoices: Invoice[] }) {
  const navigate = useNavigate()

  if (invoices.length === 0) {
    return (
      <div className="bg-white border border-orange-100 rounded-2xl p-16 text-center animate-fade-up">
        <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-orange-50 flex items-center justify-center">
          <MessageSquare className="w-7 h-7 text-orange-300" />
        </div>
        <p className="text-gray-400 text-lg font-medium font-[family-name:var(--font-heading)]">
          No invoices yet
        </p>
        <p className="text-gray-400/70 text-sm mt-1">
          Click "New Invoice" to start chasing a payment
        </p>
      </div>
    )
  }

  return (
    <div className="bg-white border border-gray-200/80 rounded-2xl overflow-hidden shadow-sm animate-fade-up">
      <table className="w-full">
        <thead>
          <tr className="bg-gradient-to-r from-gray-50/80 to-orange-50/30 border-b border-gray-100">
            <th className="text-left px-6 py-3.5 text-[11px] font-bold text-gray-400 uppercase tracking-widest">Invoice</th>
            <th className="text-left px-6 py-3.5 text-[11px] font-bold text-gray-400 uppercase tracking-widest">Client</th>
            <th className="text-right px-6 py-3.5 text-[11px] font-bold text-gray-400 uppercase tracking-widest">Amount</th>
            <th className="text-right px-6 py-3.5 text-[11px] font-bold text-gray-400 uppercase tracking-widest">Overdue</th>
            <th className="text-left px-6 py-3.5 text-[11px] font-bold text-gray-400 uppercase tracking-widest">Level</th>
            <th className="text-center px-6 py-3.5 text-[11px] font-bold text-gray-400 uppercase tracking-widest"></th>
          </tr>
        </thead>
        <tbody>
          {invoices.map((inv, i) => (
            <tr
              key={inv.id}
              className="border-b border-gray-50 hover:bg-orange-50/40 transition-colors cursor-pointer group"
              onClick={() => navigate(`/invoice/${inv.id}`)}
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <td className="px-6 py-4">
                <span className="font-mono text-sm font-semibold text-gray-800 bg-gray-100 px-2 py-0.5 rounded-md">
                  {inv.id}
                </span>
              </td>
              <td className="px-6 py-4">
                <div>
                  <p className="text-sm font-semibold text-gray-800">{inv.client_name}</p>
                  <p className="text-xs text-gray-400">{inv.client_email}</p>
                </div>
              </td>
              <td className="px-6 py-4 text-right">
                <span className="text-sm font-bold text-gray-900 font-[family-name:var(--font-heading)]">
                  ${inv.invoice_amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </span>
              </td>
              <td className="px-6 py-4 text-right">
                <span className="text-sm font-bold text-rose-500 bg-rose-50 px-2 py-0.5 rounded-md">
                  {inv.days_overdue}d
                </span>
              </td>
              <td className="px-6 py-4">
                <EscalationBadge level={inv.escalation_level} />
              </td>
              <td className="px-6 py-4 text-center">
                <span className="inline-flex items-center gap-1 text-xs font-semibold text-[#FF6B35] opacity-0 group-hover:opacity-100 transition-opacity">
                  Open <ArrowRight className="w-3 h-3" />
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
