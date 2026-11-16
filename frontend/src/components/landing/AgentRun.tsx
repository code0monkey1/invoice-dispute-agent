import { useState, useEffect, useRef } from 'react'
import { Check, Pause, Play, RotateCcw, FileText, Search, PenLine, Send, Inbox, AlertTriangle, BadgeCheck, Mail, Scale, FileUp } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'


// ─── Agent run script ────────────────────────────────────────────────────────

type Mood = 'happy' | 'focused' | 'distressed'


const FACES: Record<Mood, string> = {
  happy: '/presenter/woman-happy.jpg',
  focused: '/presenter/woman-focused.jpg',
  distressed: '/presenter/woman-distressed.jpg',
}


interface Draft {
  subject: string
  body: string[]
}


interface RunEvent {
  who: 'agent' | 'you'
  date: string
  icon: LucideIcon
  title: string
  detail?: string
  file?: string
  fields?: [string, string][]
  draft?: Draft
  mood: Mood
  thought: string
}


const FRIENDLY_DRAFT: Draft = {
  subject: 'A reminder about invoice INV-042',
  body: [
    'Hi Sam,',
    'Invoice INV-042 for $5,000 was due on 2 April. When can I expect payment?',
    'Thanks, Lena',
  ],
}


const FORMAL_DRAFT: Draft = {
  subject: 'Invoice INV-042: payment overdue',
  body: [
    'Hello Sam,',
    'Our 3 March contract covers this work, so the full $5,000 stands.',
    'Please pay the balance within 7 business days.',
  ],
}


const RUN: RunEvent[] = [
  {
    who: 'you', date: '16 Apr', icon: FileUp, title: 'Added the invoice PDF',
    file: 'INV-042_ClientCo.pdf',
    mood: 'happy', thought: 'I drop in the PDF. No retyping.',
  },
  {
    who: 'agent', date: '16 Apr', icon: FileText, title: 'Read the PDF',
    fields: [
      ['Invoice', 'INV-042'],
      ['Client', 'Client Co.'],
      ['Email', 'sam@clientco.com'],
      ['Amount', '$5,000.00'],
      ['Due', '2 April'],
      ['Jurisdiction', 'Oregon'],
    ],
    mood: 'happy', thought: 'Back to client work. The agent takes it from here.',
  },
  {
    who: 'agent', date: '16 Apr', icon: Search, title: 'Checked the invoice status',
    detail: 'Unpaid. 14 days overdue.',
    mood: 'happy', thought: 'Back to client work. The agent takes it from here.',
  },
  {
    who: 'agent', date: '16 Apr', icon: PenLine, title: 'Drafted a friendly reminder',
    mood: 'happy', thought: 'Back to client work. The agent takes it from here.',
  },
  {
    who: 'you', date: '16 Apr', icon: Mail, title: 'Approve the reminder',
    draft: FRIENDLY_DRAFT,
    mood: 'focused', thought: 'My only job: read it, approve it.',
  },
  {
    who: 'agent', date: '16 Apr', icon: Send, title: 'Sent from your Gmail',
    detail: 'Watching for a reply.',
    mood: 'happy', thought: 'Back to my own work.',
  },
  {
    who: 'agent', date: '18 Apr', icon: AlertTriangle, title: 'Client disputed the invoice',
    detail: '“We don\'t approve this invoice. Please clarify the scope and terms.”',
    mood: 'distressed', thought: "A dispute. The email I'd put off for a week.",
  },
  {
    who: 'agent', date: '18 Apr', icon: Inbox, title: 'Summarized the dispute',
    detail: 'Suggested a firmer, formal reply.',
    mood: 'distressed', thought: "A dispute. The email I'd put off for a week.",
  },
  {
    who: 'you', date: '18 Apr', icon: Scale, title: 'Moved it to Formal',
    detail: 'Escalating is always your call.',
    mood: 'focused', thought: 'Firmer it is. My call.',
  },
  {
    who: 'agent', date: '18 Apr', icon: FileText, title: 'Drafted a formal reply',
    detail: 'Cited the agreed contract and payment terms.',
    mood: 'focused', thought: 'Firmer it is. My call.',
  },
  {
    who: 'you', date: '18 Apr', icon: Mail, title: 'Approve the formal reply',
    draft: FORMAL_DRAFT,
    mood: 'focused', thought: 'Firm, polite, numbers right.',
  },
  {
    who: 'agent', date: '18 Apr', icon: Send, title: 'Sent from your Gmail',
    detail: 'Watching for a reply.',
    mood: 'focused', thought: 'Firm, polite, numbers right.',
  },
  {
    who: 'agent', date: '22 Apr', icon: BadgeCheck, title: 'Client promised payment',
    detail: '“Paying in full on Friday.” Saved on the invoice, with a suggestion to mark it pending.',
    mood: 'happy', thought: "Getting paid, and I didn't write a single email.",
  },
]


