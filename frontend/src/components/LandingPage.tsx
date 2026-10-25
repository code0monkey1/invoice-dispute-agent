import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import {
  Zap, Check, X, Pause, Play, RotateCcw, FileText, Search, PenLine, Send,
  Inbox, AlertTriangle, BadgeCheck, Mail, Scale, ListChecks,
  Clock, ShieldCheck, Plus, FileUp, FileDown,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

// Palette, matching the live site: cream ground, brand orange, gray-900 ink.
// ground  #FFF7F0   surface #FFFFFF   ink   #111827   muted #6B7280
// border  #F1E4D8   brand   #FF6B35   brand-tint #FFE9DF
// paid    #1F7A55   legal   #B3261E

// ─── Shared bits ─────────────────────────────────────────────────────────────

function GoogleIcon() {
  return (
    <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
  )
}

interface CtaProps {
  onGoogle: () => void
  onGuest: () => void
}

// The demo needs no sign-up, so it leads; Google sign-in (which asks for
// Gmail access) is the secondary action everywhere on the page.
const demoButton =
  'inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-[#FF6B35] to-[#FF8F65] text-white font-semibold shadow-lg shadow-orange-300/40 hover:from-[#F2551C] hover:to-[#FF6B35]'
const googleButton =
  'inline-flex items-center justify-center gap-2.5 rounded-lg bg-white border border-[#F1E4D8] text-[#111827] font-semibold hover:border-[#111827]'

function CtaButtons({ onGoogle, onGuest }: CtaProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-3">
      <button onClick={onGuest} className={`${demoButton} text-[16px] px-5 py-3.5`}>
        <Play className="w-4 h-4" fill="currentColor" />
        Try the demo
      </button>
      <button onClick={onGoogle} className={`${googleButton} text-[16px] px-5 py-3.5`}>
        <GoogleIcon />
        Sign in with Google
      </button>
    </div>
  )
}

function StickyCta({ onGoogle, onGuest }: CtaProps) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    // Shown once the hero's buttons scroll away, hidden again when the closing
    // call to action (which has the same buttons) comes into view.
    const finalCta = document.getElementById('final-cta')
    const onScroll = () => {
      const finalInView = finalCta ? finalCta.getBoundingClientRect().top < window.innerHeight : false
      setVisible(window.scrollY > 560 && !finalInView)
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [])

  return (
    <div
      aria-hidden={!visible}
      className={`fixed bottom-4 inset-x-4 sm:inset-x-auto sm:left-1/2 sm:-translate-x-1/2 z-50 rounded-xl bg-white border border-[#F1E4D8] shadow-xl shadow-orange-200/40 p-2 sm:pl-5 flex items-center gap-3 sm:gap-6 transition-all duration-300 motion-reduce:transition-none ${
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'
      }`}
    >
      <p className="hidden md:block text-[15px] font-semibold whitespace-nowrap">Have an overdue invoice?</p>
      <div className="flex flex-1 sm:flex-none gap-2">
        <button onClick={onGuest} tabIndex={visible ? 0 : -1} className={`${demoButton} flex-1 sm:flex-none text-[15px] px-4 py-2.5`}>
          Try the demo
        </button>
        <button onClick={onGoogle} tabIndex={visible ? 0 : -1} className={`${googleButton} flex-1 sm:flex-none text-[15px] px-4 py-2.5`}>
          <GoogleIcon />
          Sign in
        </button>
      </div>
    </div>
  )
}

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

