import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createModelProvider,
  createProviderModel,
  deleteModelProvider,
  deleteProviderModel,
  getModelProviderSettings,
  getRuntimeConfiguration,
  getUserSettingsProfile,
  updateModelDefaults,
  updateRuntimeConfiguration,
} from '@/api/userSettings'
import { queryKeys } from './queryKeys'

export function useUserSettingsProfile() {
  return useQuery({
    queryKey: queryKeys.userSettings.profile,
    queryFn: getUserSettingsProfile,
  })
}

export function useRuntimeConfiguration() {
  return useQuery({
    queryKey: queryKeys.userSettings.configuration,
    queryFn: getRuntimeConfiguration,
  })
}

export function useUpdateRuntimeConfiguration() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateRuntimeConfiguration,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.userSettings.configuration })
    },
  })
}

export function useModelProviderSettings() {
  return useQuery({
    queryKey: queryKeys.userSettings.modelProviders,
    queryFn: getModelProviderSettings,
  })
}

export function useCreateModelProvider() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createModelProvider,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.userSettings.modelProviders })
    },
  })
}

export function useDeleteModelProvider() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteModelProvider,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.userSettings.modelProviders })
    },
  })
}

export function useCreateProviderModel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createProviderModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.userSettings.modelProviders })
    },
  })
}

export function useDeleteProviderModel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteProviderModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.userSettings.modelProviders })
    },
  })
}

export function useUpdateModelDefaults() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateModelDefaults,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.userSettings.modelProviders })
    },
  })
}
