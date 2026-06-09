import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { deleteSource, getSource, listSources } from '@/api/sources'

export const sourceKeys = {
  all: ['sources'] as const,
  lists: () => [...sourceKeys.all, 'list'] as const,
  list: (filters: { limit?: number; offset?: number }) =>
    [...sourceKeys.lists(), filters] as const,
  details: () => [...sourceKeys.all, 'detail'] as const,
  detail: (id: string) => [...sourceKeys.details(), id] as const,
}

export function useSources(params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: sourceKeys.list(params ?? {}),
    queryFn: () => listSources(params),
  })
}

export function useSource(sourceId: string | undefined) {
  return useQuery({
    queryKey: sourceKeys.detail(sourceId!),
    queryFn: () => getSource(sourceId!),
    enabled: !!sourceId,
  })
}

export function useDeleteSource() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (sourceId: string) => deleteSource(sourceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sourceKeys.all })
    },
  })
}
