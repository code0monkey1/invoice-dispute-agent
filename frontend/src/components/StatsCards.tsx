import type { Invoice } from '../types'
import { formatMoney } from './format'

// One quiet line of figures; the "Waiting for you" queue above is the focus.
export default function StatsCards({ invoices }: { invoices: Invoice[] }) {
  const open = invoices.filter((inv) => inv.status !== 'paid')
  const outstanding = open.reduce((sum, inv) => sum + (inv.balance_due ?? inv.invoice_amount), 0)
  const paidCount = invoices.length - open.length

  const figures = [
    { label: 'Outstanding', value: formatMoney(outstanding) },
    { label: 'Being chased', value: String(open.length) },
    { label: 'Collected', value: `${paidCount} of ${invoices.length}` },
  ]

  return (
    <dl className="grid grid-cols-1 sm:grid-cols-3 border-y border-[#F1E4D8] divide-y sm:divide-y-0 sm:divide-x divide-[#F1E4D8]">
      {figures.map((f) => (
        <div key={f.label} className="py-5 sm:px-6 sm:first:pl-0">
          <dt className="text-[15px] text-[#6B7280]">{f.label}</dt>
          <dd className="mt-1 text-[28px] font-bold tracking-[-0.02em] tabular-nums">{f.value}</dd>
        </div>
      ))}
    </dl>
  )
}
