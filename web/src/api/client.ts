import createClient from 'openapi-fetch'
import type { paths } from './schema'

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() ?? ''

export const apiBaseUrl = configuredBaseUrl.replace(/\/$/, '')

export const apiClient = createClient<paths>({
  baseUrl: apiBaseUrl,
})

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
