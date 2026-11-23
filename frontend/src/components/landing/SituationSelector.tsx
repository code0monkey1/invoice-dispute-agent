import { useState, useRef } from 'react'
import { ShieldCheck } from 'lucide-react'
import { SITUATIONS } from './situations'


// ─── Situations (interactive) ───────────────────────────────────────────────



export function SituationSelector() {
  const [active, setActive] = useState(1)
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([])
  const s = SITUATIONS[active]

  const select = (i: number) => {
    const next = (i + SITUATIONS.length) % SITUATIONS.length
    setActive(next)
    tabRefs.current[next]?.focus()
  }

  return (
    <section className="max-w-[1180px] mx-auto px-4 sm:px-8 pb-20 sm:pb-28">
      <div className="max-w-[640px]">
        <h2 className="text-[34px] sm:text-[44px] font-bold leading-[1.08] tracking-[-0.02em]">
          Different late invoices need different pressure
        </h2>
        <p className="mt-4 text-[18px] leading-[1.6] text-muted">
          Pick a situation to see the email the agent drafts. You choose the level, and approve every email.
        </p>
      </div>

      <div className="mt-10 grid md:grid-cols-[280px_1fr] gap-4 items-start">
        <div role="tablist" aria-label="Situations" aria-orientation="vertical" className="grid gap-2">
          {SITUATIONS.map((item, i) => {
            const selected = i === active
            return (
              <button
                key={item.label}
                ref={(el) => { tabRefs.current[i] = el }}
                role="tab"
                id={`situation-tab-${i}`}
                aria-selected={selected}
                aria-controls="situation-panel"
                tabIndex={selected ? 0 : -1}
                onClick={() => setActive(i)}
                onKeyDown={(e) => {
                  if (e.key === 'ArrowDown' || e.key === 'ArrowRight') { e.preventDefault(); select(i + 1) }
                  if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') { e.preventDefault(); select(i - 1) }
                }}
                className={`text-left rounded-xl border px-4 py-3.5 transition-colors ${
                  selected ? `bg-white border-line shadow-card` : 'bg-transparent border-transparent hover:bg-white/60'
                }`}
              >
                <span className="flex items-center gap-2 text-[18px] font-semibold">
                  <span className={`w-2.5 h-2.5 rounded-full ${item.solid}`} />
                  {item.label}
                </span>
                <span className="mt-0.5 block text-[16px] text-muted">{item.pain}</span>
              </button>
            )
          })}
        </div>

        <div
          role="tabpanel"
          id="situation-panel"
          aria-labelledby={`situation-tab-${active}`}
          key={active}
          className="rounded-xl bg-white border border-line p-5 sm:p-7 animate-[runIn_.3s_ease-out] motion-reduce:animate-none"
        >
          <div className={`rounded-lg ${s.tint} px-4 py-3 flex flex-wrap items-center gap-x-3 gap-y-1`}>
            <span className={`w-8 h-8 rounded-lg ${s.solid} text-white flex items-center justify-center`}>
              <s.icon className="w-4 h-4" />
            </span>
            <span className="text-[18px] font-semibold">Level {s.level}: {s.name}</span>
            <span className="text-[16px] text-body">{s.when}</span>
          </div>

          <div className="mt-5 grid lg:grid-cols-[1.4fr_1fr] gap-6">
            <div className="rounded-lg border border-line bg-card">
              <p className="px-4 pt-3 text-[14px] text-muted">To sam@clientco.com</p>
              <p className="px-4 pt-0.5 text-[16px] font-semibold">{s.email.subject}</p>
              <div className="font-serif px-4 pt-2 pb-4 text-[16px] leading-[1.6] space-y-1.5">
                {s.email.body.map((line) => <p key={line}>{line}</p>)}
              </div>
            </div>
            <div>
              <h3 className="text-[16px] font-semibold">What the agent does</h3>
              <ul className="mt-3 space-y-2.5 text-[16px]">
                {s.does.map(([Icon, text]) => (
                  <li key={text} className="flex items-center gap-2.5">
                    <span className="w-8 h-8 shrink-0 rounded-lg bg-ink text-white flex items-center justify-center">
                      <Icon className="w-4 h-4" />
                    </span>
                    {text}
                  </li>
                ))}
              </ul>
              <p className="mt-5 flex items-center gap-2 text-[16px] font-semibold">
                <ShieldCheck className="w-4 h-4 text-green" />
                You approve before it sends
              </p>
              {s.level === 3 && (
                <p className="mt-2 text-[14px] text-muted">Court guidance is information, not a filing or a guarantee of payment.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
