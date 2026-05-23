import { useEffect, useRef, useState } from 'react'
import {
  Upload, FileText, Sparkles, Send, CheckCircle2, Mail,
  ArrowRight, MessageSquare, AlertCircle, Pause, Play, Inbox,
} from 'lucide-react'

const SCENES = [
  { id: 1, title: 'Upload invoice', label: 'STEP 1', duration: 11400 },
  { id: 2, title: 'Approve mail', label: 'STEP 2', duration: 11400 },
  { id: 3, title: 'Escalate if needed', label: 'STEP 3', duration: 11400 },
  { id: 4, title: 'Mark resolved if needed', label: 'STEP 4', duration: 11400 },
] as const

const PRESENTER_PHOTOS: Record<PresenterMood, string> = {
  happy: '/presenter/woman-happy.jpg',
  focused: '/presenter/woman-focused.jpg',
  distressed: '/presenter/woman-distressed.jpg',
  relieved: '/presenter/woman-happy.jpg',
  celebrate: '/presenter/woman-happy.jpg',
}

export default function ProductDemoReel() {
  const [sceneIdx, setSceneIdx] = useState(0)
  const [playing, setPlaying] = useState(true)
  const [progress, setProgress] = useState(0)
  const rafRef = useRef<number | null>(null)
  const sceneStartRef = useRef<number>(0)

  useEffect(() => {
    if (!playing) {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      return
    }
    sceneStartRef.current = performance.now()
    const tick = (t: number) => {
      const elapsed = t - sceneStartRef.current
      const dur = SCENES[sceneIdx].duration
      const p = Math.min(1, elapsed / dur)
      setProgress(p)
      if (p >= 1) {
        setSceneIdx((i) => (i + 1) % SCENES.length)
      } else {
        rafRef.current = requestAnimationFrame(tick)
      }
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [sceneIdx, playing])

  const goTo = (i: number) => {
    setSceneIdx(i)
    setProgress(0)
  }

  return (
    <div className="relative w-full max-w-[620px] mx-auto contain-layout">
      {/* Subtle ambient glow */}
      <div className="absolute -inset-6 bg-gradient-to-br from-[#FF6B35]/15 via-violet-300/10 to-teal-300/10 blur-3xl rounded-[40px]" />

      <PresenterNarration sceneIdx={sceneIdx} progress={progress} />

      {/* Browser chrome */}
      <div className="relative mt-4 bg-white rounded-3xl shadow-2xl shadow-orange-300/30 border border-gray-100 overflow-hidden">
        {/* Top bar */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-100 bg-gradient-to-b from-gray-50 to-white">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-red-400/80" />
            <span className="w-3 h-3 rounded-full bg-amber-400/80" />
            <span className="w-3 h-3 rounded-full bg-emerald-400/80" />
          </div>
          <div className="flex-1 mx-3">
            <div className="bg-gray-100 rounded-md px-3 py-1 text-[11px] text-gray-500 font-medium flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              app.invoicechaser.io <span className="text-gray-300">/ INV-042</span>
            </div>
          </div>
          <div className="text-[10px] font-bold text-violet-700 bg-violet-50 border border-violet-200/60 px-2 py-0.5 rounded-full">
            DEMO
          </div>
        </div>

        {/* Step rail */}
        <div className="border-b border-gray-100 bg-white px-3 py-3">
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            {SCENES.map((s, i) => {
              const active = i === sceneIdx
              return (
                <button
                  key={s.id}
                  onClick={() => goTo(i)}
                  aria-label={`Jump to ${s.label.toLowerCase()}: ${s.title}`}
                  className={`relative min-w-[84px] flex-1 rounded-xl border px-2.5 py-2 text-left transition-all ${
                    active
                      ? 'border-orange-200 bg-orange-50 shadow-sm'
                      : 'border-gray-100 bg-gray-50/70 hover:bg-white'
                  }`}
                >
                  <span className={`block text-[9px] font-extrabold tracking-wider ${
                    active ? 'text-[#FF6B35]' : 'text-gray-400'
                  }`}>
                    {s.label}
                  </span>
                  <span className={`mt-0.5 block truncate text-[10px] font-bold ${
                    active ? 'text-gray-900' : 'text-gray-500'
                  }`}>
                    {s.title}
                  </span>
                  {active && (
                    <span className="absolute inset-x-2 bottom-1 h-0.5 overflow-hidden rounded-full bg-orange-100">
                      <span
                        className="block h-full rounded-full bg-gradient-to-r from-[#FF6B35] to-[#FF8F65]"
                        style={{ width: `${progress * 100}%`, transition: 'width 50ms linear' }}
                      />
                    </span>
                  )}
                </button>
              )
            })}
            <button
              onClick={() => setPlaying((p) => !p)}
              aria-label={playing ? 'Pause demo' : 'Play demo'}
              className="ml-1 flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-gray-100 bg-gray-50 text-gray-400 transition-colors hover:bg-white hover:text-gray-700"
            >
              {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Stage */}
        <div className="relative h-[340px] sm:h-[370px] bg-gradient-to-b from-white to-orange-50/30 overflow-hidden">
          <Scene1 active={sceneIdx === 0} progress={sceneIdx === 0 ? progress : 0} />
          <Scene2 active={sceneIdx === 1} progress={sceneIdx === 1 ? progress : 0} />
          <Scene3 active={sceneIdx === 2} progress={sceneIdx === 2 ? progress : 0} />
          <Scene4 active={sceneIdx === 3} progress={sceneIdx === 3 ? progress : 0} />
        </div>
      </div>
    </div>
  )
}

function PresenterNarration({ sceneIdx, progress }: { sceneIdx: number; progress: number }) {
  const note = getPresenterNote(sceneIdx, progress)
  const mood = getPresenterMood(sceneIdx, progress)

  return (
    <div className="relative flex h-[144px] items-stretch gap-3 rounded-2xl border border-orange-100/80 bg-white/90 p-3 shadow-xl shadow-orange-200/30 backdrop-blur sm:h-[142px]">
      <div className="relative flex shrink-0 items-end">
        <AnimatedPresenter mood={mood} />
      </div>

      <div
        className="relative h-full flex-1 overflow-hidden rounded-2xl rounded-bl-md border border-orange-100 bg-white px-3.5 py-2.5 shadow-sm"
      >
        <span className="absolute -left-2 bottom-2 h-4 w-4 rotate-45 border-b border-l border-orange-100 bg-white/95" />
        <p className="text-[11px] font-bold uppercase tracking-wider text-[#FF6B35]">Live walkthrough</p>
        <p className="mt-1 text-[11px] font-semibold leading-snug text-gray-700 sm:text-xs sm:leading-relaxed">
          {note}
        </p>
      </div>
    </div>
  )
}

type PresenterMood = 'happy' | 'focused' | 'distressed' | 'relieved' | 'celebrate'

function getPresenterNote(sceneIdx: number, progress: number) {
  if (sceneIdx === 0) {
    if (progress < 0.5) return 'First human step: upload the invoice. The PDF is being dropped into the product right now.'
    if (progress < 0.82) return 'Now the AI takes over automatically: it reads the invoice and extracts the key details.'
    return 'The product has the client, amount, and overdue status ready. You did not have to type those fields.'
  }
  if (sceneIdx === 1) {
    if (progress < 0.5) return 'The AI is drafting the email on screen. It is not sending anything by itself.'
    if (progress < 0.8) return 'Second human step: review the draft and approve the mail when it looks right.'
    return 'Approved. The reminder is sent from your Gmail only after your click.'
  }
  if (sceneIdx === 2) {
    if (progress < 0.24) return 'The client pushes back on the invoice. This is the stressful part the AI helps you handle.'
    if (progress < 0.58) return 'The AI checks the thread, calculates the fee, and prepares a firmer escalation draft automatically.'
    if (progress < 0.82) return 'Third human step: choose whether escalation is necessary before the stronger message goes out.'
    return 'Escalation is selected. The AI has the formal follow-up ready for approval.'
  }
  if (progress < 0.38) return 'A payment reply comes in and lands on the invoice timeline automatically.'
  if (progress < 0.72) return 'The AI has organized the reply, but closing the invoice is still your decision.'
  if (progress < 0.84) return 'Final human step: mark the invoice resolved when you are satisfied.'
  return 'Resolved. The invoice is closed and the timeline is up to date.'
}

function getPresenterMood(sceneIdx: number, progress: number): PresenterMood {
  if (sceneIdx === 0) return progress < 0.5 ? 'happy' : 'focused'
  if (sceneIdx === 1) return progress > 0.78 ? 'relieved' : 'focused'
  if (sceneIdx === 2) return progress < 0.58 ? 'distressed' : 'focused'
  if (progress > 0.84) return 'celebrate'
  return progress > 0.38 ? 'relieved' : 'focused'
}

function AnimatedPresenter({ mood }: { mood: PresenterMood }) {
  const moods = Object.entries(PRESENTER_PHOTOS) as Array<[PresenterMood, string]>

  return (
    <div
      className={`presenter-photo-avatar presenter-photo-avatar--${mood} h-24 w-24 rounded-2xl border-2 border-white bg-white shadow-lg shadow-orange-200/45 sm:h-[108px] sm:w-[108px]`}
      aria-label={`InvoiceChaser product guide, ${mood} expression`}
      role="img"
    >
      {moods.map(([photoMood, src]) => (
        <img
          key={photoMood}
          src={src}
          alt=""
          width={108}
          height={108}
          loading="eager"
          decoding="async"
          referrerPolicy="no-referrer"
          className={`presenter-photo ${photoMood === mood ? 'presenter-photo--active' : ''}`}
          aria-hidden="true"
        />
      ))}
      <span className="presenter-spark presenter-spark-one" />
      <span className="presenter-spark presenter-spark-two" />
    </div>
  )
}

// ─── Scene wrappers ────────────────────────────────────────────────────────────

function SceneFrame({ active, children }: { active: boolean; children: React.ReactNode }) {
  return (
    <div
      className="absolute inset-0 transition-opacity duration-500"
      style={{
        opacity: active ? 1 : 0,
        pointerEvents: active ? 'auto' : 'none',
      }}
      aria-hidden={!active}
    >
      {children}
    </div>
  )
}

// ─── 1: Drop invoice ──────────────────────────────────────────────────────────

function Scene1({ active, progress }: { active: boolean; progress: number }) {
  const dropFraction = Math.min(1, progress / 0.45)
  const filenameAppears = progress > 0.5
  const readingProgress = Math.max(0, Math.min(1, (progress - 0.55) / 0.4))
  const extracted = progress > 0.82
  return (
    <SceneFrame active={active}>
      <div className="absolute inset-0 flex flex-col items-center justify-center p-5 sm:p-8">
        {/* Drop zone */}
        <div
          className="relative w-full max-w-md border-2 border-dashed rounded-2xl px-5 py-7 transition-all duration-300"
          style={{
            borderColor: progress > 0.45 ? '#FF6B35' : '#fed7aa',
            background: progress > 0.45 ? 'rgba(255,107,53,0.06)' : 'rgba(255,237,213,0.4)',
            transform: dropFraction > 0.3 ? 'scale(1.02)' : 'scale(1)',
          }}
        >
          {/* Floating PDF "tile" descending into the zone */}
          {!filenameAppears && (
            <div
              className="absolute left-1/2 -translate-x-1/2 transition-all duration-700 ease-out"
              style={{
                top: `${10 + dropFraction * 35}%`,
                opacity: 1 - Math.max(0, dropFraction - 0.85) * 5,
              }}
            >
              <div className="w-16 h-20 rounded-lg bg-white border border-gray-200 shadow-xl shadow-orange-200/40 flex flex-col items-center justify-center gap-1 rotate-[-6deg]">
                <FileText className="w-7 h-7 text-[#FF6B35]" />
                <span className="text-[8px] font-bold text-gray-400 tracking-wider">PDF</span>
              </div>
            </div>
          )}

          <div className="flex flex-col items-center justify-center gap-3 min-h-[120px]">
            {filenameAppears ? (
              <>
                <div className="flex items-center gap-3 bg-white border border-orange-200 rounded-xl px-4 py-3 shadow-sm">
                  <div className="w-9 h-9 rounded-lg bg-orange-100 flex items-center justify-center">
                    <FileText className="w-4 h-4 text-[#FF6B35]" />
                  </div>
                  <div className="text-left">
                    <p className="text-sm font-bold text-gray-800">Invoice_Acme_INV-042.pdf</p>
                    <p className="text-[11px] text-gray-400">182 KB · uploaded just now</p>
                  </div>
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 ml-2" />
                </div>
                <div className="w-full max-w-[260px] mt-1">
                  <div className="flex items-center justify-between text-[10px] font-semibold text-gray-500 mb-1">
                    <span className="flex items-center gap-1"><Sparkles className="w-3 h-3 text-violet-500" /> AI reading invoice...</span>
                    <span>{Math.round(readingProgress * 100)}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-orange-100 overflow-hidden">
                    <div className="h-full rounded-full bg-gradient-to-r from-[#FF6B35] to-violet-500" style={{ width: `${readingProgress * 100}%` }} />
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="w-12 h-12 rounded-2xl bg-white border border-orange-100 flex items-center justify-center shadow-sm">
                  <Upload className="w-5 h-5 text-[#FF6B35]" />
                </div>
                <p className="text-sm font-bold text-gray-700">Drop your invoice PDF here</p>
                <p className="text-xs text-gray-400">or click to browse · PDF / DOCX up to 10MB</p>
              </>
            )}
          </div>
        </div>
        <div className="mt-4 w-full max-w-md rounded-2xl border border-violet-100 bg-white/90 p-3 shadow-sm">
          <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-violet-600">
            <Sparkles className="h-3.5 w-3.5" />
            AI automatic
          </div>
          <div className="mt-2 grid grid-cols-3 gap-2">
            {[
              ['Client', 'Acme Corp'],
              ['Amount', '$5,000'],
              ['Due', '45 days late'],
            ].map(([label, value]) => (
              <div
                key={label}
                className="rounded-lg border border-gray-100 bg-gray-50 px-2.5 py-2 transition-all"
                style={{
                  opacity: extracted ? 1 : 0.45,
                  transform: extracted ? 'translateY(0)' : 'translateY(4px)',
                }}
              >
                <p className="text-[9px] font-bold uppercase tracking-wider text-gray-400">{label}</p>
                <p className="mt-0.5 truncate text-[11px] font-bold text-gray-800">{extracted ? value : '...'}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </SceneFrame>
  )
}

// ─── 2: Approve mail ──────────────────────────────────────────────────────────

function Scene2({ active, progress }: { active: boolean; progress: number }) {
  const draftProgress = Math.max(0, Math.min(1, progress / 0.48))
  const draftReady = progress > 0.5
  const cursorProgress = Math.max(0, Math.min(1, (progress - 0.56) / 0.2))
  const isClicking = progress > 0.68 && progress < 0.78
  const sent = progress > 0.8
  const shown = DRAFT_BODY.slice(0, Math.floor(draftProgress * DRAFT_BODY.length))
  return (
    <SceneFrame active={active}>
      <div className="absolute inset-0 p-5 sm:p-6 flex flex-col">
        <div className="mb-3 inline-flex w-fit items-center gap-1.5 rounded-full border border-violet-100 bg-violet-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-violet-700">
          <Sparkles className="h-3 w-3" />
          AI automatic: draft prepared
        </div>
        <div className="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden flex-1 flex flex-col">
          <div className="px-4 py-2.5 bg-gradient-to-r from-violet-50 to-orange-50 border-b border-violet-100/60 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-violet-500" />
              <p className="text-[11px] font-bold text-violet-700 tracking-widest">APPROVAL REQUIRED</p>
            </div>
            <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200/60 rounded-full px-2 py-0.5">
              LEVEL 1
            </span>
          </div>
          <div className="p-4 flex-1 text-[11px] text-gray-600 leading-relaxed overflow-hidden">
            {draftReady ? (
              <>
                <p className="text-xs font-bold text-gray-800 mb-1">To: billing@acme.com</p>
                <p className="text-gray-400 mb-2">Subject: Friendly reminder - Invoice #INV-042</p>
                <p>Hi Sarah, just a gentle nudge that invoice INV-042 for $5,000 is now 45 days past due...</p>
              </>
            ) : (
              <pre className="text-[11px] text-gray-700 leading-relaxed whitespace-pre-wrap font-sans">
                {shown}<span className="inline-block w-1.5 h-3 bg-violet-500 ml-0.5 align-middle animate-pulse" />
              </pre>
            )}
          </div>
          <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-end gap-2 relative">
            <button className="text-xs font-bold text-gray-500 px-3 py-1.5 rounded-lg hover:bg-gray-50">Edit</button>
            <button className="text-xs font-bold text-gray-500 px-3 py-1.5 rounded-lg hover:bg-gray-50">Reject</button>
            <div
              className="relative inline-flex"
              style={{ transform: isClicking ? 'scale(0.95)' : 'scale(1)', transition: 'transform 120ms' }}
            >
              <button
                className="text-xs font-bold text-white px-4 py-1.5 rounded-lg shadow-md shadow-emerald-200/40 flex items-center gap-1.5"
                style={{
                  background: sent ? 'linear-gradient(135deg,#10b981,#059669)' : 'linear-gradient(135deg,#10b981,#34d399)',
                }}
              >
                {sent ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Send className="w-3 h-3" />}
                {sent ? 'Sent' : 'Approve & send'}
              </button>
            </div>
          </div>
        </div>

        {!sent && draftReady && (
          <div
            className="absolute pointer-events-none transition-all duration-500 ease-out"
            style={{ top: 244 - cursorProgress * 34, left: `calc(${50 + cursorProgress * 31}% - 8px)` }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="#1f2937" stroke="white" strokeWidth="1.2" style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.25))' }}>
              <path d="M5 3l14 8-6 1.5-3 6L5 3z" />
            </svg>
            {isClicking && (
              <div className="absolute -inset-3 rounded-full border-2 border-[#FF6B35] animate-ping" />
            )}
          </div>
        )}

        {sent && (
          <div className="absolute bottom-5 left-1/2 -translate-x-1/2 bg-emerald-600 text-white text-xs font-bold px-4 py-2 rounded-full shadow-lg shadow-emerald-300/40 flex items-center gap-2 animate-fade-up">
            <CheckCircle2 className="w-4 h-4" />
            Email sent from your Gmail
          </div>
        )}
      </div>
    </SceneFrame>
  )
}

// ─── 3: Escalate if needed ───────────────────────────────────────────────────

const DRAFT_BODY = `Subject: Friendly reminder - Invoice #INV-042

Hi Sarah,

I hope you're doing well! Just a gentle nudge that invoice INV-042 for $5,000 is now 45 days past due.

Could you let me know when I can expect payment? Happy to resend the invoice or hop on a quick call if anything's unclear.

Best,
Alex`

function Scene3({ active, progress }: { active: boolean; progress: number }) {
  const scanDone = progress > 0.16
  const draftReady = progress > 0.42
  const cursorProgress = Math.max(0, Math.min(1, (progress - 0.58) / 0.2))
  const isClicking = progress > 0.7 && progress < 0.8
  const escalated = progress > 0.82
  return (
    <SceneFrame active={active}>
      <div className="absolute inset-0 p-5 sm:p-6 flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-500" />
          <p className="text-xs font-bold text-gray-700 font-[family-name:var(--font-heading)]">CLIENT PUSHBACK RECEIVED</p>
        </div>

        <div className="self-start max-w-[86%] flex items-start gap-2 animate-fade-up">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-rose-500 to-red-500 flex items-center justify-center text-white shrink-0 mt-1 text-[10px] font-bold">
            SR
          </div>
          <div className="flex-1 bg-white border border-rose-200/70 rounded-2xl rounded-tl-md px-3.5 py-2.5 shadow-md shadow-rose-100/50">
            <div className="flex items-center justify-between mb-1">
              <p className="text-[10px] font-bold text-rose-700 tracking-wider">CLIENT REPLY · DISPUTED</p>
              <span className="text-[10px] text-gray-400">just now</span>
            </div>
            <p className="text-[11px] text-gray-700 leading-relaxed">
              We do not approve this invoice as submitted. Please clarify the late fee and contract terms.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {[
            ['Sent', 'Level 1 mail'],
            ['Checked', scanDone ? 'Dispute found' : 'Scanning'],
            ['Calculated', scanDone ? '$225 fee' : '...'],
          ].map(([label, value], i) => (
            <div key={label} className="rounded-xl border border-gray-100 bg-white px-3 py-2 shadow-sm">
              <p className="text-[9px] font-bold uppercase tracking-wider text-gray-400">{label}</p>
              <p className={`mt-1 text-[11px] font-bold ${scanDone || i === 0 ? 'text-gray-800' : 'text-gray-400'}`}>{value}</p>
            </div>
          ))}
        </div>

        <div className="rounded-2xl border border-amber-200/60 bg-white shadow-sm overflow-hidden">
          <div className="px-3.5 py-2 bg-gradient-to-r from-amber-50 to-orange-50 border-b border-amber-100/60 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-amber-600" />
              <p className="text-[10px] font-bold text-amber-700 tracking-widest">AI AUTOMATIC: FIRMER DRAFT READY</p>
            </div>
          </div>
          <div className="p-3 text-[11px] text-gray-600 leading-relaxed">
            {draftReady ? (
              <>
                <p>"Per our agreement, payment of <span className="font-bold">$5,000</span> was due 45 days ago. A late fee of <span className="font-bold">$225</span> has accrued..."</p>
                <p className="text-[10px] text-gray-400 mt-2 flex items-center gap-1.5">
                  <ArrowRight className="w-3 h-3" /> Tone hardened · Late fees calculated · Awaiting your choice
                </p>
              </>
            ) : (
              <div className="inline-flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-bounce" />
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-bounce" style={{ animationDelay: '120ms' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-bounce" style={{ animationDelay: '240ms' }} />
                <span className="font-semibold text-gray-500 ml-1">Preparing escalation...</span>
              </div>
            )}
          </div>
        </div>

        <div className="mt-auto flex items-center justify-between rounded-2xl border border-gray-100 bg-white px-4 py-3 shadow-sm">
          <div className="flex items-center gap-2">
            <Mail className="w-4 h-4 text-amber-600" />
            <p className="text-[11px] font-semibold text-gray-600">You decide whether this gets firmer.</p>
          </div>
          <button
            className="relative rounded-lg px-4 py-2 text-xs font-bold text-white shadow-md shadow-amber-200/50"
            style={{
              background: escalated ? 'linear-gradient(135deg,#f59e0b,#d97706)' : 'linear-gradient(135deg,#FF6B35,#FF8F65)',
              transform: isClicking ? 'scale(0.95)' : 'scale(1)',
              transition: 'transform 120ms',
            }}
          >
            {escalated ? 'Escalated' : 'Escalate'}
          </button>
        </div>

        {draftReady && !escalated && (
          <div
            className="absolute pointer-events-none transition-all duration-500 ease-out"
            style={{ top: 260 - cursorProgress * 12, left: `calc(${60 + cursorProgress * 25}% - 8px)` }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="#1f2937" stroke="white" strokeWidth="1.2" style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.25))' }}>
              <path d="M5 3l14 8-6 1.5-3 6L5 3z" />
            </svg>
            {isClicking && <div className="absolute -inset-3 rounded-full border-2 border-[#FF6B35] animate-ping" />}
          </div>
        )}
      </div>
    </SceneFrame>
  )
}

// ─── 4: Mark resolved if needed ──────────────────────────────────────────────

function Scene4({ active, progress }: { active: boolean; progress: number }) {
  const replyVisible = progress > 0.16
  const timelineVisible = progress > 0.38
  const cursorProgress = Math.max(0, Math.min(1, (progress - 0.58) / 0.22))
  const isClicking = progress > 0.72 && progress < 0.82
  const resolved = progress > 0.84
  return (
    <SceneFrame active={active}>
      <div className="absolute inset-0 p-5 sm:p-6 flex flex-col gap-3">
        <div className="self-end max-w-[72%] bg-gray-100 text-xs text-gray-600 px-3 py-2 rounded-2xl rounded-br-md">
          <p className="text-[9px] font-bold text-gray-400 mb-0.5">YOU · 2 DAYS AGO</p>
          Formal reminder - Invoice #INV-042
        </div>

        {replyVisible && (
          <div className="self-start max-w-[82%] flex items-start gap-2 animate-fade-up">
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-sky-500 to-blue-500 flex items-center justify-center text-white shrink-0 mt-1 text-[10px] font-bold">
              SR
            </div>
            <div className="flex-1 bg-white border border-sky-200/60 rounded-2xl rounded-tl-md px-3.5 py-2.5 shadow-md shadow-sky-100/50">
              <div className="flex items-center justify-between mb-1">
                <p className="text-[10px] font-bold text-sky-700 tracking-wider">CLIENT REPLY · INBOUND</p>
                <span className="text-[10px] text-gray-400">just now</span>
              </div>
              <p className="text-[11px] text-gray-700 leading-relaxed">
                Payment went through this morning. Thanks for your patience.
              </p>
            </div>
          </div>
        )}

        {timelineVisible && (
          <div className="rounded-2xl border border-violet-100 bg-white p-3 shadow-sm animate-fade-up">
            <div className="flex items-start gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-violet-50 flex items-center justify-center text-violet-600">
                <Inbox className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[10px] font-bold uppercase tracking-wider text-violet-700">AI automatic</p>
                <p className="text-[11px] text-gray-600 mt-0.5">
                  Reply added to the timeline and invoice status is ready for your resolution.
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="mt-auto flex items-center justify-between rounded-2xl border border-gray-100 bg-white px-4 py-3 shadow-sm">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-emerald-600" />
            <p className="text-[11px] font-semibold text-gray-600">Close the loop only when you are satisfied.</p>
          </div>
          <button
            className="relative rounded-lg px-4 py-2 text-xs font-bold text-white shadow-md shadow-emerald-200/50"
            style={{
              background: resolved ? 'linear-gradient(135deg,#10b981,#059669)' : 'linear-gradient(135deg,#10b981,#34d399)',
              transform: isClicking ? 'scale(0.95)' : 'scale(1)',
              transition: 'transform 120ms',
            }}
          >
            {resolved ? 'Resolved' : 'Mark resolved'}
          </button>
        </div>

        {timelineVisible && !resolved && (
          <div
            className="absolute pointer-events-none transition-all duration-500 ease-out"
            style={{ top: 260 - cursorProgress * 12, left: `calc(${56 + cursorProgress * 29}% - 8px)` }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="#1f2937" stroke="white" strokeWidth="1.2" style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.25))' }}>
              <path d="M5 3l14 8-6 1.5-3 6L5 3z" />
            </svg>
            {isClicking && <div className="absolute -inset-3 rounded-full border-2 border-[#FF6B35] animate-ping" />}
          </div>
        )}

        {resolved && (
          <div className="absolute bottom-5 left-1/2 -translate-x-1/2 bg-emerald-600 text-white text-xs font-bold px-4 py-2 rounded-full shadow-lg shadow-emerald-300/40 flex items-center gap-2 animate-fade-up">
            <CheckCircle2 className="w-4 h-4" />
            Invoice marked resolved
          </div>
        )}
      </div>
    </SceneFrame>
  )
}
