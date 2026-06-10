import type { RunIndexJobRequest } from './api'

export type UploadSourceInput = {
  file: File
  notebookId: string
  sourceId?: string
  metadata?: string
}

export type RunSourceIndexingInput = {
  sourceId: string
  capture_artifacts?: boolean
} & RunIndexJobRequest

export type Dataset = {
  dataset_id: string
  name: string
  description: string | null
  config: Record<string, unknown>
  metadata: Record<string, unknown>
  created_at: string | null
  updated_at: string | null
}

export type DatasetFile = {
  id: number
  dataset_id: string
  source_id: string
  added_at: string | null
}

export type DatasetWithFiles = {
  dataset: Dataset
  files: DatasetFile[]
  file_count: number
}

export type CreateDatasetInput = {
  name: string
  dataset_id?: string
  description?: string
  config?: Record<string, unknown>
  metadata?: Record<string, unknown>
}

export type UpdateDatasetInput = {
  name?: string
  description?: string
  config?: Record<string, unknown>
  metadata?: Record<string, unknown>
}

export type AddFilesToDatasetInput = {
  source_ids: string[]
}

export type IndexingStageName =
  | 'source'
  | 'parse_blocks'
  | 'analyze_profile'
  | 'chunk_nodes'
  | 'quality_enrich'
  | 'vectorize'

export type IndexPipelineRun = {
  run_id: string
  source_id: string
  status: string
  requested_profile: string | null
  effective_profile: string | null
  requested_parser: string | null
  effective_parser: string | null
  overrides: Record<string, unknown>
  summary: Record<string, unknown>
  error_message: string | null
  created_at: string | null
  started_at: string | null
  finished_at: string | null
}

export type IndexStageRun = {
  stage_run_id: string
  run_id: string
  stage_name: IndexingStageName
  status: string
  sequence_no: number
  stale: boolean
  summary: Record<string, unknown>
  error_message: string | null
  started_at: string | null
  finished_at: string | null
  duration_ms: number | null
  artifact_count: number
}

export type IndexArtifactManifest = {
  artifact_id: string
  run_id: string
  stage_run_id: string
  stage_name: IndexingStageName
  artifact_type: string
  storage_uri: string
  payload_format: string
  content_hash: string
  size_bytes: number
  record_count: number
  preview: Record<string, unknown>
  created_at: string | null
}

export type IndexPipelineRunDetail = {
  run: IndexPipelineRun
  stages: IndexStageRun[]
}

export type StageArtifacts = {
  stage_run: IndexStageRun | null
  manifests: IndexArtifactManifest[]
}

export type ArtifactData = {
  manifest: IndexArtifactManifest
  data: Record<string, unknown> | Record<string, unknown>[]
  has_more: boolean
}
