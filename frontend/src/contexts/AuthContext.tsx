import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '../api'
import type { User } from '../types'

interface AuthContextType {
  user: User | null
  loading: boolean
  signIn: () => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('invoicechaser_token')
    const savedUser = localStorage.getItem('invoicechaser_user')
    if (token && savedUser) {
      setUser(JSON.parse(savedUser))
    }
    setLoading(false)
  }, [])

  const signIn = async () => {
    const { url } = await api.getGoogleAuthUrl()
    window.location.href = url
  }

  const signOut = () => {
    localStorage.removeItem('invoicechaser_token')
    localStorage.removeItem('invoicechaser_user')
    setUser(null)
    window.location.href = '/'
  }

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut }}>
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
