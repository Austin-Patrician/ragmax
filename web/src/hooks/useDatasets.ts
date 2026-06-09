import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  addFilesToDataset,
  createDataset,
  deleteDataset,
  getDataset,
  listDatasets,
  removeFileFromDataset,
  updateDataset,
} from '@/api/datasets'
import type {
  AddFilesToDatasetInput,
  CreateDatasetInput,
  UpdateDatasetInput,
} from '@/types'

export const datasetKeys = {
  all: ['datasets'] as const,
  lists: () => [...datasetKeys.all, 'list'] as const,
  list: (filters: { limit?: number; offset?: number }) =>
    [...datasetKeys.lists(), filters] as const,
  details: () => [...datasetKeys.all, 'detail'] as const,
  detail: (id: string) => [...datasetKeys.details(), id] as const,
  files: (id: string) => [...datasetKeys.detail(id), 'files'] as const,
}

export function useDatasets(params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: datasetKeys.list(params ?? {}),
    queryFn: () => listDatasets(params),
  })
}

export function useDataset(datasetId: string | undefined) {
  return useQuery({
    queryKey: datasetKeys.detail(datasetId!),
    queryFn: () => getDataset(datasetId!),
    enabled: !!datasetId,
  })
}

export function useCreateDataset() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: CreateDatasetInput) => createDataset(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: datasetKeys.lists() })
    },
  })
}

export function useUpdateDataset() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ datasetId, input }: { datasetId: string; input: UpdateDatasetInput }) =>
      updateDataset(datasetId, input),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: datasetKeys.detail(variables.datasetId) })
      queryClient.invalidateQueries({ queryKey: datasetKeys.lists() })
    },
  })
}

export function useDeleteDataset() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (datasetId: string) => deleteDataset(datasetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: datasetKeys.all })
    },
  })
}

export function useAddFilesToDataset() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ datasetId, input }: { datasetId: string; input: AddFilesToDatasetInput }) =>
      addFilesToDataset(datasetId, input),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: datasetKeys.detail(variables.datasetId) })
      queryClient.invalidateQueries({ queryKey: datasetKeys.files(variables.datasetId) })
    },
  })
}

export function useRemoveFileFromDataset() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ datasetId, sourceId }: { datasetId: string; sourceId: string }) =>
      removeFileFromDataset(datasetId, sourceId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: datasetKeys.detail(variables.datasetId) })
      queryClient.invalidateQueries({ queryKey: datasetKeys.files(variables.datasetId) })
    },
  })
}
