import {
  apiBaseUrl,
  authenticatedFetch,
  parseJsonResponse,
} from './client'
import type {
  ArtifactData,
  IndexingStageName,
  IndexPipelineRun,
  IndexPipelineRunDetail,
  RunIndexJobResponse,
  RunSourceIndexingInput,
  StageArtifacts,
  Source,
  UploadSourceInput,
} from '@/types'

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

  const response = await authenticatedFetch(`${apiBaseUrl}/api/v1/sources/upload`, {
    method: 'POST',
    body: formData,
  })

  return parseJsonResponse<Source>(response)
}

export async function runSourceIndexing(
  input: RunSourceIndexingInput,
): Promise<RunIndexJobResponse> {
  const { sourceId, ...request } = input
  const response = await authenticatedFetch(
    `${apiBaseUrl}/api/v1/sources/${encodeURIComponent(sourceId)}/index`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    },
  )

  return parseJsonResponse<RunIndexJobResponse>(response)
}

export async function listIndexPipelineRuns(input: {
  sourceId: string
  limit?: number
}): Promise<IndexPipelineRun[]> {
  const limit = input.limit ?? 20
  const response = await authenticatedFetch(
    `${apiBaseUrl}/api/v1/sources/${encodeURIComponent(input.sourceId)}/index/runs?limit=${limit}`,
  )
  return parseJsonResponse<IndexPipelineRun[]>(response)
}

export async function listLatestIndexPipelineRuns(input?: {
  limit?: number
}): Promise<IndexPipelineRun[]> {
  const limit = input?.limit ?? 100
  const response = await authenticatedFetch(
    `${apiBaseUrl}/api/v1/indexing/runs/latest?limit=${limit}`,
  )
  return parseJsonResponse<IndexPipelineRun[]>(response)
}

export async function getIndexPipelineRun(runId: string): Promise<IndexPipelineRunDetail> {
  const response = await authenticatedFetch(
    `${apiBaseUrl}/api/v1/indexing/runs/${encodeURIComponent(runId)}`,
  )
  return parseJsonResponse<IndexPipelineRunDetail>(response)
}

export async function getIndexPipelineStageArtifacts(input: {
  runId: string
  stageName: IndexingStageName
}): Promise<StageArtifacts> {
  const response = await authenticatedFetch(
    `${apiBaseUrl}/api/v1/indexing/runs/${encodeURIComponent(
      input.runId,
    )}/stages/${encodeURIComponent(input.stageName)}/artifacts`,
  )
  return parseJsonResponse<StageArtifacts>(response)
}

export async function getIndexArtifactData(input: {
  artifactId: string
  offset?: number
  limit?: number
}): Promise<ArtifactData> {
  const offset = input.offset ?? 0
  const limit = input.limit ?? 50
  const response = await authenticatedFetch(
    `${apiBaseUrl}/api/v1/indexing/artifacts/${encodeURIComponent(
      input.artifactId,
    )}?offset=${offset}&limit=${limit}`,
  )
  return parseJsonResponse<ArtifactData>(response)
}
