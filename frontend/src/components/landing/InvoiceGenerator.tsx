import { useState } from 'react'
import { FileDown } from 'lucide-react'


// ─── Invoice generator ───────────────────────────────────────────────────────

const TEMPLATE_NAMES = ['Modern', 'Classic', 'Minimal'] as const

// Each template restyles the same sample invoice, as the real PDF templates do.
const PREVIEW_STYLES: Record<(typeof TEMPLATE_NAMES)[number], { page: string; head: string; title: string; rows: string }> = {
  Modern: {
    page: 'rounded-lg bg-card border border-line p-5',
    head: 'flex justify-between gap-4',
    title: 'text-[18px] font-bold',
    rows: 'mt-4 border-t border-line divide-y divide-line',
  },
  Classic: {
    page: 'rounded-lg bg-white border border-line-2 p-5 font-serif',
    head: 'flex justify-between gap-4 pb-3 border-b-2 border-ink',
    title: 'text-[20px] font-bold uppercase tracking-wide',
    rows: 'mt-4 border border-line-2 divide-y divide-line-2 px-3',
  },
  Minimal: {
    page: 'rounded-lg bg-white p-5 pt-6',
    head: 'flex justify-between gap-4',
    title: 'text-[18px] font-normal',
    rows: 'mt-6 divide-y divide-line/60',
  },
}


export function InvoiceGenerator({ onTry }: { onTry: () => void }) {
  const [template, setTemplate] = useState<(typeof TEMPLATE_NAMES)[number]>('Modern')
  const style = PREVIEW_STYLES[template]
  return (
    <section className="max-w-[1180px] mx-auto px-4 sm:px-8 pb-20 sm:pb-28">
      <div className="grid lg:grid-cols-[1fr_1fr] gap-8 lg:gap-16 items-start">
        <div>
          <h2 className="text-[30px] sm:text-[38px] font-bold leading-[1.1] tracking-[-0.02em] max-w-[16ch]">
            No invoice PDF yet? Make one here.
          </h2>
          <p className="mt-4 text-[18px] leading-[1.6] text-muted max-w-[48ch]">
            Pick a template, add line items and a Stripe, Lemon Squeezy or PayPal link. The PDF goes straight to the agent.
          </p>
          <button onClick={onTry} className="mt-6 inline-flex items-center min-h-11 text-[16px] font-semibold underline underline-offset-4 decoration-ink/30 hover:decoration-ink">
            Try the invoice generator in the demo
          </button>
        </div>

        <div className="rounded-xl bg-white border border-line shadow-card p-4 sm:p-5">
          <div role="tablist" aria-label="Invoice template" className="grid grid-cols-3 gap-2 text-[14px] font-semibold">
            {TEMPLATE_NAMES.map((name, i) => {
              const selected = name === template
              return (
                <button
                  key={name}
                  type="button"
                  role="tab"
                  id={`tpl-tab-${name}`}
                  aria-selected={selected}
                  aria-controls="tpl-preview"
                  tabIndex={selected ? 0 : -1}
                  onClick={() => setTemplate(name)}
                  onKeyDown={(e) => {
                    const step = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0
                    if (!step) return
                    e.preventDefault()
                    const next = TEMPLATE_NAMES[(i + step + TEMPLATE_NAMES.length) % TEMPLATE_NAMES.length]
                    setTemplate(next)
                    document.getElementById(`tpl-tab-${next}`)?.focus()
                  }}
                  className={`rounded-lg border min-h-11 px-3 py-2 text-center transition-colors ${selected ? 'border-coral bg-white' : 'border-line text-muted hover:text-ink hover:border-line-2'}`}
                >
                  {name}
                </button>
              )
            })}
          </div>
          <div id="tpl-preview" role="tabpanel" aria-labelledby={`tpl-tab-${template}`} className={`mt-4 text-[14px] ${style.page}`}>
            <div className={style.head}>
              <div>
                <p className={style.title}>Invoice INV-043</p>
                <p className="text-muted mt-0.5">Lena Park Illustration</p>
              </div>
              <div className="text-right text-muted">
                <p>Due 30 May</p>
                <p>Bill to Studio North</p>
              </div>
            </div>
            <div className={style.rows}>
              <p className="flex justify-between py-2"><span>Brand illustrations (6)</span><span className="tabular-nums">$1,800.00</span></p>
              <p className="flex justify-between py-2"><span>Revisions</span><span className="tabular-nums">$600.00</span></p>
              <p className="flex justify-between py-2 font-bold"><span>Total</span><span className="tabular-nums">$2,400.00</span></p>
            </div>
            <p className="mt-3 text-muted">Pay online: <span className="text-ink underline underline-offset-2">buy.stripe.com/…</span></p>
          </div>
          <p className="mt-4 flex items-center gap-2 text-[16px] font-semibold text-green">
            <FileDown className="w-4 h-4" />
            Downloaded. INV-043 is now with the agent.
          </p>
        </div>
      </div>
    </section>
  )
}
