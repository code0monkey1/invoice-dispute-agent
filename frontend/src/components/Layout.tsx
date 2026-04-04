import { ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Zap, LogOut, User } from 'lucide-react'

function getUser(): { name: string; type: string } | null {
  try {
    const raw = localStorage.getItem('invoicechaser_user')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export default function Layout({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const user = getUser()

  const handleSignOut = () => {
    localStorage.removeItem('invoicechaser_user')
    navigate('/')
  }

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
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-2 bg-gray-50 border border-gray-200/60 rounded-full pl-1.5 pr-3 py-1">
                    <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#FF6B35] to-[#FF8F65] flex items-center justify-center">
                      <User className="w-3 h-3 text-white" />
                    </div>
                    <span className="text-xs font-semibold text-gray-600">{user.name}</span>
                    {user.type === 'guest' && (
                      <span className="text-[9px] font-bold text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded-full border border-amber-200/60 uppercase tracking-wider">Guest</span>
                    )}
                  </div>
                  <button
                    onClick={handleSignOut}
                    className="text-gray-400 hover:text-rose-500 transition-colors p-1.5 rounded-lg hover:bg-rose-50"
                    title="Sign out"
                  >
                    <LogOut className="w-4 h-4" />
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
