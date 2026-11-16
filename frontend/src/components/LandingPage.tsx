import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/auth'
import { Zap, Check, X, ShieldCheck } from 'lucide-react'
import { CtaButtons, StickyCta } from './landing/CallToAction'
import { demoButton } from './landing/styles'
import { WhoDoesWhat } from './landing/WhoDoesWhat'
import { InvoiceGenerator } from './landing/InvoiceGenerator'
import { SituationSelector } from './landing/SituationSelector'
import { WithWithout } from './landing/WithWithout'
import { HowItWorksBand } from './landing/HowItWorksBand'
import { Testimonials } from './landing/Testimonials'
import { Faq } from './landing/Faq'
import { GuestModal } from './landing/GuestModal'
import { AgentRun } from './landing/AgentRun'


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