function AgentRun() {
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

// ─── Who does what ───────────────────────────────────────────────────────────

const AGENT_JOBS: [LucideIcon, string][] = [
  [FileText, 'Reads your PDF or DOCX invoice'],
  [Clock, 'Works out how overdue it is'],
  [PenLine, 'Drafts each follow-up in the right tone'],
  [Inbox, 'Reads replies and flags disputes'],
  [FileDown, 'Creates invoice PDFs from three templates'],
  [Scale, 'Suggests when to get firmer'],
  [ListChecks, "Finds small-claims rules for your client's location"],
  [Send, 'Sends from your Gmail, not a no-reply bot'],
]

function WhoDoesWhat() {
  return (
    <section className="max-w-[1180px] mx-auto px-4 sm:px-8 pt-20 sm:pt-28 pb-20 sm:pb-28">
      <h2 className="text-[34px] sm:text-[44px] font-bold leading-[1.08] tracking-[-0.02em] max-w-[16ch]">
        The agent does the chasing. You keep the final say.
      </h2>
      <div className="mt-10 grid lg:grid-cols-[1.6fr_1fr] gap-4 items-start">
        <div className="rounded-[16px] bg-white border border-[#F1E4D8] p-6 sm:p-8">
          <h3 className="text-[20px] font-semibold flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#111827]" />
            The agent
          </h3>
          <ul className="mt-5 grid sm:grid-cols-2 gap-x-8 gap-y-4 text-[16px] leading-[1.4]">
            {AGENT_JOBS.map(([Icon, text]) => (
              <li key={text} className="flex items-center gap-3">
                <span className="w-9 h-9 shrink-0 rounded-[10px] bg-[#111827] text-white flex items-center justify-center">
                  <Icon className="w-[18px] h-[18px]" />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-[16px] bg-[#FF6B35] text-[#111827] p-6 sm:p-8">
          <h3 className="text-[20px] font-semibold flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-[3px] bg-[#111827]" />
            You
          </h3>
          <p className="mt-5 text-[28px] sm:text-[32px] font-bold leading-[1.15] tracking-[-0.01em]">
            Add the invoice. Approve each email.
          </p>
          <p className="mt-3 text-[16px] leading-[1.5]">
            Edit or reject any draft. Nothing sends without your click.
          </p>
        </div>
      </div>
    </section>
  )
}

// ─── Invoice generator ───────────────────────────────────────────────────────

const TEMPLATE_NAMES = ['Modern', 'Classic', 'Minimal']

function InvoiceGenerator({ onTry }: { onTry: () => void }) {
  return (
    <section className="max-w-[1180px] mx-auto px-4 sm:px-8 pb-20 sm:pb-28">
      <div className="grid lg:grid-cols-[1fr_1fr] gap-8 lg:gap-16 items-center">
        <div>
          <h2 className="text-[30px] sm:text-[38px] font-bold leading-[1.1] tracking-[-0.02em] max-w-[16ch]">
            No invoice PDF yet? Make one here.
          </h2>
          <p className="mt-4 text-[17px] leading-[1.6] text-[#6B7280] max-w-[48ch]">
            Pick a template, add line items and a Stripe, Lemon Squeezy or PayPal link. The PDF goes straight to the agent.
          </p>
          <button onClick={onTry} className="mt-6 text-[16px] font-semibold underline underline-offset-4 decoration-[#111827]/30 hover:decoration-[#111827]">
            Try the invoice generator in the demo
          </button>
        </div>

        <div aria-hidden="true" className="rounded-[16px] bg-white border border-[#F1E4D8] shadow-xl shadow-orange-200/30 p-4 sm:p-5">
          <div className="grid grid-cols-3 gap-2 text-[14px] font-semibold">
            {TEMPLATE_NAMES.map((name, i) => (
              <span
                key={name}
                className={`rounded-lg border px-3 py-2 text-center ${i === 0 ? 'border-[#FF6B35] bg-white' : 'border-[#F1E4D8] text-[#6B7280]'}`}
              >
                {name}
              </span>
            ))}
          </div>
          <div className="mt-4 rounded-[10px] bg-[#FFFAF5] border border-[#F1E4D8] p-5 text-[14px]">
            <div className="flex justify-between gap-4">
              <div>
                <p className="text-[18px] font-bold">Invoice INV-043</p>
                <p className="text-[#6B7280] mt-0.5">Lena Park Illustration</p>
              </div>
              <div className="text-right text-[#6B7280]">
                <p>Due 30 May</p>
                <p>Bill to Studio North</p>
              </div>
            </div>
            <div className="mt-4 border-t border-[#F1E4D8] divide-y divide-[#F1E4D8]">
              <p className="flex justify-between py-2"><span>Brand illustrations (6)</span><span className="tabular-nums">$1,800.00</span></p>
              <p className="flex justify-between py-2"><span>Revisions</span><span className="tabular-nums">$600.00</span></p>
              <p className="flex justify-between py-2 font-bold"><span>Total</span><span className="tabular-nums">$2,400.00</span></p>
            </div>
            <p className="mt-3 text-[#6B7280]">Pay online: <span className="text-[#111827] underline underline-offset-2">buy.stripe.com/…</span></p>
          </div>
          <p className="mt-4 flex items-center gap-2 text-[15px] font-semibold text-[#1F7A55]">
            <FileDown className="w-4 h-4" />
            Downloaded. INV-043 is now with the agent.
          </p>
        </div>
      </div>
    </section>
  )
}

// ─── Situations (interactive) ───────────────────────────────────────────────

// The day ranges are guidance for the user, not thresholds in the agent:
// escalating is always the user's call.
const SITUATIONS = [
  {
    label: 'Just overdue', pain: 'You want to stay friendly.',
    level: 1, name: 'Friendly', icon: Mail, solid: 'bg-[#1F7A55]', tint: 'bg-[#E7F4EC]', edge: 'border-l-[#1F7A55]',
    when: 'Usually right for invoices 7–30 days late.',
    email: { subject: 'A quick reminder: invoice INV-042', body: ['Hi Sam,', 'Just checking in on invoice INV-042 for $5,000, due 2 April. When can I expect payment?', 'Thanks, Lena'] },
    does: [[Mail, 'Polite reminders'], [Search, 'Invoice status checks']],
  },
  {
    label: 'Being ignored', pain: 'You followed up. Silence.',
    level: 2, name: 'Formal', icon: FileText, solid: 'bg-[#A35E00]', tint: 'bg-[#FDF1DE]', edge: 'border-l-[#A35E00]',
    when: '30–60 days late, or when the client disputes it.',
    email: { subject: 'Invoice INV-042: payment overdue', body: ['Hello Sam,', 'Invoice INV-042 for $5,000 is now 45 days overdue, past our agreed terms.', 'Please pay the balance by 30 May.'] },
    does: [[FileText, 'A formal demand letter'], [Search, 'Invoice status checks']],
  },
  {
    label: 'Last chance', pain: 'Formal letters were ignored.',
    level: 3, name: 'Legal', icon: Scale, solid: 'bg-[#B3261E]', tint: 'bg-[#FBE8E6]', edge: 'border-l-[#B3261E]',
    when: '60+ days late, after formal letters are ignored.',
    email: { subject: 'Final notice: invoice INV-042', body: ['Sam,', "This is formal notice. If payment of $5,000 isn't received within 10 days, I'll file a small-claims case."] },
    does: [[Mail, 'A final notice'], [Scale, "Small-claims rules for the client's location"], [ListChecks, 'A court filing guide']],
  },
] as const

function SituationSelector() {
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
        <p className="mt-4 text-[18px] leading-[1.6] text-[#6B7280]">
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
                className={`text-left rounded-[12px] border border-l-4 px-4 py-3.5 transition-colors ${
                  selected ? `bg-white border-[#F1E4D8] ${item.edge} shadow-md shadow-orange-200/30` : 'bg-transparent border-transparent hover:bg-white/60'
                }`}
              >
                <span className="flex items-center gap-2 text-[17px] font-semibold">
                  <span className={`w-2.5 h-2.5 rounded-full ${item.solid}`} />
                  {item.label}
                </span>
                <span className="mt-0.5 block text-[15px] text-[#6B7280]">{item.pain}</span>
              </button>
            )
          })}
        </div>

        <div
          role="tabpanel"
          id="situation-panel"
          aria-labelledby={`situation-tab-${active}`}
          key={active}
          className="rounded-[16px] bg-white border border-[#F1E4D8] p-5 sm:p-7 animate-[runIn_.3s_ease-out] motion-reduce:animate-none"
        >
          <div className={`rounded-[10px] ${s.tint} px-4 py-3 flex flex-wrap items-center gap-x-3 gap-y-1`}>
            <span className={`w-8 h-8 rounded-[8px] ${s.solid} text-white flex items-center justify-center`}>
              <s.icon className="w-4 h-4" />
            </span>
            <span className="text-[18px] font-semibold">Level {s.level}: {s.name}</span>
            <span className="text-[15px] text-[#374151]">{s.when}</span>
          </div>

          <div className="mt-5 grid lg:grid-cols-[1.4fr_1fr] gap-6">
            <div className="rounded-[10px] border border-[#F1E4D8] bg-[#FFFAF5]">
              <p className="px-4 pt-3 text-[14px] text-[#6B7280]">To sam@clientco.com</p>
              <p className="px-4 pt-0.5 text-[15px] font-semibold">{s.email.subject}</p>
              <div className="lp-serif px-4 pt-2 pb-4 text-[16px] leading-[1.6] space-y-1.5">
                {s.email.body.map((line) => <p key={line}>{line}</p>)}
              </div>
            </div>
            <div>
              <h3 className="text-[16px] font-semibold">What the agent does</h3>
              <ul className="mt-3 space-y-2.5 text-[16px]">
                {s.does.map(([Icon, text]) => (
                  <li key={text} className="flex items-center gap-2.5">
                    <span className="w-8 h-8 shrink-0 rounded-[8px] bg-[#111827] text-white flex items-center justify-center">
                      <Icon className="w-4 h-4" />
                    </span>
                    {text}
                  </li>
                ))}
              </ul>
              <p className="mt-5 flex items-center gap-2 text-[15px] font-semibold">
                <ShieldCheck className="w-4 h-4 text-[#1F7A55]" />
                You approve before it sends
              </p>
              {s.level === 3 && (
                <p className="mt-2 text-[14px] text-[#6B7280]">Court guidance is information, not a filing or a guarantee of payment.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

// ─── With and without ────────────────────────────────────────────────────────

const COMPARISON: [string, string, string][] = [
  ['Writing the email', 'Start from a blank page, every time', 'A draft from your invoice, in the right tone'],
  ['Getting firmer', 'Decide alone how blunt to be', 'The agent suggests the level. You decide.'],
  ['Client replies', 'Search your inbox, update a spreadsheet', 'Saved on the invoice'],
  ['Small claims', 'Research the rules yourself', "Rules for your client's location, plus a filing guide"],
]

function WithWithout() {
  return (
    <section className="max-w-[1180px] mx-auto px-4 sm:px-8 pb-20 sm:pb-28">
      <h2 className="text-[34px] sm:text-[44px] font-bold leading-[1.08] tracking-[-0.02em] max-w-[18ch]">
        Chasing an invoice, with and without InvoiceChaser
      </h2>
      <div className="mt-10 rounded-[16px] bg-white border border-[#F1E4D8] overflow-hidden">
        <table className="w-full text-left text-[16px]">
          <thead>
            <tr className="border-b border-[#F1E4D8] text-[15px]">
              <th scope="col" className="px-5 py-3.5 font-medium text-[#6B7280] hidden md:table-cell w-[22%]">Task</th>
              <th scope="col" className="px-5 py-3.5 font-medium text-[#6B7280]">On your own</th>
              <th scope="col" className="px-5 py-3.5 font-semibold bg-[#111827] text-white">With InvoiceChaser</th>
            </tr>
          </thead>
          <tbody>
            {COMPARISON.map(([task, without, withIt]) => (
              <tr key={task} className="border-b last:border-b-0 border-[#F6EDE3] align-top">
                <th scope="row" className="px-5 py-4 font-semibold hidden md:table-cell">{task}</th>
                <td className="px-5 py-4 text-[#6B7280]">
                  <span className="md:hidden block text-[14px] font-semibold text-[#111827] mb-0.5">{task}</span>
                  <span className="flex gap-2"><X className="w-4 h-4 mt-1 shrink-0 text-[#B3261E]" />{without}</span>
                </td>
                <td className="px-5 py-4 bg-[#FFFAF5]">
                  <span className="md:hidden block text-[14px] mb-0.5">&nbsp;</span>
                  <span className="flex gap-2 font-medium"><Check className="w-4 h-4 mt-1 shrink-0 text-[#1F7A55]" strokeWidth={2.5} />{withIt}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

// ─── How it works (dark band) ────────────────────────────────────────────────

const BAND_STEPS = [
  { you: true, title: 'You add the invoice', text: 'Drop in the PDF, or create one here.' },
  { you: false, title: 'The agent chases', text: 'Reminders, replies and escalation advice.' },
  { you: true, title: 'You approve each email', text: 'Nothing sends from your Gmail without your click.' },
]

function HowItWorksBand() {
  return (
    <section aria-labelledby="how-title" className="bg-[#111827] text-white">
      <div className="max-w-[1180px] mx-auto px-4 sm:px-8 py-12 sm:py-14">
        <h2 id="how-title" className="sr-only">How it works</h2>
        <ol className="grid md:grid-cols-3 gap-8 md:gap-10">
          {BAND_STEPS.map((step, i) => (
            <li key={step.title} className="flex gap-4">
              <span
                className={`w-10 h-10 shrink-0 rounded-[10px] flex items-center justify-center text-[17px] font-bold ${
                  step.you ? 'bg-[#FF6B35] text-[#111827]' : 'bg-white text-[#111827]'
                }`}
              >
                {i + 1}
              </span>
              <div>
                <h3 className="text-[20px] font-semibold">{step.title}</h3>
                <p className="mt-1 text-[16px] leading-[1.5] text-[#D1D5DB]">{step.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

// ─── Testimonials ────────────────────────────────────────────────────────────
// Quotes from InvoiceChaser customers, carried over from the original landing
// page. The portraits are Unsplash stock headshots, not the customers.

interface Testimonial {
  name: string
  role: string
  location: string
  quote: string
  photo: string
}

const FEATURED_TESTIMONIAL: Testimonial = {
  name: 'Daniel Okafor',
  role: 'Co-founder, two-person studio',
  location: 'London, UK',
  quote: 'A client owed us £8,400 for 90 days. InvoiceChaser drafted a formal demand. They paid two days after the demand went out.',
  photo: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=facearea&facepad=2&q=80&auto=format',
}

const TESTIMONIALS: Testimonial[] = [
  {
    name: 'Maya Chen',
    role: 'Brand designer, freelance',
    location: 'Portland, OR',
    quote: 'Now the agent writes [the reminder], I tweak a word or two, and hit approve. Three of my late clients paid within a week.',
    photo: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=200&h=200&fit=facearea&facepad=2&q=80&auto=format',
  },
  {
    name: 'Priya Raman',
    role: 'Independent consultant',
    location: 'Singapore',
    quote: "Every reminder is from my own Gmail, in my own thread. I just don't have to be the one writing the awkward part anymore.",
    photo: 'https://images.unsplash.com/photo-1580489944761-15a19d654956?w=200&h=200&fit=facearea&facepad=2&q=80&auto=format',
  },
]

function Author({ t, size }: { t: Testimonial; size: 'lg' | 'sm' }) {
  return (
    <figcaption className="flex items-center gap-3">
      <img
        src={t.photo}
        alt=""
        loading="lazy"
        referrerPolicy="no-referrer"
        className={`${size === 'lg' ? 'w-14 h-14' : 'w-11 h-11'} rounded-full object-cover bg-[#FDEBDD]`}
      />
      <div className="min-w-0">
        <p className="text-[16px] font-semibold">{t.name}</p>
        <p className="text-[14px] text-[#6B7280]">{t.role}, {t.location}</p>
      </div>
    </figcaption>
  )
}

function Testimonials() {
  return (
    <section className="max-w-[1180px] mx-auto px-4 sm:px-8 pb-20 sm:pb-28">
      <div className="max-w-[640px]">
        <h2 className="text-[34px] sm:text-[44px] font-bold leading-[1.08] tracking-[-0.02em]">
          Loved by people who hate chasing
        </h2>
        <p className="mt-4 text-[18px] leading-[1.6] text-[#6B7280]">
          Freelancers who stopped writing "just following up" emails.
        </p>
      </div>
      <div className="mt-12 grid lg:grid-cols-[1.25fr_1fr] gap-10 lg:gap-16">
        <figure className="border-l-4 border-[#FF6B35] pl-6 sm:pl-8 flex flex-col justify-between gap-8">
          <blockquote className="text-[24px] sm:text-[30px] font-semibold leading-[1.3] tracking-[-0.015em] max-w-[30ch]">
            “{FEATURED_TESTIMONIAL.quote}”
          </blockquote>
          <Author t={FEATURED_TESTIMONIAL} size="lg" />
        </figure>
        <div className="divide-y divide-[#E9D9C8]">
          {TESTIMONIALS.map((t) => (
            <figure key={t.name} className="py-7 first:pt-0 last:pb-0 flex flex-col gap-5">
              <blockquote className="text-[17px] leading-[1.55]">“{t.quote}”</blockquote>
              <Author t={t} size="sm" />
            </figure>
          ))}
        </div>
      </div>
    </section>
  )
}

// ─── FAQ ─────────────────────────────────────────────────────────────────────

const FAQS = [
  {
    question: 'Will InvoiceChaser send emails without my approval?',
    answer: 'No. Every draft waits for you to approve, edit or reject it.',
  },
  {
    question: "Do clients know I'm using an AI tool?",
    answer: 'Emails come from your own Gmail, in the same thread. Clients see a normal email from you.',
  },
  {
    question: 'What if a client replies with a dispute?',
    answer: 'The agent summarizes their objection and suggests how to respond. Anything it drafts still needs your approval.',
  },
  {
    question: 'Is this a replacement for a lawyer?',
    answer: "No. It drafts emails and explains small-claims steps, but it isn't legal advice.",
  },
  {
    question: 'What do I need to get started?',
    answer: 'Your invoice as a PDF or DOCX, or type the details in. Sign in with Google, then connect Gmail to send. Or try the demo first.',
  },
  {
    question: 'Can InvoiceChaser read my inbox?',
    answer: 'No. It can only send the emails you approve. Replies reach your inbox as usual, and a copy lands on the invoice.',
  },
  {
    question: 'Which invoice files work?',
    answer: "PDF or DOCX up to 10 MB. Scans and photos aren't supported yet, so type those in.",
  },
]

// FAQ structured data comes from the same FAQS array, so it can't drift from the page.
const FAQ_JSON_LD = JSON.stringify({
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: FAQS.map(({ question, answer }) => ({
    '@type': 'Question',
    name: question,
    acceptedAnswer: { '@type': 'Answer', text: answer },
  })),
}).replace(/</g, '\\u003c') // static copy only; escaping keeps "</script>" impossible

function Faq() {
  return (
    <section className="max-w-[1180px] mx-auto px-4 sm:px-8 pb-20 sm:pb-28 grid lg:grid-cols-[1fr_1.6fr] gap-8 lg:gap-16">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: FAQ_JSON_LD }} />
      <h2 className="text-[34px] sm:text-[44px] font-bold leading-[1.08] tracking-[-0.02em] max-w-[14ch]">
        Questions before you connect Gmail
      </h2>
      <div className="border-y border-[#E9D9C8] divide-y divide-[#E9D9C8]">
        {FAQS.map(({ question, answer }) => (
          <details key={question} className="group">
            <summary className="flex items-center justify-between gap-4 py-5 cursor-pointer list-none [&::-webkit-details-marker]:hidden text-[17px] font-semibold">
              {question}
              <Plus className="w-5 h-5 shrink-0 text-[#6B7280] transition-transform group-open:rotate-45 motion-reduce:transition-none" />
            </summary>
            <p className="pb-5 -mt-1 text-[16px] leading-[1.6] text-[#6B7280] max-w-[62ch]">{answer}</p>
          </details>
        ))}
      </div>
    </section>
  )
}

// ─── Guest modal ─────────────────────────────────────────────────────────────

interface GuestModalProps {
  name: string
  onNameChange: (name: string) => void
  onEnter: () => void
  onGoogle: () => void
  onClose: () => void
}

function GuestModal({ name, onNameChange, onEnter, onGoogle, onClose }: GuestModalProps) {
  return (
    <div className="fixed inset-0 bg-[#111827]/50 z-[100] flex items-center justify-center p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="guest-title"
        className="bg-white rounded-[16px] w-full max-w-sm border border-[#F1E4D8] shadow-2xl p-6 sm:p-7"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="guest-title" className="text-[22px] font-bold">Try the demo</h2>
            <p className="text-[15px] text-[#6B7280] mt-1">No sign-up. Guest sessions are temporary.</p>
          </div>
          <button onClick={onClose} aria-label="Close" className="p-1 -m-1 text-[#6B7280] hover:text-[#111827]">
            <X className="w-5 h-5" />
          </button>
        </div>

        <label className="block mt-6">
          <span className="block text-[15px] font-semibold mb-1.5">Your name</span>
          <input
            type="text"
            value={name}
            onChange={(e) => onNameChange(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && onEnter()}
            placeholder="e.g. Sam"
            autoFocus
            className="w-full rounded-lg border border-[#F1E4D8] bg-[#FFFAF5] px-3.5 py-2.5 text-[16px] focus:outline-2 focus:outline-[#111827]"
          />
        </label>

        <button
          onClick={onEnter}
          disabled={!name.trim()}
          className="mt-4 w-full rounded-lg bg-[#111827] text-white font-semibold text-[16px] py-3 hover:bg-black disabled:opacity-40"
        >
          Start the demo
        </button>

        <div className="flex items-center gap-3 my-4 text-[14px] text-[#6B7280]">
          <span className="h-px flex-1 bg-[#F1E4D8]" />or<span className="h-px flex-1 bg-[#F1E4D8]" />
        </div>

        <button
          onClick={onGoogle}
          className="w-full inline-flex items-center justify-center gap-2.5 rounded-lg border border-[#F1E4D8] font-semibold text-[16px] py-3 hover:border-[#111827]"
        >
          <GoogleIcon />
          Sign in with Google to save your data
        </button>
      </div>
    </div>
  )
}

// Verified benefits only: each one is something the product does today.
const HERO_POINTS = ['Reads your invoice PDF', 'Friendly, formal, then legal', 'Sends from your Gmail']

// ─── Main Landing Page ───────────────────────────────────────────────────────

export default function LandingPage() {
  const navigate = useNavigate()
  const { signIn, enterAsGuest } = useAuth()
  const [showGuestModal, setShowGuestModal] = useState(false)
  const [guestName, setGuestName] = useState('')

  const handleGuestEntry = () => {
    if (!guestName.trim()) return
    enterAsGuest(guestName.trim())
    navigate('/dashboard')
  }

  const [signInError, setSignInError] = useState(false)

  const handleGoogleSignIn = async () => {
    setSignInError(false)
    try {
      await signIn()
    } catch {
      setSignInError(true)
    }
  }

  const cta = { onGoogle: handleGoogleSignIn, onGuest: () => setShowGuestModal(true) }

  return (
    <div className="lp bg-[#FFF7F0] text-[#111827] min-h-screen [overflow-x:clip]">
      <header className="max-w-[1180px] mx-auto px-4 sm:px-8 h-16 sm:h-20 flex items-center justify-between gap-4">
        <a href="/" className="flex items-center gap-2.5">
          <span className="w-8 h-8 rounded-[10px] bg-gradient-to-br from-[#FF6B35] to-[#FF8F65] text-white shadow-md shadow-orange-300/40 flex items-center justify-center">
            <Zap className="w-4 h-4" strokeWidth={2.5} />
          </span>
          <span className="font-bold text-[19px] tracking-tight">Invoice<span className="text-[#FF6B35]">Chaser</span></span>
        </a>
        <div className="flex items-center gap-4">
          <button onClick={cta.onGoogle} className="hidden sm:inline text-[15px] font-semibold hover:underline underline-offset-4">
            Sign in
          </button>
          <button onClick={cta.onGuest} className={`${demoButton} text-[15px] px-4 py-2`}>
            Try the demo
          </button>
        </div>
      </header>

      <main>
        {/* Two columns on desktop so the product is visible next to the promise. */}
        <section className="max-w-[1180px] mx-auto px-4 sm:px-8 pt-4 sm:pt-8 pb-20 sm:pb-28 grid lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] gap-10 lg:gap-14 items-start">
          <div className="lg:pt-6">
            <h1 className="text-[42px] sm:text-[56px] lg:text-[52px] font-extrabold leading-[1.02] tracking-[-0.035em] max-w-[15ch]">
              Stop chasing unpaid invoices. An agent does it, you approve.
            </h1>
            <p className="mt-6 text-[18px] sm:text-[20px] leading-[1.55] text-[#6B7280] max-w-[42ch]">
              Drop in an overdue invoice. The agent drafts each reminder and suggests when to get firmer. Nothing sends without you.
            </p>
            <ul className="mt-5 flex flex-wrap gap-x-5 gap-y-2 text-[15px] font-medium">
              {HERO_POINTS.map((point) => (
                <li key={point} className="flex items-center gap-1.5">
                  <Check className="w-4 h-4 text-[#1F7A55]" strokeWidth={2.5} />
                  {point}
                </li>
              ))}
            </ul>
            <div className="mt-8">
              <CtaButtons {...cta} />
              <p className="mt-3 text-[15px] font-medium">Free to use. No credit card.</p>
              <p className="mt-3 flex gap-2 text-[14px] leading-[1.5] text-[#6B7280] max-w-[44ch]">
                <ShieldCheck className="w-4 h-4 mt-0.5 shrink-0" />
                Send-only Gmail access. We can't read your inbox.
              </p>
            </div>
          </div>
          <AgentRun />
        </section>

        <HowItWorksBand />

        <WhoDoesWhat />
        <InvoiceGenerator onTry={cta.onGuest} />
        <SituationSelector />
        <WithWithout />
        <Testimonials />
        <Faq />

        <section id="final-cta" className="max-w-[1180px] mx-auto px-4 sm:px-8 pb-16">
          <div className="rounded-[16px] bg-[#111827] text-white p-7 sm:p-12 grid lg:grid-cols-[1fr_auto] gap-8 lg:items-end">
            <div>
              <h2 className="text-[32px] sm:text-[44px] font-bold leading-[1.08] tracking-[-0.02em] max-w-[18ch]">
                Hand your next overdue invoice to the agent.
              </h2>
              <p className="mt-3 text-[17px] text-[#F1E4D8]">No sign-up for the demo. You approve every email.</p>
            </div>
            <CtaButtons {...cta} />
          </div>
        </section>
      </main>

      <footer className="max-w-[1180px] mx-auto px-4 sm:px-8 py-8 flex flex-col sm:flex-row gap-2 sm:gap-6 sm:items-center justify-between text-[14px] text-[#6B7280]">
        <span className="font-semibold text-[#111827] text-[15px]">InvoiceChaser</span>
        <span className="flex flex-wrap gap-x-6 gap-y-1">
          <span>Made for freelancers and small studios</span>
          <span>Built with LangGraph, Groq, FastAPI and React</span>
          <a href="https://github.com/code0monkey1/invoice-dispute-agent" target="_blank" rel="noopener noreferrer" className="underline underline-offset-4">GitHub</a>
        </span>
      </footer>

      <StickyCta {...cta} />

      {signInError && (
        <div role="alert" className="fixed bottom-4 inset-x-4 sm:inset-x-auto sm:right-6 sm:max-w-[420px] z-[110] rounded-xl bg-[#111827] text-white px-5 py-4 shadow-2xl flex items-start gap-4">
          <p className="text-[15px] leading-[1.5]">
            Google sign-in isn't available right now. Try again in a moment, or try the demo.
          </p>
          <button onClick={() => setSignInError(false)} aria-label="Dismiss" className="shrink-0 p-1 -m-1 text-white/70 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>
      )}

      {showGuestModal && (
        <GuestModal
          name={guestName}
          onNameChange={setGuestName}
          onEnter={handleGuestEntry}
          onGoogle={handleGoogleSignIn}
          onClose={() => setShowGuestModal(false)}
        />
      )}
    </div>
  )
}
