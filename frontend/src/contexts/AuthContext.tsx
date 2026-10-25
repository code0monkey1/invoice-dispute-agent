import { createContext, useContext, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { api } from '../api'
import type { User } from '../types'
import { qk } from '../hooks/queries'
import { clearCache } from '../queryClient'

interface AuthContextType {
  user: User | null
  isGuest: boolean
  loading: boolean
  signIn: () => Promise<void>
  connectGmail: () => Promise<void>
  signOut: () => Promise<void>
  enterAsGuest: (name: string) => void
}

const AuthContext = createContext<AuthContextType | null>(null)

// Login CSRF protection: each Google redirect carries a random state that
// this browser remembers, and the callback rejects any other state.
export const OAUTH_STATE_KEY = 'invoicechaser_oauth_state'

function withOAuthState(url: string): string {
  const state = crypto.randomUUID()
  sessionStorage.setItem(OAUTH_STATE_KEY, state)
  const u = new URL(url)
  u.searchParams.set('state', state)
  return u.toString()
}

export function AuthProvider({ children }: { children: ReactNode }) {
  // The saved user renders immediately; the cached /me check below keeps
  // flags like gmail_connected current without blocking the first paint.
  const [savedUser, setUser] = useState<User | null>(() => {
    try {
      const saved = localStorage.getItem('invoicechaser_user')
      return saved ? JSON.parse(saved) : null
    } catch {
      return null
    }
  })
  const loading = false
  const me = useQuery({
    queryKey: qk.me,
    queryFn: async () => {
      const { user: fresh } = await api.getMe()
      localStorage.setItem('invoicechaser_user', JSON.stringify(fresh))
      return fresh
    },
    enabled: Boolean(localStorage.getItem('invoicechaser_token')),
    staleTime: 5 * 60_000,
  })
  const user = me.data ?? savedUser

  const signIn = async () => {
    const { url } = await api.getGoogleAuthUrl()
    window.location.href = withOAuthState(url)
  }

  // Asks Google for send-only Gmail access, separately from sign-in.
  const connectGmail = async () => {
    const { url } = await api.getGmailConnectUrl()
    window.location.href = withOAuthState(url)
  }

  const signOut = async () => {
    localStorage.removeItem('invoicechaser_token')
    localStorage.removeItem('invoicechaser_user')
    setUser(null)
    // Invoice data must not stay in this browser after signing out.
    await clearCache()
    window.location.href = '/'
  }

  const enterAsGuest = (name: string) => {
    const guestUser: User = {
      id: 'guest',
      email: '',
      name,
      picture: '',
    }
    localStorage.setItem('invoicechaser_user', JSON.stringify(guestUser))
    void clearCache()
    setUser(guestUser)
  }

  // A guest is any user without a real auth token. The frontend marker is
  // the legacy 'guest' id; the backend independently tracks each guest via
  // an HTTP-only cookie (ic_guest_session) so data stays isolated per browser.
  const isGuest = !!user && (user.id === 'guest' || !user.email)

  return (
    <AuthContext.Provider value={{ user, isGuest, loading, signIn, connectGmail, signOut, enterAsGuest }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export function handleGoogleCallback(token: string, user: User) {
  localStorage.setItem('invoicechaser_token', token)
  localStorage.setItem('invoicechaser_user', JSON.stringify(user))
}
