import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import {
  Zap, ArrowRight, Shield, Mail, Scale,
  CheckCircle2, Clock, DollarSign, MessageSquare,
  Sparkles, Eye, Users, TrendingUp, Lock, Play, FileText
} from 'lucide-react'

// ─── Animated Agent Flow (3D Isometric CSS) ──────────────────────────────────

function AgentFlowVisualization() {
  const [activeLevel, setActiveLevel] = useState(1)
  const [particlePhase, setParticlePhase] = useState(0)

  useEffect(() => {
    const levelTimer = setInterval(() => {
      setActiveLevel(prev => prev >= 3 ? 1 : prev + 1)
    }, 3000)
    const particleTimer = setInterval(() => {
      setParticlePhase(prev => (prev + 1) % 6)
    }, 800)
    return () => { clearInterval(levelTimer); clearInterval(particleTimer) }
  }, [])

  const levels = [
    {
      level: 1, label: 'Friendly', color: '#10b981', bgFrom: '#ecfdf5', bgTo: '#d1fae5',
      tools: ['Polite reminder', 'Status check'],
      icon: <Mail className="w-4 h-4" />,
    },
    {
      level: 2, label: 'Formal', color: '#f59e0b', bgFrom: '#fffbeb', bgTo: '#fef3c7',
      tools: ['Formal demand', 'Late fee math'],
      icon: <Shield className="w-4 h-4" />,
    },
    {
      level: 3, label: 'Legal', color: '#ef4444', bgFrom: '#fef2f2', bgTo: '#fecaca',
      tools: ['Final notice', 'Small-claims path'],
      icon: <Scale className="w-4 h-4" />,
    },
  ]

  return (
    <div className="agent-flow-container relative w-full max-w-[600px] mx-auto" style={{ perspective: '1200px' }}>
      <div
        className="relative py-4"
        style={{
          transform: 'rotateX(8deg) rotateY(-4deg)',
          transformStyle: 'preserve-3d',
        }}
      >
        {/* Input node */}
        <div className="flex items-center justify-center mb-6 animate-fade-up">
          <div className="relative flex items-center gap-3 bg-white rounded-2xl px-5 py-3 shadow-lg shadow-gray-200/60 border border-gray-100">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#FF6B35] to-[#FF8F65] flex items-center justify-center shadow-md shadow-orange-200/50">
              <MessageSquare className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Input</p>
              <p className="text-sm font-bold text-gray-800 font-[family-name:var(--font-heading)]">"Chase this payment"</p>
            </div>
            <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 w-px h-3 bg-gradient-to-b from-gray-300 to-transparent" />
          </div>
        </div>

        {/* Middleware pipeline */}
        <div className="relative mx-auto max-w-[480px]">
          <div className="absolute left-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-[#FF6B35]/30 via-gray-200 to-transparent -translate-x-1/2" />

          {/* Dynamic Prompt */}
          <div className="flex items-center justify-center mb-4 animate-fade-up" style={{ animationDelay: '200ms' }}>
            <div className="middleware-node relative bg-gradient-to-r from-violet-50 to-purple-50 border border-violet-200/60 rounded-xl px-4 py-2.5 shadow-sm">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-violet-500 to-purple-500 flex items-center justify-center">
                  <Sparkles className="w-3 h-3 text-white" />
                </div>
                <div>
                  <p className="text-[9px] font-bold text-violet-500 uppercase tracking-widest">Middleware</p>
                  <p className="text-xs font-bold text-gray-700">Dynamic Prompt</p>
                </div>
                <span className="ml-2 text-[10px] font-semibold text-violet-600 bg-violet-100 px-2 py-0.5 rounded-full">
                  Tone: {levels[activeLevel - 1].label}
                </span>
              </div>
              {/* Pulse ring */}
              <div className="absolute inset-0 rounded-xl border-2 border-violet-300/40 animate-middleware-pulse" />
            </div>
          </div>

          {/* Dynamic Tools */}
          <div className="flex items-center justify-center mb-4 animate-fade-up" style={{ animationDelay: '400ms' }}>
            <div className="middleware-node relative bg-gradient-to-r from-teal-50 to-emerald-50 border border-teal-200/60 rounded-xl px-4 py-2.5 shadow-sm">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-teal-500 to-emerald-500 flex items-center justify-center">
                  <Lock className="w-3 h-3 text-white" />
                </div>
                <div>
                  <p className="text-[9px] font-bold text-teal-500 uppercase tracking-widest">Middleware</p>
                  <p className="text-xs font-bold text-gray-700">Dynamic Tool Gate</p>
                </div>
                <span className="ml-2 text-[10px] font-semibold text-teal-600 bg-teal-100 px-2 py-0.5 rounded-full">
                  Level {activeLevel} tools
                </span>
              </div>
              <div className="absolute inset-0 rounded-xl border-2 border-teal-300/40 animate-middleware-pulse" style={{ animationDelay: '500ms' }} />
            </div>
          </div>

          {/* HITL */}
          <div className="flex items-center justify-center mb-6 animate-fade-up" style={{ animationDelay: '600ms' }}>
            <div className="middleware-node relative bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200/60 rounded-xl px-4 py-2.5 shadow-sm">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center">
                  <Eye className="w-3 h-3 text-white" />
                </div>
                <div>
                  <p className="text-[9px] font-bold text-amber-500 uppercase tracking-widest">Middleware</p>
                  <p className="text-xs font-bold text-gray-700">Human-in-the-Loop</p>
                </div>
                <span className="ml-2 text-[10px] font-semibold text-amber-600 bg-amber-100 px-2 py-0.5 rounded-full">
                  Approve / Edit / Reject
                </span>
              </div>
              <div className="absolute inset-0 rounded-xl border-2 border-amber-300/40 animate-middleware-pulse" style={{ animationDelay: '1000ms' }} />
            </div>
          </div>
        </div>

        {/* Escalation Level Cards */}
        <div className="flex items-stretch gap-3 justify-center animate-fade-up" style={{ animationDelay: '800ms' }}>
          {levels.map((l) => (
            <div
              key={l.level}
              className="level-card relative rounded-xl px-4 py-3 transition-all duration-500 border-2 flex-1 max-w-[160px]"
              style={{
                background: activeLevel === l.level
                  ? `linear-gradient(135deg, ${l.bgFrom}, ${l.bgTo})`
                  : '#fafafa',
                borderColor: activeLevel === l.level ? l.color + '40' : '#e5e7eb',
                transform: activeLevel === l.level ? 'translateY(-4px) scale(1.04)' : 'translateY(0) scale(1)',
                boxShadow: activeLevel === l.level ? `0 8px 30px -8px ${l.color}30` : 'none',
              }}
            >
              {/* Active indicator */}
              {activeLevel === l.level && (
                <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-3 h-3 rounded-full animate-pulse-dot"
                  style={{ background: l.color, boxShadow: `0 0 12px ${l.color}60` }}
                />
              )}
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-lg flex items-center justify-center"
                  style={{ background: activeLevel === l.level ? l.color : '#d1d5db', color: 'white' }}>
                  {l.icon}
                </div>
                <div>
                  <p className="text-[9px] font-bold uppercase tracking-widest" style={{ color: activeLevel === l.level ? l.color : '#9ca3af' }}>Level {l.level}</p>
                  <p className="text-xs font-bold text-gray-800">{l.label}</p>
                </div>
              </div>
              <div className="space-y-1">
                {l.tools.map((t) => (
                  <div key={t} className="text-[10px] font-medium text-gray-600 bg-white/80 rounded-md px-2 py-0.5 truncate border border-gray-100">
                    {t}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Floating particles */}
        {[0, 1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="flow-particle absolute w-2 h-2 rounded-full"
            style={{
              background: `linear-gradient(135deg, #FF6B35, #FF8F65)`,
              left: `${20 + i * 15}%`,
              top: `${10 + (particlePhase + i) % 6 * 14}%`,
              opacity: ((particlePhase + i) % 6) < 4 ? 0.6 : 0,
              transition: 'all 0.8s ease-in-out',
              boxShadow: '0 0 8px rgba(255, 107, 53, 0.4)',
            }}
          />
        ))}
      </div>
    </div>
  )
}

// ─── Feature Cards ───────────────────────────────────────────────────────────

const features = [
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
    desc: 'When it&apos;s time to add interest, the math is done for you — based on your terms, the balance, and how long it&apos;s been overdue.',
    color: '#0d9488',
    bg: 'from-teal-50 to-emerald-50',
    border: 'border-teal-200/60',
  },
  {
    icon: <Scale className="w-5 h-5" />,
    title: 'Ready for small-claims, if you need it',
    desc: 'When a dispute really has to go legal, the agent looks up the actual filing procedure for the client&apos;s jurisdiction and gives you a step-by-step path to court.',
    color: '#ef4444',
    bg: 'from-rose-50 to-red-50',
    border: 'border-rose-200/60',
  },
  {
    icon: <MessageSquare className="w-5 h-5" />,
    title: 'Telegram alerts when it matters',
    desc: 'The moment a client replies — or the agent decides it&apos;s time to escalate — you get a ping on Telegram so nothing slips.',
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

// ─── How It Works Steps ──────────────────────────────────────────────────────

const steps = [
  { step: '01', title: 'Drop the invoice PDF', desc: 'Upload the original invoice (PDF or DOCX). InvoiceChaser reads it and pre-fills the client, amount, due date, and jurisdiction — no retyping.' },
  { step: '02', title: 'AI drafts the email', desc: 'The agent writes a reminder tuned to how overdue the invoice is and to your client&apos;s tone. No blank-page anxiety.' },
  { step: '03', title: 'You approve in one click', desc: 'Read the draft, edit anything you want, or reject it. Nothing leaves your Gmail until you say so.' },
  { step: '04', title: 'It escalates if needed', desc: 'No response after a few rounds? The agent gets firmer, calculates late fees, and prepares a small-claims notice when the time is right.' },
]

// ─── Tech Stack Badges ───────────────────────────────────────────────────────

const techStack = [
  { name: 'LangChain', color: '#1C3C3C' },
  { name: 'LangGraph', color: '#1C3C3C' },
  { name: 'Groq', color: '#F55036' },
  { name: 'LLaMA 3.3', color: '#0467C8' },
  { name: 'Tavily', color: '#5B21B6' },
  { name: 'FastAPI', color: '#009688' },
  { name: 'React', color: '#61DAFB' },
  { name: 'Tailwind', color: '#38BDF8' },
  { name: 'Vercel', color: '#000000' },
  { name: 'MCP', color: '#FF6B35' },
]

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

              <p className="text-lg text-gray-500 leading-relaxed mb-8 max-w-lg">
                Late invoices kill freelancers and small businesses. InvoiceChaser handles the awkward follow-ups for you — it drafts polite reminders, firm demand letters, even small-claims notices when needed. You stay in control: nothing leaves your inbox until you say yes.
              </p>

              <div className="flex flex-wrap gap-3 mb-10">
                <button
                  onClick={() => setShowGuestModal(true)}
                  className="inline-flex items-center gap-2.5 btn-gradient text-white text-sm font-bold rounded-xl px-7 py-3.5 shadow-lg shadow-orange-300/40 hover:shadow-orange-400/60 transition-all font-[family-name:var(--font-heading)] group"
                >
                  <Play className="w-4 h-4 group-hover:scale-110 transition-transform" />
                  Live Demo
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </button>
                <button
                  onClick={handleGoogleSignIn}
                  className="inline-flex items-center gap-2.5 bg-white hover:bg-gray-50 text-gray-700 text-sm font-bold rounded-xl px-7 py-3.5 shadow-sm border border-gray-200 transition-all font-[family-name:var(--font-heading)]"
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                  </svg>
                  Sign in with Google
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

            {/* Right — 3D Agent Flow Animation */}
            <div className="animate-fade-up" style={{ animationDelay: '300ms' }}>
              <AgentFlowVisualization />
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

      {/* ──── Tech Stack ──── */}
      <section className="py-20 bg-gradient-to-b from-transparent to-white/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10 animate-fade-up">
            <h3 className="text-2xl font-extrabold text-gray-900 font-[family-name:var(--font-heading)] tracking-tight mb-3">
              Built with
            </h3>
            <div className="flex flex-wrap items-center justify-center gap-3">
              {techStack.map((t, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1.5 text-xs font-bold px-4 py-2 rounded-full border shadow-sm bg-white animate-fade-up"
                  style={{ animationDelay: `${i * 60}ms`, borderColor: t.color + '20', color: t.color }}
                >
                  <span className="w-2 h-2 rounded-full" style={{ background: t.color }} />
                  {t.name}
                </span>
              ))}
            </div>
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
                  Live Demo
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
                  Sign in with Google
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
            <span>&middot; Built with LangChain &amp; Groq</span>
          </div>
          <div className="flex items-center gap-4 text-xs text-gray-400">
            <a href="https://github.com" target="_blank" rel="noopener" className="hover:text-[#FF6B35] transition-colors font-medium">GitHub</a>
            <span>&middot;</span>
            <span>Powered by LLaMA 3.3 70B</span>
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
    </div>
  )
}
