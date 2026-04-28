import { useState } from 'react'
import { X, Sparkles } from 'lucide-react'

interface Props {
  open: boolean
  onClose: () => void
  onSubmit: (data: {
    invoice_id: string
    client_name: string
    client_email: string
    invoice_amount: number
    days_overdue: number
    jurisdiction: string
  }) => void
  loading: boolean
  error?: string | null
}

export default function InvoiceForm({ open, onClose, onSubmit, loading, error }: Props) {
  const [form, setForm] = useState({
    invoice_id: '',
    client_name: '',
    client_email: '',
    invoice_amount: '',
    days_overdue: '',
    jurisdiction: '',
  })

  if (!open) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      ...form,
      invoice_amount: parseFloat(form.invoice_amount),
      days_overdue: parseInt(form.days_overdue),
    })
  }

  const fields = [
    { key: 'invoice_id', label: 'Invoice ID', placeholder: 'INV-001', type: 'text' },
    { key: 'client_name', label: 'Client Name', placeholder: 'Acme Corp', type: 'text' },
    { key: 'client_email', label: 'Client Email', placeholder: 'billing@acme.com', type: 'email' },
    { key: 'invoice_amount', label: 'Amount ($)', placeholder: '5000.00', type: 'number' },
    { key: 'days_overdue', label: 'Days Overdue', placeholder: '45', type: 'number' },
    { key: 'jurisdiction', label: 'Jurisdiction', placeholder: 'California', type: 'text' },
  ] as const

  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl w-full max-w-md shadow-2xl shadow-orange-200/30 border border-orange-100/50 animate-fade-up overflow-hidden">
        {/* Header with gradient */}
        <div className="bg-gradient-to-r from-[#FF6B35] to-[#FF8F65] px-6 py-5 relative overflow-hidden">
          <div className="absolute inset-0 opacity-10">
            <div className="absolute -right-8 -top-8 w-32 h-32 rounded-full bg-white/20" />
            <div className="absolute -left-4 -bottom-4 w-20 h-20 rounded-full bg-white/10" />
          </div>
          <div className="flex items-center justify-between relative">
            <div>
              <h2 className="text-lg font-bold text-white font-[family-name:var(--font-heading)]">New Invoice Dispute</h2>
              <p className="text-white/70 text-xs mt-0.5">Enter the overdue invoice details</p>
            </div>
            <button onClick={onClose} className="text-white/60 hover:text-white transition-colors p-1 rounded-lg hover:bg-white/10">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 stagger">
          {fields.map(({ key, label, placeholder, type }) => (
            <div key={key} className="animate-fade-up">
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">{label}</label>
              <input
                type={type}
                required
                placeholder={placeholder}
                value={form[key]}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-800 placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[#FF6B35]/30 focus:border-[#FF6B35]/50 transition-all"
              />
            </div>
          ))}
          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full btn-gradient disabled:opacity-50 text-white font-bold rounded-xl py-3.5 text-sm transition-all flex items-center justify-center gap-2 shadow-lg shadow-orange-300/40 hover:shadow-orange-400/50 mt-3 font-[family-name:var(--font-heading)]"
          >
            <Sparkles className="w-4 h-4" />
            {loading ? 'Creating Dispute...' : 'Start AI-Powered Dispute'}
          </button>
        </form>
      </div>
    </div>
  )
}
