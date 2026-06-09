import { apiBaseUrl, authenticatedFetch, parseJsonResponse } from './client'
import type {
  AddFilesToDatasetInput,
  CreateDatasetInput,
  Dataset,
  DatasetFile,
  DatasetWithFiles,
  UpdateDatasetInput,
} from '@/types'

export async function createDataset(input: CreateDatasetInput): Promise<Dataset> {
  const response = await authenticatedFetch(`${apiBaseUrl}/api/v1/datasets`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  return parseJsonResponse<Dataset>(response)
}

export async function listDatasets(params?: {
  limit?: number
  offset?: number
}): Promise<Dataset[]> {
  const limit = params?.limit ?? 100
  const offset = params?.offset ?? 0
  const response = await authenticatedFetch(
    `${apiBaseUrl}/api/v1/datasets?limit=${limit}&offset=${offset}`,
  )
  return parseJsonResponse<Dataset[]>(response)
}

export async function getDataset(datasetId: string): Promise<DatasetWithFiles> {
  const response = await authenticatedFetch(
    `${apiBaseUrl}/api/v1/datasets/${encodeURIComponent(datasetId)}`,
  )
  return parseJsonResponse<DatasetWithFiles>(response)
}

export async function updateDataset(
  datasetId: string,
  input: UpdateDatasetInput,
): Promise<Dataset> {
  const response = await authenticatedFetch(
    `${apiBaseUrl}/api/v1/datasets/${encodeURIComponent(datasetId)}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    },
  )
  return parseJsonResponse<Dataset>(response)
}

export async function deleteDataset(datasetId: string): Promise<void> {
  await authenticatedFetch(`${apiBaseUrl}/api/v1/datasets/${encodeURIComponent(datasetId)}`, {
    method: 'DELETE',
  })
}

export async function addFilesToDataset(
  datasetId: string,
  input: AddFilesToDatasetInput,
): Promise<DatasetFile[]> {
  const response = await authenticatedFetch(
    `${apiBaseUrl}/api/v1/datasets/${encodeURIComponent(datasetId)}/files`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    },
  )
  return parseJsonResponse<DatasetFile[]>(response)
}

export async function removeFileFromDataset(
  datasetId: string,
  sourceId: string,
): Promise<void> {
  await authenticatedFetch(
    `${apiBaseUrl}/api/v1/datasets/${encodeURIComponent(datasetId)}/files/${encodeURIComponent(sourceId)}`,
    {
      method: 'DELETE',
    },
  )
}

export async function listDatasetFiles(datasetId: string): Promise<DatasetFile[]> {
  const response = await authenticatedFetch(
    `${apiBaseUrl}/api/v1/datasets/${encodeURIComponent(datasetId)}/files`,
  )
  return parseJsonResponse<DatasetFile[]>(response)
}
