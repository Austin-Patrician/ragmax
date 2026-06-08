import type { RunIndexJobRequest } from '@/types'

export function buildIndexRequest(
  profileName: string | null,
  parserName: string | null,
  chunkSize: string | number,
  chunkOverlap: string | number,
): RunIndexJobRequest {
  const request: RunIndexJobRequest = {}
  const overrides: NonNullable<RunIndexJobRequest['overrides']> = {}

  if (profileName) {
    request.profile_name = profileName
  }
  if (parserName) {
    request.parser_name = parserName
  }
  if (typeof chunkSize === 'number') {
    overrides.chunk_size = chunkSize
  }
  if (typeof chunkOverlap === 'number') {
    overrides.chunk_overlap = chunkOverlap
  }
  if (Object.keys(overrides).length > 0) {
    request.overrides = overrides
  }

  return request
}
