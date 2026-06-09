import { apiBaseUrl, authenticatedFetch, parseJsonResponse } from './client'
import type {
  CreateModelProviderInput,
  CreateProviderModelInput,
  ModelProviderSettings,
  RuntimeConfigurationResponse,
  UserSettingsProfile,
} from '@/types'

export async function getUserSettingsProfile(): Promise<UserSettingsProfile> {
  const response = await authenticatedFetch(`${apiBaseUrl}/api/v1/user-settings/profile`)
  return parseJsonResponse<UserSettingsProfile>(response)
}

export async function getRuntimeConfiguration(): Promise<RuntimeConfigurationResponse> {
  const response = await authenticatedFetch(
    `${apiBaseUrl}/api/v1/user-settings/configuration`,
  )
  return parseJsonResponse<RuntimeConfigurationResponse>(response)
}

export async function updateRuntimeConfiguration(
  values: Record<string, unknown | null>,
): Promise<RuntimeConfigurationResponse> {
  const response = await authenticatedFetch(
    `${apiBaseUrl}/api/v1/user-settings/configuration`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ values }),
    },
  )
  return parseJsonResponse<RuntimeConfigurationResponse>(response)
}

export async function getModelProviderSettings(): Promise<ModelProviderSettings> {
  const response = await authenticatedFetch(
    `${apiBaseUrl}/api/v1/user-settings/model-providers`,
  )
  return parseJsonResponse<ModelProviderSettings>(response)
}

export async function createModelProvider(
  input: CreateModelProviderInput,
): Promise<ModelProviderSettings> {
  const response = await authenticatedFetch(
    `${apiBaseUrl}/api/v1/user-settings/model-providers`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    },
  )
  return parseJsonResponse<ModelProviderSettings>(response)
}

export async function deleteModelProvider(providerId: string): Promise<void> {
  await authenticatedFetch(
    `${apiBaseUrl}/api/v1/user-settings/model-providers/${encodeURIComponent(providerId)}`,
    { method: 'DELETE' },
  )
}

export async function createProviderModel(input: {
  providerId: string
  model: CreateProviderModelInput
}): Promise<ModelProviderSettings> {
  const response = await authenticatedFetch(
    `${apiBaseUrl}/api/v1/user-settings/model-providers/${encodeURIComponent(
      input.providerId,
    )}/models`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input.model),
    },
  )
  return parseJsonResponse<ModelProviderSettings>(response)
}

export async function deleteProviderModel(input: {
  providerId: string
  modelId: string
}): Promise<void> {
  await authenticatedFetch(
    `${apiBaseUrl}/api/v1/user-settings/model-providers/${encodeURIComponent(
      input.providerId,
    )}/models/${encodeURIComponent(input.modelId)}`,
    { method: 'DELETE' },
  )
}

export async function updateModelDefaults(
  bindings: Record<string, string | null>,
): Promise<ModelProviderSettings> {
  const response = await authenticatedFetch(
    `${apiBaseUrl}/api/v1/user-settings/model-providers/defaults`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bindings }),
    },
  )
  return parseJsonResponse<ModelProviderSettings>(response)
}
