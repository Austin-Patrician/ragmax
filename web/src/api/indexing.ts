import { apiBaseUrl, apiClient, assertApiData, parseJsonResponse } from './client'
import type {
  IndexingArtifactsResponse,
  IndexingPreviewResponse,
  RunIndexJobRequest,
  RunIndexJobResponse,
  Source,
  UploadSourceInput,
} from '@/types'

export async function listIndexingProfiles() {
  const { data, error } = await apiClient.GET('/api/v1/indexing/profiles')
  return assertApiData(data, error)
}

export async function listSourceParsers() {
  const { data, error } = await apiClient.GET('/api/v1/indexing/parsers')
  return assertApiData(data, error)
}

export async function uploadSource(input: UploadSourceInput): Promise<Source> {
  const formData = new FormData()
  formData.append('file', input.file)
  formData.append('notebook_id', input.notebookId)

  if (input.sourceId) {
    formData.append('source_id', input.sourceId)
  }
  if (input.metadata) {
    formData.append('metadata', input.metadata)
  }

  const response = await fetch(`${apiBaseUrl}/api/v1/sources/upload`, {
    method: 'POST',
    body: formData,
  })

  return parseJsonResponse<Source>(response)
}

export async function previewSourceIndexing(input: {
  sourceId: string
  request: RunIndexJobRequest
}): Promise<IndexingPreviewResponse> {
  const { data, error } = await apiClient.POST('/api/v1/sources/{source_id}/index/preview', {
    params: { path: { source_id: input.sourceId } },
    body: input.request,
  })
  return assertApiData(data, error) as IndexingPreviewResponse
}

export async function runSourceIndexing(input: {
  sourceId: string
  request: RunIndexJobRequest
}): Promise<RunIndexJobResponse> {
  const { data, error } = await apiClient.POST('/api/v1/sources/{source_id}/index', {
    params: { path: { source_id: input.sourceId } },
    body: input.request,
  })
  return assertApiData(data, error)
}

export async function getIndexingArtifacts(jobId: string): Promise<IndexingArtifactsResponse> {
  const { data, error } = await apiClient.GET('/api/v1/indexing/jobs/{job_id}/artifacts', {
    params: { path: { job_id: jobId } },
  })
  return assertApiData(data, error) as IndexingArtifactsResponse
}
