import { useMutation, useQuery } from '@tanstack/react-query'
import {
  getIndexingArtifacts,
  listIndexingProfiles,
  listSourceParsers,
  previewSourceIndexing,
  runSourceIndexing,
  uploadSource,
} from '@/api/indexing'
import { queryKeys } from './queryKeys'

export function useIndexingProfiles() {
  return useQuery({
    queryKey: queryKeys.indexing.profiles,
    queryFn: listIndexingProfiles,
  })
}

export function useSourceParsers() {
  return useQuery({
    queryKey: queryKeys.indexing.parsers,
    queryFn: listSourceParsers,
  })
}

export function useUploadSource() {
  return useMutation({
    mutationFn: uploadSource,
  })
}

export function usePreviewSourceIndexing() {
  return useMutation({
    mutationFn: previewSourceIndexing,
  })
}

export function useRunSourceIndexing() {
  return useMutation({
    mutationFn: runSourceIndexing,
  })
}

export function useIndexingArtifacts(jobId: string | null) {
  return useQuery({
    queryKey: jobId ? queryKeys.indexing.artifacts(jobId) : queryKeys.indexing.emptyArtifacts,
    queryFn: () => getIndexingArtifacts(jobId ?? ''),
    enabled: Boolean(jobId),
  })
}
