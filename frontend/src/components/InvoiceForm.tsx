import { useRef, useState } from 'react'
import { AlertCircle, FileText, Sparkles, Upload, X } from 'lucide-react'
import { useInvoiceFiles } from '../hooks/useInvoiceFiles'

interface Props {
  open: boolean
  onClose: () => void
  onSubmit: (data: {
    invoice_id: string
    client_name: string
    client_email: string
    invoice_amount: number
    amount_paid?: number
    days_overdue: number
    jurisdiction: string
  }, file?: File) => void
  loading: boolean
  error?: string | null
}

const emptyForm = {
  invoice_id: '',
  client_name: '',
  client_email: '',
  invoice_amount: '',
  amount_paid: '0',
  days_overdue: '',
  jurisdiction: '',
}

export default function InvoiceForm({ open, onClose, onSubmit, loading, error }: Props) {
  const { parse } = useInvoiceFiles()
  const [form, setForm] = useState(emptyForm)
  const [uploadedFile, setUploadedFile] = useState<File | undefined>()
  const [parsing, setParsing] = useState(false)
  const [parseError, setParseError] = useState<string | null>(null)
  const [parseWarnings, setParseWarnings] = useState<string[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  if (!open) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      invoice_id: form.invoice_id.trim(),
      client_name: form.client_name.trim(),
      client_email: form.client_email.trim(),
      invoice_amount: parseFloat(form.invoice_amount),
      amount_paid: parseFloat(form.amount_paid || '0') || 0,
      days_overdue: parseInt(form.days_overdue),
      jurisdiction: form.jurisdiction.trim(),
    }, uploadedFile)
  }

  const handleFile = async (file: File) => {
    setUploadedFile(file)
    setParsing(true)
    setParseError(null)
    setParseWarnings([])
    try {
      const parsed = await parse(file)
      const extracted = parsed.extracted
      setForm(current => ({
        ...current,
        invoice_id: extracted.invoice_id || current.invoice_id,
        client_name: extracted.client_name || current.client_name,
        client_email: extracted.client_email || current.client_email,
        invoice_amount: extracted.invoice_amount != null ? String(extracted.invoice_amount) : current.invoice_amount,
        days_overdue: extracted.days_overdue != null ? String(extracted.days_overdue) : current.days_overdue,
        jurisdiction: extracted.jurisdiction || current.jurisdiction,
      }))
      setParseWarnings(parsed.warnings || [])
    } catch (err) {
      setUploadedFile(undefined)
      setParseError(err instanceof Error ? err.message : 'Could not read this invoice.')
    } finally {
      setParsing(false)
    }
  }

  const fields = [
    { key: 'invoice_id', label: 'Invoice ID', placeholder: 'e.g. INV-001', type: 'text', required: true },
    { key: 'client_name', label: 'Client Name', placeholder: 'e.g. Acme Corp', type: 'text', required: true },
    { key: 'client_email', label: 'Client Email', placeholder: 'e.g. billing@acme.com', type: 'email', required: true },
    { key: 'invoice_amount', label: 'Invoice total ($)', placeholder: 'e.g. 5000.00', type: 'number', required: true },
    { key: 'amount_paid', label: 'Already paid ($)', placeholder: 'e.g. 0.00', type: 'number', required: false },
    { key: 'days_overdue', label: 'Days Overdue', placeholder: 'e.g. 45', type: 'number', required: true },
    { key: 'jurisdiction', label: 'Client location (for legal notices)', placeholder: 'e.g. California', type: 'text', required: true },
  ] as const

  return (
    <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl w-full max-w-lg shadow-pop border border-line animate-fade-up overflow-hidden">
        <div className="px-6 pt-6 pb-4 border-b border-line flex items-start justify-between gap-4">
          <div>
            <h2 className="text-[20px] font-bold text-ink">Chase an invoice</h2>
            <p className="text-[14px] text-muted mt-1">Upload the invoice, or enter the details yourself.</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close" className="text-muted hover:text-ink transition-colors p-2.5 -m-2.5 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 max-h-[78vh] overflow-y-auto">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) void handleFile(file)
            }}
          />

          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={parsing || loading}
            className="w-full border-2 border-dashed border-orange-200 bg-orange-50/50 hover:bg-orange-50 disabled:opacity-60 rounded-xl px-4 py-4 text-left transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-white border border-orange-100 flex items-center justify-center">
                {uploadedFile ? <FileText className="w-5 h-5 text-coral-text" /> : <Upload className="w-5 h-5 text-coral-text" />}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-bold text-ink">
                  {uploadedFile ? uploadedFile.name : 'Upload PDF or DOCX invoice'}
                </p>
                <p className="text-xs text-muted mt-0.5">
                  {parsing ? 'Reading invoice...' : 'Extracted fields can be reviewed before creating the dispute'}
                </p>
              </div>
            </div>
          </button>

          {parseError && (
            <div className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              {parseError}
            </div>
          )}

          {parseWarnings.length > 0 && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              <p className="font-semibold mb-1">Review extracted fields</p>
              <ul className="space-y-1">
                {parseWarnings.slice(0, 4).map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {fields.map(({ key, label, placeholder, type, required }) => (
              <div key={key} className={key === 'client_email' ? 'sm:col-span-2' : undefined}>
                <label htmlFor={`inv-${key}`} className="block text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">{label}</label>
                <input
                  id={`inv-${key}`}
                  type={type}
                  required={required}
                  min={type === 'number' ? 0 : undefined}
                  step={key.includes('amount') ? '0.01' : undefined}
                  placeholder={placeholder}
                  value={form[key]}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                  className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-coral/30 focus:border-coral/50 transition-colors"
                />
              </div>
            ))}
          </div>

          <div role="alert" className={error ? 'rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700' : 'sr-only'}>
            {error}
          </div>
          <button
            type="submit"
            disabled={loading || parsing}
            className="w-full btn-coral font-bold rounded-xl py-3.5 text-sm flex items-center justify-center gap-2 shadow-card mt-3"
          >
            <Sparkles className="w-4 h-4" />
            {loading ? 'Starting…' : parsing ? 'Reading Invoice...' : 'Start chasing'}
          </button>
        </form>
      </div>
    </div>
  )
}
