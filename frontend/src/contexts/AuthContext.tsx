import { createContext, useContext, useState, useEffect } from 'react'
import type { ReactNode } from 'react'
import { api } from '../api'
import type { User } from '../types'

interface AuthContextType {
  user: User | null
  loading: boolean
  signIn: () => Promise<void>
  signOut: () => void
  enterAsGuest: (name: string) => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const savedUser = localStorage.getItem('invoicechaser_user')
    if (savedUser) {
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

  const enterAsGuest = (name: string) => {
    const guestUser: User = {
      id: 'guest',
      email: '',
      name,
      picture: '',
    }
    localStorage.setItem('invoicechaser_user', JSON.stringify(guestUser))
    setUser(guestUser)
  }

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut, enterAsGuest }}>
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
