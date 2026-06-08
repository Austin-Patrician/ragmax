import {
  apiBaseUrl,
  getAccessToken,
  parseJsonResponse,
  setAccessToken,
} from './client'
import type { AuthTokenResponse, AuthUser, LoginRequest } from '@/types'

export async function login(request: LoginRequest): Promise<AuthTokenResponse> {
  const response = await fetch(`${apiBaseUrl}/api/v1/auth/login`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })
  const payload = await parseJsonResponse<AuthTokenResponse>(response)
  setAccessToken(payload.access_token)
  return payload
}

export async function logout(): Promise<void> {
  const headers = new Headers()
  const token = getAccessToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  await fetch(`${apiBaseUrl}/api/v1/auth/logout`, {
    method: 'POST',
    credentials: 'include',
    headers,
  }).catch(() => undefined)
  setAccessToken(null)
}

export async function getCurrentUser(): Promise<AuthUser> {
  const headers = new Headers()
  const token = getAccessToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  const response = await fetch(`${apiBaseUrl}/api/v1/auth/me`, {
    method: 'GET',
    credentials: 'include',
    headers,
  })
  return parseJsonResponse<AuthUser>(response)
}
