import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Zap, User } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

// The app shell uses the landing page's theme (the `lp` scope in index.css),
// so moving from the landing page into the app feels like one product.
export default function Layout({ children }: { children: ReactNode }) {
  const { user, isGuest, signOut } = useAuth()

  return (
    <div className="lp min-h-screen bg-[#FFF7F0] text-[#111827]">
      <header className="sticky top-0 z-50 bg-[#FFF7F0]/90 backdrop-blur border-b border-[#F1E4D8]">
        <div className="max-w-[1180px] mx-auto px-4 sm:px-8 h-16 flex items-center justify-between gap-4">
          <Link to="/dashboard" className="flex items-center gap-2.5">
            <span className="w-8 h-8 rounded-[10px] bg-gradient-to-br from-[#FF6B35] to-[#FF8F65] text-white shadow-md shadow-orange-300/40 flex items-center justify-center">
              <Zap className="w-4 h-4" strokeWidth={2.5} />
            </span>
            <span className="font-bold text-[19px] tracking-tight">Invoice<span className="text-[#FF6B35]">Chaser</span></span>
          </Link>

          {user && (
            <div className="flex items-center gap-3 sm:gap-4">
              {user.picture ? (
                <img src={user.picture} alt="" className="w-8 h-8 rounded-full" referrerPolicy="no-referrer" />
              ) : (
                <span className="w-8 h-8 rounded-full bg-[#FDEBDD] text-[#B4410E] flex items-center justify-center">
                  <User className="w-4 h-4" />
                </span>
              )}
              <span className="hidden sm:inline text-[15px] text-[#374151]">
                {isGuest ? (
                  <>
                    {user.name || 'Guest'}
                    <span className="ml-2 rounded-full bg-[#F6EDE3] text-[#6B7280] text-[13px] font-medium px-2 py-0.5">Demo</span>
                  </>
                ) : (
                  user.email
                )}
              </span>
              <button onClick={signOut} className="text-[15px] font-medium text-[#6B7280] hover:text-[#111827]">
                {isGuest ? 'Exit demo' : 'Sign out'}
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="max-w-[1180px] mx-auto px-4 sm:px-8 py-8 sm:py-10">
        {children}
      </main>
    </div>
  )
}
