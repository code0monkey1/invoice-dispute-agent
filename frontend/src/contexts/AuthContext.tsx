import type { ReactNode } from 'react'
import { AuthContext } from './auth'
import { useAuthSession } from '../hooks/useAuthSession'

export function AuthProvider({ children }: { children: ReactNode }) {
  const session = useAuthSession()
  return <AuthContext.Provider value={session}>{children}</AuthContext.Provider>
}