// Derived from RUN so the copy never drifts from the demo.
const YOUR_STEPS = RUN.filter((e) => e.who === 'you').length


const STEP_MS = 1500

const CHECKPOINT_MS = 5000

const END_HOLD_MS = 5000


// ─── Agent run (the hero demo) ───────────────────────────────────────────────

function DraftCard({ draft, pending, onApprove }: { draft: Draft; pending: boolean; onApprove: () => void }) {
  return (
    <div className="mt-3 rounded-[10px] bg-white border border-[#F1E4D8]">
      <p className="px-4 pt-3 text-[14px] text-[#6B7280]">
        To sam@clientco.com
      </p>
      <p className="px-4 pt-0.5 text-[15px] font-semibold">{draft.subject}</p>
      <div className="lp-serif px-4 pt-2 pb-3 text-[16px] leading-[1.6] text-[#111827] space-y-1.5">
        {draft.body.map((line) => <p key={line}>{line}</p>)}
      </div>
      <div className="px-4 pb-3.5 flex flex-wrap items-center gap-x-4 gap-y-2">
        {pending ? (
          <>
            <button
              onClick={onApprove}
              className="inline-flex items-center gap-2 rounded-lg bg-[#FF6B35] text-[#111827] font-semibold text-[15px] px-4 py-2 hover:bg-[#F2551C]"
            >
              <Check className="w-4 h-4" strokeWidth={2.5} />
              Approve and send
            </button>
            <span className="text-[14px] text-[#6B7280]">You can also edit or reject it.</span>
          </>
        ) : (
          <span className="inline-flex items-center gap-1.5 text-[14px] font-semibold text-[#1F7A55]">
            <Check className="w-4 h-4" strokeWidth={2.5} />
            Approved by you
          </span>
        )}
      </div>
    </div>
  )
}


