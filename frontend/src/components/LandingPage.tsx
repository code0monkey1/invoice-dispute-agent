import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import {
  Zap, ArrowRight, Shield, Mail, Scale,
  CheckCircle2, Clock, DollarSign, MessageSquare,
  Sparkles, Eye, Users, TrendingUp, Lock, Play, FileText, FilePlus, XCircle
} from 'lucide-react'
import ProductDemoReel from './ProductDemoReel'


// ─── Feature Cards ───────────────────────────────────────────────────────────

const features = [
  {
    icon: <FilePlus className="w-5 h-5" />,
    title: 'Create polished invoices in seconds',
    desc: 'Skip the spreadsheet. Pick from three professionally designed templates, add your Stripe or LemonSqueezy link, and download a clean PDF — ready to send. Saved invoices flow straight into the chase pipeline if the client ghosts.',
    color: '#8b5cf6',
    bg: 'from-violet-50 to-purple-50',
    border: 'border-violet-200/60',
  },
  {
    icon: <FileText className="w-5 h-5" />,
    title: 'Just drop the invoice PDF',
    desc: 'Upload the original invoice — PDF or DOCX. We read it, pull out the client, amount, due date, and jurisdiction, and have you ready to go in seconds. No retyping.',
    color: '#0ea5e9',
    bg: 'from-sky-50 to-blue-50',
    border: 'border-sky-200/60',
  },
  {
    icon: <TrendingUp className="w-5 h-5" />,
    title: 'Knows when to push harder',
    desc: 'Starts with a friendly nudge. If the client ghosts, it ramps to a formal demand. Still nothing? It prepares a small-claims notice — all on the right cadence, without you watching the calendar.',
    color: '#10b981',
    bg: 'from-emerald-50 to-green-50',
    border: 'border-emerald-200/60',
  },
  {
    icon: <Eye className="w-5 h-5" />,
    title: 'You approve every send',
    desc: 'Every email is drafted for you, not sent on your behalf. Read it, tweak the tone, or reject it. Nothing goes out until you click approve.',
    color: '#f59e0b',
    bg: 'from-amber-50 to-orange-50',
    border: 'border-amber-200/60',
  },
  {
    icon: <Mail className="w-5 h-5" />,
    title: 'Sends from your own Gmail',
    desc: 'Connect Gmail once. Reminders go out from your address, replies land in your inbox, and the thread stays intact — clients see a real person, not a no-reply bot.',
    color: '#FF6B35',
    bg: 'from-orange-50 to-amber-50',
    border: 'border-orange-200/60',
  },
  {
    icon: <DollarSign className="w-5 h-5" />,
    title: 'Late fees, calculated',
    desc: "When it's time to add interest, the math is done for you — based on your terms, the balance, and how long it's been overdue.",
    color: '#0d9488',
    bg: 'from-teal-50 to-emerald-50',
    border: 'border-teal-200/60',
  },
  {
    icon: <Scale className="w-5 h-5" />,
    title: 'Ready for small-claims, if you need it',
    desc: "When a dispute really has to go legal, the agent looks up the actual filing procedure for the client's jurisdiction and gives you a step-by-step path to court.",
    color: '#ef4444',
    bg: 'from-rose-50 to-red-50',
    border: 'border-rose-200/60',
  },
  {
    icon: <MessageSquare className="w-5 h-5" />,
    title: 'Replies thread back to you',
    desc: 'Clients reply to your Gmail like normal — those replies show up in the dashboard timeline next to the invoice so you always know where every conversation stands.',
    color: '#8b5cf6',
    bg: 'from-violet-50 to-purple-50',
    border: 'border-violet-200/60',
  },
]

// ─── Stats ───────────────────────────────────────────────────────────────────

const stats = [
  { value: '$825B', label: 'Lost to late payments annually' },
  { value: '3', label: 'Escalation levels' },
  { value: '9', label: 'AI-powered tools' },
  { value: '100%', label: 'Human control over drafts' },
]

const heroOutcomes = [
  'Drafts ready in under 60 seconds',
  '3-step escalation path',
  'Human approval before every send',
]

const trustSignals = [
  { label: 'Google Gmail API', detail: 'sends from your inbox' },
  { label: 'OpenAI', detail: 'drafting and research' },
  { label: 'Supabase', detail: 'secure invoice records' },
  { label: 'Vercel', detail: 'fast product experience' },
]

