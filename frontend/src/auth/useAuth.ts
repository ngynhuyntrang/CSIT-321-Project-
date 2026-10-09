import { createContext, useContext } from 'react'
import type { User } from '../types/auth'

export interface AuthState {
  user: User | null
  /** True until the stored token (if any) has been checked against /auth/me. */
  loading: boolean
  login: (email: string, password: string, rememberMe: boolean) => Promise<User>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
