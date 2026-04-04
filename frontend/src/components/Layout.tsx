import { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Zap, User } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

export default function Layout({ children }: { children: ReactNode }) {
  const { user, signOut } = useAuth()

  return (
    <div className="min-h-screen bg-mesh noise">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white/70 backdrop-blur-xl border-b border-orange-100/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link to="/dashboard" className="flex items-center gap-3 group">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#FF6B35] to-[#FF8F65] flex items-center justify-center shadow-lg shadow-orange-300/40 group-hover:shadow-orange-400/50 transition-shadow">
                <Zap className="w-5 h-5 text-white" strokeWidth={2.5} />
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900 leading-tight font-[family-name:var(--font-heading)] tracking-tight">
                  Invoice<span className="text-[#FF6B35]">Chaser</span>
                </h1>
                <p className="text-[10px] font-medium text-gray-400 uppercase tracking-[0.15em] leading-tight">
                  AI Payment Recovery
                </p>
              </div>
            </Link>
            <div className="flex items-center gap-3">
              <div className="hidden sm:flex items-center gap-1.5 text-xs font-medium text-teal-700 bg-teal-50 px-3 py-1.5 rounded-full border border-teal-200/60">
                <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse-dot" />
                Powered by LangChain + Groq
              </div>
              {user && (
                <div className="flex items-center gap-3">
                  {user.picture ? (
                    <img src={user.picture} alt="" className="w-8 h-8 rounded-full" />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#FF6B35] to-[#FF8F65] flex items-center justify-center">
                      <User className="w-4 h-4 text-white" />
                    </div>
                  )}
                  <span className="text-sm text-zinc-400">{user.email}</span>
                  <button
                    onClick={signOut}
                    className="text-sm text-zinc-500 hover:text-white transition-colors"
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  )
}
