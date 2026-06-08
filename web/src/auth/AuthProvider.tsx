import { type ReactNode, useEffect, useState } from 'react'
import { login as loginRequest, logout as logoutRequest } from '@/api/auth'
import {
  refreshAccessToken,
  setAccessToken,
  setUnauthorizedHandler,
} from '@/api/client'
import { AuthContext, type AuthStatus } from './authContext'
import type { AuthUser, LoginRequest } from '@/types'

type AuthProviderProps = {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [user, setUser] = useState<AuthUser | null>(null)

  useEffect(() => {
    let cancelled = false
    setUnauthorizedHandler(() => {
      setAccessToken(null)
      setUser(null)
      setStatus('unauthenticated')
    })

    refreshAccessToken()
      .then((payload) => {
        if (cancelled) {
          return
        }
        if (payload) {
          setUser(payload.user)
          setStatus('authenticated')
          return
        }
        setUser(null)
        setStatus('unauthenticated')
      })
      .catch(() => {
        if (!cancelled) {
          setUser(null)
          setStatus('unauthenticated')
        }
      })

    return () => {
      cancelled = true
      setUnauthorizedHandler(null)
    }
  }, [])

  async function login(request: LoginRequest): Promise<AuthUser> {
    const payload = await loginRequest(request)
    setUser(payload.user)
    setStatus('authenticated')
    return payload.user
  }

  async function logout(): Promise<void> {
    await logoutRequest()
    setUser(null)
    setStatus('unauthenticated')
  }

  function canAccessRoute(routePath: string): boolean {
    return Boolean(user?.route_permissions.includes(routePath))
  }

  return (
    <AuthContext.Provider value={{ status, user, login, logout, canAccessRoute }}>
      {children}
    </AuthContext.Provider>
  )
}
