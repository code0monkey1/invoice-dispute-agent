import { DollarSign, AlertTriangle, TrendingUp } from 'lucide-react'
import type { Invoice } from '../types'

export default function StatsCards({ invoices }: { invoices: Invoice[] }) {
  const totalOwed = invoices.reduce((sum, inv) => sum + inv.invoice_amount, 0)
  const activeCount = invoices.filter(inv => inv.status === 'active').length
  const paidCount = invoices.filter(inv => inv.status === 'paid').length
  const recoveryRate = invoices.length > 0
    ? Math.round((paidCount / invoices.length) * 100)
    : 0

  const cards = [
    {
      label: 'Total Outstanding',
      value: `$${totalOwed.toLocaleString('en-US', { minimumFractionDigits: 2 })}`,
      icon: DollarSign,
      gradient: 'from-[#FF6B35] to-[#FF8F65]',
      iconBg: 'bg-orange-100',
      iconColor: 'text-[#FF6B35]',
      shadow: 'shadow-orange-200/50',
      border: 'border-orange-100',
    },
    {
      label: 'Active Disputes',
      value: activeCount.toString(),
      icon: AlertTriangle,
      gradient: 'from-violet-500 to-purple-500',
      iconBg: 'bg-violet-100',
      iconColor: 'text-violet-600',
      shadow: 'shadow-violet-200/50',
      border: 'border-violet-100',
    },
    {
      label: 'Recovery Rate',
      value: `${recoveryRate}%`,
      icon: TrendingUp,
      gradient: 'from-teal-500 to-emerald-500',
      iconBg: 'bg-teal-100',
      iconColor: 'text-teal-600',
      shadow: 'shadow-teal-200/50',
      border: 'border-teal-100',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-5 stagger">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`animate-fade-up card-lift bg-white rounded-2xl p-6 border ${card.border} shadow-sm ${card.shadow} relative overflow-hidden`}
        >
          {/* Decorative gradient strip on top */}
          <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${card.gradient}`} />

          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-medium text-gray-500">{card.label}</span>
            <div className={`w-10 h-10 rounded-xl ${card.iconBg} flex items-center justify-center`}>
              <card.icon className={`w-5 h-5 ${card.iconColor}`} />
            </div>
          </div>
          <p className="text-3xl font-bold text-gray-900 font-[family-name:var(--font-heading)] tracking-tight">
            {card.value}
          </p>
        </div>
      ))}
    </div>
  )
}
