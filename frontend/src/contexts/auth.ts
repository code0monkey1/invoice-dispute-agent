import { createContext, useContext } from 'react'
import type { User } from '../types'

// The auth context, hook and helpers. Kept apart from AuthProvider so that
// file exports only a component (React Fast Refresh needs that).

export interface AuthContextType {
  user: User | null
  isGuest: boolean
  loading: boolean
  signIn: () => Promise<void>
  connectGmail: () => Promise<void>
  signOut: () => Promise<void>
  enterAsGuest: (name: string) => void
}

export const AuthContext = createContext<AuthContextType | null>(null)

// Login CSRF protection: each Google redirect carries a random state that
// this browser remembers, and the callback rejects any other state.
export const OAUTH_STATE_KEY = 'invoicechaser_oauth_state'

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export function handleGoogleCallback(token: string, user: User) {
  localStorage.setItem('invoicechaser_token', token)
  localStorage.setItem('invoicechaser_user', JSON.stringify(user))
}
