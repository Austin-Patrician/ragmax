import { useMutation, useQuery } from '@tanstack/react-query'
import {
  getIndexArtifactData,
  getIndexPipelineRun,
  getIndexPipelineStageArtifacts,
  listIndexPipelineRuns,
  uploadSource,
} from '@/api/indexing'
import { listDatasets } from '@/api/datasets'
import type { IndexingStageName } from '@/types'
import { queryKeys } from './queryKeys'

export function useUploadSource() {
  return useMutation({
    mutationFn: uploadSource,
  })
}

export function useIndexPipelineRuns(sourceId: string | null) {
  return useQuery({
    queryKey: sourceId
      ? queryKeys.indexing.pipelineRuns(sourceId)
      : queryKeys.indexing.pipelineRuns('empty'),
    queryFn: () => listIndexPipelineRuns({ sourceId: sourceId ?? '' }),
    enabled: Boolean(sourceId),
  })
}

export function useIndexPipelineRun(runId: string | null) {
  return useQuery({
    queryKey: runId ? queryKeys.indexing.pipelineRun(runId) : queryKeys.indexing.pipelineRun('empty'),
    queryFn: () => getIndexPipelineRun(runId ?? ''),
    enabled: Boolean(runId),
    refetchInterval: (query) => {
      const status = query.state.data?.run.status
      return status === 'running' || status === 'pending' ? 1500 : false
    },
  })
}

export function useIndexPipelineStageArtifacts(
  runId: string | null,
  stageName: IndexingStageName,
) {
  return useQuery({
    queryKey: runId
      ? queryKeys.indexing.stageArtifacts(runId, stageName)
      : queryKeys.indexing.stageArtifacts('empty', stageName),
    queryFn: () => getIndexPipelineStageArtifacts({ runId: runId ?? '', stageName }),
    enabled: Boolean(runId),
  })
}

export function useIndexArtifactData(
  artifactId: string | null,
  offset = 0,
  limit = 50,
) {
  return useQuery({
    queryKey: artifactId
      ? queryKeys.indexing.artifactData(artifactId, offset, limit)
      : queryKeys.indexing.artifactData('empty', offset, limit),
    queryFn: () => getIndexArtifactData({ artifactId: artifactId ?? '', offset, limit }),
    enabled: Boolean(artifactId),
  })
}

export function useDatasets() {
  return useQuery({
    queryKey: queryKeys.datasets.list(),
    queryFn: () => listDatasets(),
  })
}