const chaseScenarios = [
  {
    label: 'Just overdue',
    headline: 'Keep the relationship warm',
    pain: 'You need to follow up without sounding annoyed.',
    outcome: 'InvoiceChaser drafts a friendly reminder and keeps the thread human.',
    proof: 'Best for invoices 7-30 days late',
  },
  {
    label: 'Being ignored',
    headline: 'Make the payment feel urgent',
    pain: 'You have already followed up and the client has gone quiet.',
    outcome: 'The next draft gets firmer, cites the invoice terms, and asks for a clear payment date.',
    proof: 'Best for invoices 30-60 days late',
  },
  {
    label: 'Last chance',
    headline: 'Prepare the serious next step',
    pain: 'The client keeps delaying and you need leverage without losing control.',
    outcome: 'InvoiceChaser calculates late fees and prepares the small-claims path for review.',
    proof: 'Best for invoices 60+ days late',
  },
]

// ─── How It Works Steps ──────────────────────────────────────────────────────

const steps = [
  { step: '01', title: 'Drop the invoice PDF', desc: 'Upload the original invoice (PDF or DOCX). InvoiceChaser reads it and pre-fills the client, amount, due date, and jurisdiction — no retyping.' },
  { step: '02', title: 'AI drafts the email', desc: "The agent writes a reminder tuned to how overdue the invoice is and to your client's tone. No blank-page anxiety." },
  { step: '03', title: 'You approve in one click', desc: 'Read the draft, edit anything you want, or reject it. Nothing leaves your Gmail until you say so.' },
  { step: '04', title: 'It escalates if needed', desc: 'No response after a few rounds? The agent gets firmer, calculates late fees, and prepares a small-claims notice when the time is right.' },
]

// ─── Testimonials ────────────────────────────────────────────────────────────
// Portrait images are AI-styled stock headshots hosted on Unsplash's free CDN —
// stable URLs, no API key, no attribution required for editorial/product use.

const testimonials = [
  {
    name: 'Maya Chen',
    role: 'Brand designer, freelance',
    location: 'Portland, OR',
    quote: 'I used to dread the "second reminder" email — staring at a draft for an hour and still sending something awkward. Now I just upload the PDF, the agent writes it, I tweak a word or two, hit approve. Three of my late clients paid within a week.',
    photo: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=200&h=200&fit=facearea&facepad=2&q=80&auto=format',
  },
  {
    name: 'Daniel Okafor',
    role: 'Co-founder, two-person studio',
    location: 'London, UK',
    quote: 'A client owed us £8,400 for 90 days. Their accounts team kept saying "next week". InvoiceChaser drafted a formal demand with the late-fee math already done, then prepared the small-claims notice. We never had to file — they paid two days after the demand went out.',
    photo: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&h=200&fit=facearea&facepad=2&q=80&auto=format',
  },
  {
    name: 'Priya Raman',
    role: 'Independent consultant',
    location: 'Singapore',
    quote: 'What sold me is that nothing goes out from a "noreply" — every reminder is from my own Gmail, in my own thread. My clients reply like normal. I just don\'t have to be the one writing the awkward part anymore.',
    photo: 'https://images.unsplash.com/photo-1580489944761-15a19d654956?w=200&h=200&fit=facearea&facepad=2&q=80&auto=format',
  },
]

const comparisonRows = [
  {
    label: 'Follow-up timing',
    without: 'Manual calendar reminders that are easy to miss',
    with: 'Automated cadence matched to invoice age',
  },
  {
    label: 'Email quality',
    without: 'Awkward blank-page writing every time',
    with: 'Polished drafts tuned from friendly to formal',
  },
  {
    label: 'Late-fee math',
    without: 'Spreadsheet work and second-guessing',
    with: 'Fees calculated from terms, balance, and days overdue',
  },
  {
    label: 'Legal readiness',
    without: 'Start researching only after things get bad',
    with: 'Small-claims path prepared when escalation is needed',
  },
]

const faqs = [
  {
    question: 'Will InvoiceChaser send emails without my approval?',
    answer: 'No. InvoiceChaser drafts follow-ups for review. You can edit, reject, or approve each message before anything leaves your Gmail.',
  },
  {
    question: 'Do clients know I am using an AI tool?',
    answer: 'Emails are sent from your own Gmail account in the existing thread. Clients see a normal email from you, not a bot or no-reply address.',
  },
  {
    question: 'What if a client replies with a dispute?',
    answer: 'Replies stay attached to the invoice timeline so you can review the thread, adjust the next draft, pause escalation, or resolve the invoice manually.',
  },
  {
    question: 'Can it handle different escalation tones?',
    answer: 'Yes. The agent starts with a friendly reminder, moves to a firmer demand when needed, and can prepare a legal-style notice for serious non-payment.',
  },
  {
    question: 'Does it calculate late fees?',
    answer: 'Yes. When your payment terms support fees or interest, InvoiceChaser can calculate the amount based on the overdue balance and elapsed time.',
  },
  {
    question: 'Is this a replacement for a lawyer?',
    answer: 'No. InvoiceChaser helps you organize evidence, draft communications, and understand small-claims next steps. It does not provide legal representation.',
  },
  {
    question: 'What do I need to get started?',
    answer: 'Upload an invoice PDF or DOCX, confirm the extracted details, and choose whether to try the demo or connect Gmail for real follow-ups.',
  },
]

