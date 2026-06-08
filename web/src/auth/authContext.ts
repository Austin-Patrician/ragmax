import { createContext } from 'react'
import type { AuthUser, LoginRequest } from '@/types'

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated'

export type AuthContextValue = {
  status: AuthStatus
  user: AuthUser | null
  login: (request: LoginRequest) => Promise<AuthUser>
  logout: () => Promise<void>
  canAccessRoute: (routePath: string) => boolean
}

export const AuthContext = createContext<AuthContextValue | null>(null)