function Freelancer({ mood, thought }: { mood: Mood; thought: string }) {
  return (
    <figure className="flex items-center gap-4">
      <div className="relative w-[76px] h-[76px] sm:w-[88px] sm:h-[88px] shrink-0 rounded-[14px] overflow-hidden bg-[#FDEBDD]">
        {(Object.keys(FACES) as Mood[]).map((m) => (
          <img
            key={m}
            src={FACES[m]}
            alt=""
            width={148}
            height={148}
            className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-500 motion-reduce:transition-none ${m === mood ? 'opacity-100' : 'opacity-0'}`}
          />
        ))}
      </div>
      <figcaption className="min-w-0">
        <p
          className="relative rounded-[12px] rounded-bl-[4px] bg-[#FFF1E6] px-3.5 py-2.5 text-[16px] leading-[1.45] font-medium max-w-[34ch] before:absolute before:-left-1.5 before:bottom-2 before:w-3 before:h-3 before:rotate-45 before:bg-[#FFF1E6]"
          aria-live="polite"
        >
          “{thought}”
        </p>
        <p className="mt-1.5 text-[14px] text-[#6B7280]">Lena, freelance illustrator</p>
      </figcaption>
    </figure>
  )
}


export function AgentRun() {
  const reducedMotion = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  // `shown` is how many events are on screen. A draft that is the last event
  // shown is a pending checkpoint; revealing the next event approves it.
  const [shown, setShown] = useState(reducedMotion ? RUN.length : 1)
  const [playing, setPlaying] = useState(!reducedMotion)
  const logRef = useRef<HTMLOListElement>(null)

  const current = RUN[shown - 1]
  const pending = Boolean(current.draft)
  const finished = shown === RUN.length

  useEffect(() => {
    if (!playing) return
    const delay = finished ? END_HOLD_MS : pending ? CHECKPOINT_MS : STEP_MS
    const timer = setTimeout(() => setShown((n) => (n >= RUN.length ? 1 : n + 1)), delay)
    return () => clearTimeout(timer)
  }, [shown, playing, pending, finished])

  useEffect(() => {
    const log = logRef.current
    if (log) log.scrollTo({ top: log.scrollHeight, behavior: reducedMotion ? 'auto' : 'smooth' })
  }, [shown, reducedMotion])

  const approve = () => setShown((n) => n + 1)
  const replay = () => {
    setShown(1)
    setPlaying(true)
  }

  return (
    <div aria-labelledby="run-title" role="region">
      <div className="rounded-[16px] bg-white border border-[#F1E4D8] shadow-xl shadow-orange-200/30">
        <div aria-hidden="true" className="flex items-center gap-3 px-4 py-2.5 rounded-t-[16px] bg-[#FBF5EE] border-b border-[#F1E4D8]">
          <span className="flex gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#F2A39A]" />
            <span className="w-2.5 h-2.5 rounded-full bg-[#F4C77B]" />
            <span className="w-2.5 h-2.5 rounded-full bg-[#9FD3AE]" />
          </span>
          <span className="flex-1 max-w-[300px] mx-auto rounded-md bg-white border border-[#F1E4D8] px-3 py-1 text-[13px] text-[#6B7280] text-center truncate">
            InvoiceChaser / Invoices / INV-042
          </span>
          <span className="w-[42px]" />
        </div>
        <div className="px-5 sm:px-6 py-4 border-b border-[#F1E4D8] flex items-center justify-between gap-4">
          <Freelancer mood={current.mood} thought={current.thought} />
          <div className="hidden sm:block shrink-0 text-[14px] leading-[1.5] text-[#6B7280]">
            <p className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-[#111827]" />The agent</p>
            <p className="flex items-center gap-2 mt-1.5"><span className="w-2.5 h-2.5 rounded-[3px] bg-[#FF6B35]" />You</p>
          </div>
        </div>

        <div className="flex flex-col min-w-0">
          <div className="flex items-center justify-between gap-4 px-5 sm:px-6 py-3.5 border-b border-[#F1E4D8]">
            <h2 id="run-title" className="text-[17px] font-semibold">
              Agent run for INV-042 <span className="font-normal text-[#6B7280]">(example)</span>
            </h2>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPlaying((p) => !p)}
                aria-label={playing ? 'Pause the example' : 'Play the example'}
                className="w-9 h-9 rounded-lg flex items-center justify-center hover:bg-[#FFF1E6]"
              >
                {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </button>
              <button
                onClick={replay}
                aria-label="Replay the example from the start"
                className="w-9 h-9 rounded-lg flex items-center justify-center hover:bg-[#FFF1E6]"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="px-5 sm:px-6 py-3 border-b border-[#F1E4D8]">
            <div className="flex items-center justify-between gap-3 text-[14px]">
              <span className="text-[#6B7280] tabular-nums" aria-live="polite">
                Step {shown} of {RUN.length}
              </span>
              {pending ? (
                <span className="rounded-full bg-[#FF6B35] text-[#111827] font-semibold px-2.5 py-0.5">Your turn</span>
              ) : (
                <span className="text-[#6B7280]">{current.who === 'you' ? 'You' : 'Agent working'}</span>
              )}
            </div>
            <p className="sr-only">{`${YOUR_STEPS} of the ${RUN.length} steps are yours: adding the invoice, deciding to escalate, and approving each email.`}</p>
            <ol className="mt-2 flex gap-1" aria-hidden="true">
              {RUN.map((event, i) => {
                const done = i < shown
                const isYou = event.who === 'you'
                const color = isYou
                  ? done ? 'bg-[#FF6B35]' : 'bg-[#FFCFB8]'
                  : done ? 'bg-[#111827]' : 'bg-[#F1E4D8]'
                return (
                  <li key={i} className={`h-1.5 flex-1 rounded-full transition-colors ${color} ${i === shown - 1 ? 'ring-2 ring-offset-1 ring-[#FF6B35]/40' : ''}`}>
                  </li>
                )
              })}
            </ol>
          </div>

          <ol ref={logRef} className="h-[420px] sm:h-[440px] overflow-y-auto px-5 sm:px-6 py-4 space-y-1">
            {RUN.slice(0, shown).map((event, i) => {
              const Icon = event.icon
              const isYou = event.who === 'you'
              const isPending = Boolean(event.draft) && i === shown - 1
              return (
                <li
                  key={i}
                  className={`grid grid-cols-[52px_1fr] sm:grid-cols-[64px_1fr] gap-3 rounded-[10px] py-3 animate-[runIn_.35s_ease-out] motion-reduce:animate-none ${
                    isYou ? 'bg-[#FFE9DF] px-3 -mx-3' : ''
                  }`}
                >
                  <span className="text-[14px] text-[#6B7280] tabular-nums pt-0.5">{event.date}</span>
                  <div className="min-w-0">
                    <p className="flex items-start gap-2.5 text-[16px] font-semibold leading-snug">
                      <span
                        className={`mt-0.5 w-6 h-6 shrink-0 flex items-center justify-center ${
                          isYou ? 'rounded-[6px] bg-[#FF6B35] text-[#111827]' : 'rounded-full bg-[#111827] text-white'
                        }`}
                      >
                        <Icon className="w-3.5 h-3.5" strokeWidth={2.25} />
                      </span>
                      <span>
                        <span className="sr-only">{isYou ? 'You: ' : 'Agent: '}</span>
                        {event.title}
                      </span>
                    </p>
                    {event.detail && <p className="mt-1 pl-[34px] text-[15px] leading-[1.5] text-[#6B7280]">{event.detail}</p>}
                    {event.file && (
                      <div className="sm:pl-[34px]">
                        <div className="mt-3 rounded-[10px] border-2 border-dashed border-[#FF6B35]/50 bg-white px-4 py-4 flex items-center gap-4">
                          <span className="w-11 h-12 shrink-0 rounded-[6px] bg-[#FFF1E6] border border-[#F1E4D8] flex flex-col items-center justify-center">
                            <FileText className="w-4 h-4 text-[#B3261E]" />
                            <span className="text-[10px] font-bold text-[#B3261E] mt-0.5">PDF</span>
                          </span>
                          <div className="min-w-0 flex-1">
                            <p className="text-[15px] font-semibold truncate">{event.file}</p>
                            <div className="mt-2 h-1.5 rounded-full bg-[#F1E4D8] overflow-hidden">
                              <div className="h-full rounded-full bg-[#FF6B35] animate-[lpFill_1.3s_ease-out_forwards] motion-reduce:animate-none motion-reduce:w-full" />
                            </div>
                            <p className="mt-1.5 text-[14px] text-[#6B7280]">48 KB, uploaded</p>
                          </div>
                        </div>
                      </div>
                    )}
                    {event.fields && (
                      <dl className="mt-3 pl-[34px] grid grid-cols-2 gap-2">
                        {event.fields.map(([label, value], f) => (
                          <div
                            key={label}
                            style={{ animationDelay: `${f * 90}ms` }}
                            className="rounded-[8px] bg-white border border-[#F1E4D8] px-3 py-2 animate-[runIn_.35s_ease-out_both] motion-reduce:animate-none"
                          >
                            <dt className="text-[13px] text-[#6B7280]">{label}</dt>
                            <dd className="text-[15px] font-semibold truncate">{value}</dd>
                          </div>
                        ))}
                      </dl>
                    )}
                    {event.draft && (
                      <div className="sm:pl-[34px]">
                        <DraftCard draft={event.draft} pending={isPending} onApprove={approve} />
                      </div>
                    )}
                  </div>
                </li>
              )
            })}
          </ol>
        </div>
      </div>
      <p className="mt-3 text-[14px] text-[#6B7280]">
        {pending ? 'Your turn. Approve, or it continues in a few seconds.' : `You do ${YOUR_STEPS} of the ${RUN.length} steps. Nothing here is actually sent.`}
      </p>
    </div>
  )
}