// ─── Main Landing Page ───────────────────────────────────────────────────────

export default function LandingPage() {
  const navigate = useNavigate()
  const { signIn, enterAsGuest } = useAuth()
  const [showGuestModal, setShowGuestModal] = useState(false)
  const [showStickyCta, setShowStickyCta] = useState(false)
  const [selectedScenario, setSelectedScenario] = useState(1)
  const [guestName, setGuestName] = useState('')

  const activeScenario = chaseScenarios[selectedScenario]

  useEffect(() => {
    const handleScroll = () => setShowStickyCta(window.scrollY > 560)
    handleScroll()
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const handleGuestEntry = () => {
    if (!guestName.trim()) return
    enterAsGuest(guestName.trim())
    navigate('/dashboard')
  }

  const handleGoogleSignIn = () => {
    signIn()
  }

  return (
    <div className="min-h-screen bg-mesh noise overflow-x-hidden">
      {/* ──── Navbar ──── */}
      <nav className="sticky top-0 z-50 bg-white/70 backdrop-blur-xl border-b border-orange-100/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#FF6B35] to-[#FF8F65] flex items-center justify-center shadow-lg shadow-orange-300/40">
                <Zap className="w-5 h-5 text-white" strokeWidth={2.5} />
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900 leading-tight font-[family-name:var(--font-heading)] tracking-tight">
                  Invoice<span className="text-[#FF6B35]">Chaser</span>
                </h1>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="hidden sm:flex items-center gap-1.5 text-xs font-medium text-teal-700 bg-teal-50 px-3 py-1.5 rounded-full border border-teal-200/60">
                <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse-dot" />
                AI Payment Recovery
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* ──── Hero Section ──── */}
      <section className="relative pt-16 pb-24 overflow-hidden">
        {/* Background decorative elements */}
        <div className="absolute top-20 -left-32 w-96 h-96 rounded-full bg-gradient-to-br from-[#FF6B35]/10 to-transparent blur-3xl" />
        <div className="absolute bottom-0 -right-32 w-96 h-96 rounded-full bg-gradient-to-br from-teal-400/8 to-transparent blur-3xl" />
        <div className="absolute top-40 right-20 w-64 h-64 rounded-full bg-gradient-to-br from-violet-400/6 to-transparent blur-3xl" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            {/* Left — Copy */}
            <div className="animate-fade-up">
              <div className="inline-flex items-center gap-2 text-xs font-bold text-[#FF6B35] bg-orange-50 px-4 py-2 rounded-full border border-orange-200/60 mb-6">
                <Sparkles className="w-3.5 h-3.5" />
                AI-POWERED PAYMENT RECOVERY
              </div>

              <h2 className="text-5xl sm:text-6xl font-extrabold text-gray-900 font-[family-name:var(--font-heading)] tracking-tight leading-[1.1] mb-6">
                Stop chasing.
                <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#FF6B35] to-[#FF8F65]">
                  Start recovering.
                </span>
              </h2>

              <p className="text-lg text-gray-500 leading-relaxed mb-6 max-w-lg">
                Turn an overdue invoice into an approved follow-up in under a minute. InvoiceChaser drafts the reminder, calculates the next escalation, and keeps every send under your control.
              </p>

              <div className="grid sm:grid-cols-3 gap-2.5 mb-8 max-w-xl">
                {heroOutcomes.map((outcome) => (
                  <div key={outcome} className="flex items-start gap-2 rounded-xl bg-white/75 border border-orange-100/70 px-3 py-2.5 shadow-sm">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                    <span className="text-xs font-semibold leading-snug text-gray-600">{outcome}</span>
                  </div>
                ))}
              </div>

              <div className="flex flex-wrap gap-3 mb-10">
                <button
                  onClick={() => setShowGuestModal(true)}
                  className="inline-flex items-center gap-2.5 btn-gradient text-white text-sm font-bold rounded-xl px-7 py-3.5 shadow-lg shadow-orange-300/40 hover:shadow-orange-400/60 transition-all font-[family-name:var(--font-heading)] group"
                >
                  <Play className="w-4 h-4 group-hover:scale-110 transition-transform" />
                  Try live demo
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </button>
                <button
                  onClick={handleGoogleSignIn}
                  className="inline-flex items-center gap-2.5 bg-white hover:bg-gray-50 text-gray-700 text-sm font-bold rounded-xl px-6 py-3.5 shadow-sm border border-gray-200 transition-all font-[family-name:var(--font-heading)]"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                  </svg>
                  Connect Gmail
                </button>
              </div>

              {/* Trust badges */}
              <div className="flex items-center gap-4 text-xs text-gray-400">
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  <span className="font-medium">Free to use</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  <span className="font-medium">No credit card</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  <span className="font-medium">Full AI control</span>
                </div>
              </div>
            </div>

            {/* Right — Product demo reel (auto-playing walkthrough) */}
            <div className="animate-fade-up" style={{ animationDelay: '300ms' }}>
              <ProductDemoReel />
            </div>
          </div>
        </div>
      </section>

      {/* ──── Trust Strip ──── */}
      <section className="py-6 bg-white/65 border-y border-orange-100/70">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col lg:flex-row lg:items-center gap-5">
            <div className="flex items-center gap-2.5 text-sm font-extrabold text-gray-900 font-[family-name:var(--font-heading)] shrink-0">
              <Lock className="w-4 h-4 text-[#FF6B35]" />
              You&apos;re in good company
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 flex-1">
              {trustSignals.map((signal) => (
                <div key={signal.label} className="rounded-xl border border-gray-100 bg-white px-4 py-3 shadow-sm">
                  <p className="text-sm font-bold text-gray-800">{signal.label}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{signal.detail}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ──── Stats Bar ──── */}
      <section className="relative py-10 bg-gradient-to-r from-gray-900 via-gray-800 to-gray-900 overflow-hidden">
        <div className="absolute inset-0 opacity-20">
          <div className="absolute -left-20 top-0 w-60 h-60 rounded-full bg-[#FF6B35]/30 blur-3xl" />
          <div className="absolute -right-20 bottom-0 w-60 h-60 rounded-full bg-teal-400/20 blur-3xl" />
        </div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((s, i) => (
              <div key={i} className="text-center animate-fade-up" style={{ animationDelay: `${i * 100}ms` }}>
                <p className="text-3xl sm:text-4xl font-extrabold text-white font-[family-name:var(--font-heading)] mb-1">
                  {s.value}
                </p>
                <p className="text-xs sm:text-sm text-gray-400 font-medium">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ──── Situation Selector ──── */}
      <section className="py-20 bg-white/35 border-b border-orange-100/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-[0.9fr_1.1fr] gap-10 items-center">
            <div className="animate-fade-up">
              <span className="inline-flex items-center gap-1.5 text-xs font-bold text-[#FF6B35] bg-orange-50 px-3 py-1.5 rounded-full border border-orange-200/60 mb-4">
                <Eye className="w-3 h-3" />
                PICK YOUR CHASE
              </span>
              <h3 className="text-3xl sm:text-4xl font-extrabold text-gray-900 font-[family-name:var(--font-heading)] tracking-tight">
                Different late invoices need different pressure.
              </h3>
              <p className="text-gray-500 mt-4 leading-relaxed">
                Choose the situation closest to yours. The product demo stays the same, but the message changes because the follow-up should match the client&apos;s behavior.
              </p>
            </div>

            <div className="animate-fade-up" style={{ animationDelay: '120ms' }}>
              <div className="grid sm:grid-cols-3 gap-3 mb-4">
                {chaseScenarios.map((scenario, i) => (
                  <button
                    key={scenario.label}
                    onClick={() => setSelectedScenario(i)}
                    className={`rounded-2xl border p-4 text-left transition-all ${
                      selectedScenario === i
                        ? 'border-orange-300 bg-orange-50 shadow-lg shadow-orange-200/35'
                        : 'border-gray-100 bg-white hover:border-orange-200 hover:bg-orange-50/40'
                    }`}
                  >
                    <p className={`text-xs font-extrabold uppercase tracking-wider ${
                      selectedScenario === i ? 'text-[#FF6B35]' : 'text-gray-400'
                    }`}>
                      {scenario.label}
                    </p>
                    <p className="mt-2 text-sm font-bold text-gray-900 leading-snug">{scenario.headline}</p>
                  </button>
                ))}
              </div>

              <div className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-start gap-4">
                  <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-[#FF6B35] to-[#FF8F65] flex items-center justify-center text-white shrink-0">
                    <MessageSquare className="w-5 h-5" />
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">{activeScenario.proof}</p>
                    <h4 className="text-xl font-extrabold text-gray-900 font-[family-name:var(--font-heading)]">{activeScenario.headline}</h4>
                    <p className="text-sm text-gray-500 mt-2 leading-relaxed">{activeScenario.pain}</p>
                    <div className="mt-4 rounded-xl bg-emerald-50 border border-emerald-100 px-4 py-3 flex gap-2.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                      <p className="text-sm font-medium text-gray-700 leading-relaxed">{activeScenario.outcome}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ──── How It Works ──── */}
      <section className="py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16 animate-fade-up">
            <span className="inline-flex items-center gap-1.5 text-xs font-bold text-teal-600 bg-teal-50 px-3 py-1.5 rounded-full border border-teal-200/60 mb-4">
              <Clock className="w-3 h-3" />
              SIMPLE WORKFLOW
            </span>
            <h3 className="text-4xl font-extrabold text-gray-900 font-[family-name:var(--font-heading)] tracking-tight">
              How it works
            </h3>
            <p className="text-gray-400 mt-3 max-w-md mx-auto">Four steps to recover what you're owed. The AI handles the hard part.</p>
          </div>

          <div className="grid md:grid-cols-4 gap-6">
            {steps.map((s, i) => (
              <div key={i} className="relative group animate-fade-up" style={{ animationDelay: `${i * 120}ms` }}>
                {/* Connector line */}
                {i < steps.length - 1 && (
                  <div className="hidden md:block absolute top-8 left-[calc(100%+0.25rem)] w-[calc(100%-3rem)] h-px bg-gradient-to-r from-[#FF6B35]/30 to-transparent" />
                )}
                <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm card-lift h-full">
                  <div className="text-4xl font-extrabold text-[#FF6B35]/15 font-[family-name:var(--font-heading)] mb-3 leading-none">
                    {s.step}
                  </div>
                  <h4 className="text-lg font-bold text-gray-900 font-[family-name:var(--font-heading)] mb-2">{s.title}</h4>
                  <p className="text-sm text-gray-500 leading-relaxed">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ──── Features Grid ──── */}
      <section className="py-24 bg-gradient-to-b from-white/40 to-transparent">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16 animate-fade-up">
            <span className="inline-flex items-center gap-1.5 text-xs font-bold text-violet-600 bg-violet-50 px-3 py-1.5 rounded-full border border-violet-200/60 mb-4">
              <Sparkles className="w-3 h-3" />
              WHAT YOU GET
            </span>
            <h3 className="text-4xl font-extrabold text-gray-900 font-[family-name:var(--font-heading)] tracking-tight">
              The collections workflow you wish you had
            </h3>
            <p className="text-gray-400 mt-3 max-w-lg mx-auto">
              All the steps you&apos;d normally dread — written for you, ready for your approval.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map((f, i) => (
              <div
                key={i}
                className={`bg-gradient-to-br ${f.bg} rounded-2xl p-6 border ${f.border} card-lift animate-fade-up`}
                style={{ animationDelay: `${i * 80}ms` }}
              >
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center mb-4 shadow-sm"
                  style={{ background: `linear-gradient(135deg, ${f.color}, ${f.color}cc)`, color: 'white' }}
                >
                  {f.icon}
                </div>
                <h4 className="text-lg font-bold text-gray-900 font-[family-name:var(--font-heading)] mb-2">{f.title}</h4>
                <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ──── Escalation Preview ──── */}
      <section className="py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16 animate-fade-up">
            <span className="inline-flex items-center gap-1.5 text-xs font-bold text-[#FF6B35] bg-orange-50 px-3 py-1.5 rounded-full border border-orange-200/60 mb-4">
              <TrendingUp className="w-3 h-3" />
              ESCALATION ENGINE
            </span>
            <h3 className="text-4xl font-extrabold text-gray-900 font-[family-name:var(--font-heading)] tracking-tight">
              Three levels. Zero missed payments.
            </h3>
          </div>

          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {[
              {
                level: 1, name: 'Friendly', color: '#10b981', bgFrom: '#ecfdf5', bgTo: '#d1fae5',
                icon: <Mail className="w-5 h-5 text-white" />,
                tone: '"Hi Sarah, just a gentle reminder about invoice #INV-042 — let me know if you need anything to release payment."',
                summary: 'A warm, friendly nudge. Keeps the relationship intact.',
              },
              {
                level: 2, name: 'Formal', color: '#f59e0b', bgFrom: '#fffbeb', bgTo: '#fef3c7',
                icon: <Shield className="w-5 h-5 text-white" />,
                tone: '"Per our agreement, payment of $5,000 was due 45 days ago. A late fee of $225 has now accrued."',
                summary: 'Firm, businesslike, with late fees calculated for you.',
              },
              {
                level: 3, name: 'Legal', color: '#ef4444', bgFrom: '#fef2f2', bgTo: '#fecaca',
                icon: <Scale className="w-5 h-5 text-white" />,
                tone: '"This constitutes formal notice. Failure to remit within 10 days will result in a small-claims filing in California."',
                summary: 'Final notice + the actual small-claims filing path for your jurisdiction.',
              },
            ].map((l, i) => (
              <div key={i} className="animate-fade-up" style={{ animationDelay: `${i * 150}ms` }}>
                <div
                  className="rounded-2xl border-2 overflow-hidden card-lift h-full"
                  style={{
                    borderColor: l.color + '30',
                    background: `linear-gradient(180deg, ${l.bgFrom}, ${l.bgTo})`,
                  }}
                >
                  <div className="px-5 py-4 flex items-center gap-3" style={{ background: `linear-gradient(135deg, ${l.color}, ${l.color}dd)` }}>
                    <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center">
                      {l.icon}
                    </div>
                    <div>
                      <p className="text-white font-extrabold font-[family-name:var(--font-heading)]">Level {l.level}</p>
                      <p className="text-white/70 text-xs font-medium">{l.name}</p>
                    </div>
                  </div>
                  <div className="p-5 space-y-4">
                    <div>
                      <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1.5">Sample tone</p>
                      <p className="text-xs text-gray-600 italic leading-relaxed">
                        {l.tone}
                      </p>
                    </div>
                    <p className="text-xs text-gray-600 leading-relaxed">{l.summary}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ──── Testimonials ──── */}
      <section className="py-24 bg-gradient-to-b from-transparent to-white/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-14 animate-fade-up">
            <span className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-full border border-emerald-200/60 mb-4">
              <Users className="w-3 h-3" />
              REAL FREELANCERS, REAL RESULTS
            </span>
            <h3 className="text-4xl font-extrabold text-gray-900 font-[family-name:var(--font-heading)] tracking-tight">
              Loved by people who hate chasing
            </h3>
            <p className="text-gray-500 mt-3 max-w-lg mx-auto">
              Designers, agencies, and consultants who finally stopped writing awkward "just following up" emails.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 max-w-6xl mx-auto">
            {testimonials.map((t, i) => (
              <figure
                key={t.name}
                className="relative bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-lg transition-shadow p-6 animate-fade-up flex flex-col"
                style={{ animationDelay: `${i * 120}ms` }}
              >
                {/* 5-star rating */}
                <div className="flex items-center gap-0.5 mb-4">
                  {[0, 1, 2, 3, 4].map((s) => (
                    <svg key={s} className="w-4 h-4 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.286 3.953a1 1 0 00.95.69h4.156c.969 0 1.371 1.24.588 1.81l-3.362 2.443a1 1 0 00-.364 1.118l1.286 3.953c.3.921-.755 1.688-1.54 1.118l-3.362-2.443a1 1 0 00-1.176 0l-3.362 2.443c-.784.57-1.838-.197-1.54-1.118l1.287-3.953a1 1 0 00-.364-1.118L2.93 8.38c-.783-.57-.38-1.81.588-1.81h4.156a1 1 0 00.95-.69l1.286-3.953z" />
                    </svg>
                  ))}
                </div>

                {/* Quote */}
                <blockquote className="text-sm text-gray-700 leading-relaxed mb-6 flex-1">
                  &ldquo;{t.quote}&rdquo;
                </blockquote>

                {/* Author */}
                <figcaption className="flex items-center gap-3 pt-4 border-t border-gray-100">
                  <img
                    src={t.photo}
                    alt={t.name}
                    loading="lazy"
                    referrerPolicy="no-referrer"
                    className="w-11 h-11 rounded-full object-cover border-2 border-white shadow-md ring-1 ring-gray-100"
                  />
                  <div className="min-w-0">
                    <p className="text-sm font-bold text-gray-900 truncate">{t.name}</p>
                    <p className="text-xs text-gray-500 truncate">
                      {t.role} <span className="text-gray-300">·</span> {t.location}
                    </p>
                  </div>
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>

      {/* ──── Comparison ──── */}
      <section className="py-24 bg-gradient-to-b from-white/35 to-transparent">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12 animate-fade-up">
            <span className="inline-flex items-center gap-1.5 text-xs font-bold text-[#FF6B35] bg-orange-50 px-3 py-1.5 rounded-full border border-orange-200/60 mb-4">
              <Shield className="w-3 h-3" />
              LESS CHASING, MORE CONTROL
            </span>
            <h3 className="text-4xl font-extrabold text-gray-900 font-[family-name:var(--font-heading)] tracking-tight">
              With vs. without InvoiceChaser
            </h3>
          </div>

          <div className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm animate-fade-up">
            <div className="grid grid-cols-[1fr] md:grid-cols-[1.05fr_1fr_1fr] bg-gray-900 text-white">
              <div className="hidden md:block px-5 py-4 text-xs font-bold uppercase tracking-wider text-gray-400">Workflow</div>
              <div className="px-5 py-4 text-sm font-extrabold font-[family-name:var(--font-heading)]">Without InvoiceChaser</div>
              <div className="px-5 py-4 text-sm font-extrabold font-[family-name:var(--font-heading)] bg-[#FF6B35]">With InvoiceChaser</div>
            </div>
            {comparisonRows.map((row) => (
              <div key={row.label} className="grid grid-cols-1 md:grid-cols-[1.05fr_1fr_1fr] border-t border-gray-100">
                <div className="px-5 py-4 bg-gray-50/80">
                  <p className="text-sm font-bold text-gray-900">{row.label}</p>
                </div>
                <div className="px-5 py-4 flex gap-2.5">
                  <XCircle className="w-4 h-4 text-gray-300 mt-0.5 shrink-0" />
                  <p className="text-sm text-gray-500 leading-relaxed">{row.without}</p>
                </div>
                <div className="px-5 py-4 flex gap-2.5 bg-orange-50/45">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                  <p className="text-sm font-medium text-gray-700 leading-relaxed">{row.with}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ──── FAQ ──── */}
      <section className="py-24">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12 animate-fade-up">
            <span className="inline-flex items-center gap-1.5 text-xs font-bold text-teal-700 bg-teal-50 px-3 py-1.5 rounded-full border border-teal-200/60 mb-4">
              <MessageSquare className="w-3 h-3" />
              QUESTIONS BEFORE YOU CHASE
            </span>
            <h3 className="text-4xl font-extrabold text-gray-900 font-[family-name:var(--font-heading)] tracking-tight">
              Common objections, answered
            </h3>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            {faqs.map((faq, i) => (
              <details
                key={faq.question}
                className="group rounded-2xl border border-gray-100 bg-white p-5 shadow-sm animate-fade-up open:border-orange-200/80 open:shadow-md"
                style={{ animationDelay: `${i * 60}ms` }}
              >
                <summary className="flex cursor-pointer list-none items-start justify-between gap-4">
                  <span className="text-sm font-extrabold text-gray-900 font-[family-name:var(--font-heading)] leading-snug">{faq.question}</span>
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-orange-50 text-[#FF6B35] text-lg leading-none transition-transform group-open:rotate-45">+</span>
                </summary>
                <p className="mt-4 text-sm leading-relaxed text-gray-500">{faq.answer}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ──── CTA Section ──── */}
      <section className="py-24">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center animate-fade-up">
          <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-3xl p-12 sm:p-16 relative overflow-hidden">
            {/* Decorative orbs */}
            <div className="absolute -top-16 -right-16 w-48 h-48 rounded-full bg-[#FF6B35]/20 blur-3xl" />
            <div className="absolute -bottom-16 -left-16 w-48 h-48 rounded-full bg-teal-400/15 blur-3xl" />

            <div className="relative">
              <h3 className="text-3xl sm:text-4xl font-extrabold text-white font-[family-name:var(--font-heading)] tracking-tight mb-4">
                Ready to recover what you're owed?
              </h3>
              <p className="text-gray-400 mb-8 max-w-md mx-auto">
                Start chasing payments with AI in seconds. No sign-up required to try the live demo.
              </p>
              <div className="flex flex-wrap items-center justify-center gap-4">
                <button
                  onClick={() => setShowGuestModal(true)}
                  className="inline-flex items-center gap-2.5 btn-gradient text-white text-sm font-bold rounded-xl px-8 py-4 shadow-lg shadow-orange-500/30 hover:shadow-orange-500/50 transition-all font-[family-name:var(--font-heading)] group"
                >
                  <Users className="w-4 h-4" />
                  Try live demo
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </button>
                <button
                  onClick={handleGoogleSignIn}
                  className="inline-flex items-center gap-2 bg-white/10 hover:bg-white/20 backdrop-blur text-white text-sm font-bold rounded-xl px-8 py-4 transition-all border border-white/10 font-[family-name:var(--font-heading)]"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#fff"/>
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#fff"/>
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#fff"/>
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#fff"/>
                  </svg>
                  Connect Gmail
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ──── Footer ──── */}
      <footer className="border-t border-gray-200/60 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <Zap className="w-4 h-4 text-[#FF6B35]" />
            <span className="font-semibold text-gray-600 font-[family-name:var(--font-heading)]">InvoiceChaser</span>
            <span>&middot; AI-powered invoice recovery</span>
          </div>
          <div className="flex items-center gap-4 text-xs text-gray-400">
            <a href="https://github.com" target="_blank" rel="noopener" className="hover:text-[#FF6B35] transition-colors font-medium">GitHub</a>
            <span>&middot;</span>
            <span>Made for freelancers &amp; small studios</span>
          </div>
        </div>
      </footer>

      {/* ──── Guest Sign-In Modal ──── */}
      {showGuestModal && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-[100] flex items-center justify-center p-4" onClick={() => setShowGuestModal(false)}>
          <div
            className="bg-white rounded-3xl w-full max-w-sm shadow-2xl shadow-orange-200/30 border border-orange-100/50 animate-fade-up overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="bg-gradient-to-r from-[#FF6B35] to-[#FF8F65] px-6 py-6 relative overflow-hidden">
              <div className="absolute inset-0 opacity-10">
                <div className="absolute -right-8 -top-8 w-32 h-32 rounded-full bg-white/20" />
                <div className="absolute -left-4 -bottom-4 w-20 h-20 rounded-full bg-white/10" />
              </div>
              <div className="relative text-center">
                <div className="w-14 h-14 rounded-2xl bg-white/20 flex items-center justify-center mx-auto mb-3">
                  <Users className="w-7 h-7 text-white" />
                </div>
                <h2 className="text-xl font-bold text-white font-[family-name:var(--font-heading)]">
                  Live Demo
                </h2>
                <p className="text-white/70 text-xs mt-1.5">Explore InvoiceChaser without signing up — perfect for a quick walkthrough</p>
              </div>
            </div>

            {/* Form */}
            <div className="p-6 space-y-5">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Your Name</label>
                <input
                  type="text"
                  value={guestName}
                  onChange={(e) => setGuestName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleGuestEntry()}
                  placeholder="Enter your name..."
                  autoFocus
                  className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-800 placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-[#FF6B35]/30 focus:border-[#FF6B35]/50 transition-all"
                />
              </div>

              <button
                onClick={handleGuestEntry}
                disabled={!guestName.trim()}
                className="w-full btn-gradient disabled:opacity-50 text-white font-bold rounded-xl py-3.5 text-sm transition-all flex items-center justify-center gap-2 shadow-lg shadow-orange-300/40 font-[family-name:var(--font-heading)]"
              >
                <ArrowRight className="w-4 h-4" />
                Start Demo
              </button>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-100" />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="bg-white px-3 text-gray-400 font-medium">or</span>
                </div>
              </div>

              <button
                onClick={handleGoogleSignIn}
                className="w-full bg-white hover:bg-gray-50 text-gray-700 font-bold rounded-xl py-3.5 text-sm transition-all flex items-center justify-center gap-2 border border-gray-200 shadow-sm font-[family-name:var(--font-heading)]"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                Continue with Google
              </button>

              <p className="text-[11px] text-gray-400 text-center">
                Guest sessions are temporary. Sign in with Google to save your data.
              </p>
            </div>
          </div>
        </div>
      )}

      {showStickyCta && !showGuestModal && (
        <div className="fixed bottom-4 left-0 right-0 z-40 px-4 sm:px-6">
          <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 rounded-2xl border border-orange-200/70 bg-white/90 p-3 shadow-2xl shadow-orange-200/40 backdrop-blur-xl">
            <div className="min-w-0">
              <p className="text-sm font-extrabold text-gray-900 font-[family-name:var(--font-heading)]">Recover overdue invoices faster</p>
              <p className="hidden sm:block text-xs text-gray-500">Try the demo or connect Gmail when you&apos;re ready to send real follow-ups.</p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <button
                onClick={() => setShowGuestModal(true)}
                className="inline-flex items-center gap-2 btn-gradient text-white text-xs sm:text-sm font-bold rounded-xl px-4 py-3 shadow-lg shadow-orange-300/40 font-[family-name:var(--font-heading)]"
              >
                Try demo
                <ArrowRight className="w-4 h-4" />
              </button>
              <button
                onClick={handleGoogleSignIn}
                className="hidden sm:inline-flex items-center gap-2 bg-gray-900 hover:bg-gray-800 text-white text-sm font-bold rounded-xl px-4 py-3 transition-all font-[family-name:var(--font-heading)]"
              >
                Connect Gmail
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
