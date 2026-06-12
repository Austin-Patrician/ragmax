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
  file_count?: number
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
  | 'chunk_nodes'
  | 'quality_enrich'
  | 'vectorize'

export type IndexPipelineRun = {
  run_id: string
  source_id: string
  status: string
  config: {
    parser?: string
    parser_config?: Record<string, unknown>
    chunker?: string
    chunk_config?: Record<string, unknown>
  }
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

// 新增：Chunker和Parser选项类型
export type ChunkerType =
  | 'fixed_token'
  | 'semantic_vector'
  | 'section_aware'
  | 'table_aware'
  | 'ocr_page'

export type ParserType =
  | 'simple_directory_reader'
  | 'llamaparse'
  | 'mineru'

export type ChunkConfig = {
  chunk_size?: number
  chunk_overlap?: number
  tokenizer_model?: string
  // Semantic Vector特定
  similarity_threshold_percentile?: number
  // Table Aware特定
  repeat_table_header?: boolean
  // Section Aware特定
  keep_headings?: boolean
}

export type ParserConfig = {
  // LlamaParse特定
  tier?: 'free' | 'premium'
  version?: string
  // MinerU特定
  enable_table?: boolean
  enable_formula?: boolean
}

export type IndexingConfig = {
  parser?: ParserType
  parser_config?: ParserConfig
  chunker?: ChunkerType
  chunk_config?: ChunkConfig
  capture_artifacts?: boolean
}
