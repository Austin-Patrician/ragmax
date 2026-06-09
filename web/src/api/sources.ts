import { apiBaseUrl, authenticatedFetch, parseJsonResponse } from './client'
import type { Source } from '@/types'

export async function listSources(params?: {
  limit?: number
  offset?: number
}): Promise<Source[]> {
  const limit = params?.limit ?? 100
  const offset = params?.offset ?? 0
  const response = await authenticatedFetch(
    `${apiBaseUrl}/api/v1/sources?limit=${limit}&offset=${offset}`,
  )
  return parseJsonResponse<Source[]>(response)
}

export async function getSource(sourceId: string): Promise<Source> {
  const response = await authenticatedFetch(
    `${apiBaseUrl}/api/v1/sources/${encodeURIComponent(sourceId)}`,
  )
  return parseJsonResponse<Source>(response)
}

export async function deleteSource(sourceId: string): Promise<void> {
  await authenticatedFetch(`${apiBaseUrl}/api/v1/sources/${encodeURIComponent(sourceId)}`, {
    method: 'DELETE',
  })
}
