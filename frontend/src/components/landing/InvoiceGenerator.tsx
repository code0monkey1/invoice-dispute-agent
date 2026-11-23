import { FileDown } from 'lucide-react'


// ─── Invoice generator ───────────────────────────────────────────────────────

const TEMPLATE_NAMES = ['Modern', 'Classic', 'Minimal']


export function InvoiceGenerator({ onTry }: { onTry: () => void }) {
  return (
    <section className="max-w-[1180px] mx-auto px-4 sm:px-8 pb-20 sm:pb-28">
      <div className="grid lg:grid-cols-[1fr_1fr] gap-8 lg:gap-16 items-center">
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

        <div aria-hidden="true" className="rounded-xl bg-white border border-line shadow-card p-4 sm:p-5">
          <div className="grid grid-cols-3 gap-2 text-[14px] font-semibold">
            {TEMPLATE_NAMES.map((name, i) => (
              <span
                key={name}
                className={`rounded-lg border px-3 py-2 text-center ${i === 0 ? 'border-coral bg-white' : 'border-line text-muted'}`}
              >
                {name}
              </span>
            ))}
          </div>
          <div className="mt-4 rounded-lg bg-card border border-line p-5 text-[14px]">
            <div className="flex justify-between gap-4">
              <div>
                <p className="text-[18px] font-bold">Invoice INV-043</p>
                <p className="text-muted mt-0.5">Lena Park Illustration</p>
              </div>
              <div className="text-right text-muted">
                <p>Due 30 May</p>
                <p>Bill to Studio North</p>
              </div>
            </div>
            <div className="mt-4 border-t border-line divide-y divide-line">
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
