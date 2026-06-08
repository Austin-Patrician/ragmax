import createClient from 'openapi-fetch'
import type { paths } from './schema'
import type { AuthTokenResponse } from '@/types'

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() ?? ''

export const apiBaseUrl = configuredBaseUrl.replace(/\/$/, '')

let accessToken: string | null = null
let refreshPromise: Promise<AuthTokenResponse | null> | null = null
let unauthorizedHandler: (() => void) | null = null

export const apiClient = createClient<paths>({
  baseUrl: apiBaseUrl,
  fetch: authenticatedFetch,
})

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function getAccessToken() {
  return accessToken
}

export function setUnauthorizedHandler(handler: (() => void) | null) {
  unauthorizedHandler = handler
}

export async function refreshAccessToken(): Promise<AuthTokenResponse | null> {
  if (refreshPromise) {
    return refreshPromise
  }

  refreshPromise = (async () => {
    const response = await fetch(`${apiBaseUrl}/api/v1/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    })
    if (!response.ok) {
      setAccessToken(null)
      return null
    }

    const payload = (await response.json()) as AuthTokenResponse
    setAccessToken(payload.access_token)
    return payload
  })()

  try {
    return await refreshPromise
  } finally {
    refreshPromise = null
  }
}

export async function authenticatedFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const response = await fetch(_requestWithAuth(input, init))
  if (response.status !== 401) {
    return response
  }

  const refreshed = await refreshAccessToken()
  if (!refreshed) {
    unauthorizedHandler?.()
    return response
  }

  return fetch(_requestWithAuth(input, init))
}

export async function parseJsonResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json().catch(() => null)) as unknown
  if (!response.ok) {
    throw payload
  }

  return payload as T
}

export function assertApiData<T>(data: T | undefined, error: unknown): T {
  if (error) {
    throw error
  }

  if (data === undefined) {
    throw new Error('No response data received.')
  }

  return data
}

function _requestWithAuth(input: RequestInfo | URL, init?: RequestInit): Request {
  const request = new Request(input, { ...init, credentials: 'include' })
  const headers = new Headers(request.headers)
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }
  return new Request(request, { headers, credentials: 'include' })
}
