import type { components } from '@/api/schema'
import type { ChunkerType, ParserType, ChunkConfig, ParserConfig } from './indexing'

export type Source = components['schemas']['SourceResponse']
export type RunIndexJobRequest = {
  parser?: ParserType
  parser_config?: ParserConfig
  chunker?: ChunkerType
  chunk_config?: ChunkConfig
  capture_artifacts?: boolean
}
export type RunIndexJobResponse = Omit<
  components['schemas']['RunIndexJobResponse'],
  'effective_profile'
> & {
  effective_chunker: string
  effective_config: Record<string, unknown>
}
export type RetrievalSearchRequest = components['schemas']['RetrievalSearchRequest']
export type RetrievalSearchResponse = components['schemas']['RetrievalSearchResponse']
export type RetrievalAnswerRequest = components['schemas']['RetrievalAnswerRequest']
export type RetrievalAnswerResponse = components['schemas']['RetrievalAnswerResponse']
