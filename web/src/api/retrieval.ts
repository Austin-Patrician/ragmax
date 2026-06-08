import { apiClient, assertApiData } from './client'
import type {
  RetrievalAnswerRequest,
  RetrievalAnswerResponse,
  RetrievalSearchRequest,
  RetrievalSearchResponse,
} from '@/types'

export async function searchRetrieval(
  request: RetrievalSearchRequest,
): Promise<RetrievalSearchResponse> {
  const { data, error } = await apiClient.POST('/api/v1/retrieval/search', {
    body: request,
  })
  return assertApiData(data, error)
}

export async function answerRetrieval(
  request: RetrievalAnswerRequest,
): Promise<RetrievalAnswerResponse> {
  const { data, error } = await apiClient.POST('/api/v1/retrieval/answer', {
    body: request,
  })
  return assertApiData(data, error)
}
