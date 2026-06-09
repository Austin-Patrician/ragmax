export type UserSettingsProfile = {
  user_id: string
  username: string
  route_permissions: string[]
}

export type RuntimeConfigurationField = {
  key: string
  label: string
  section: string
  value_type: 'string' | 'integer' | 'float' | 'boolean' | 'secret' | 'path' | 'select'
  secret: boolean
  options: string[]
  source: 'db' | 'env'
  value: string | number | boolean | null
  is_configured: boolean
  masked_value: string | null
}

export type RuntimeConfigurationResponse = {
  fields: RuntimeConfigurationField[]
}

export type ProviderModel = {
  model_id: string
  provider_id: string
  model_name: string
  display_name: string | null
  ai_type: ModelAiType
  dimension: number | null
  context_window: number | null
  max_tokens: number | null
  is_enabled: boolean
  created_at: string | null
  updated_at: string | null
}

export type ModelAiType =
  | 'llm'
  | 'embedding'
  | 'rerank'
  | 'vlm'
  | 'asr'
  | 'tts'
  | 'ocr'
  | 'moderation'

export type ModelProvider = {
  provider_id: string
  name: string
  provider_type: ProviderType
  base_url: string | null
  api_key_configured: boolean
  api_key_masked: string | null
  is_enabled: boolean
  models: ProviderModel[]
  created_at: string | null
  updated_at: string | null
}

export type ProviderType = 'openai_compatible' | 'local_hash' | 'local_bge'

export type ProviderPreset = {
  name: string
  provider_type: ProviderType
  base_url: string | null
  capabilities: ModelAiType[]
}

export type ModelDefaultBinding = {
  binding_key: ModelBindingKey
  model_id: string
  updated_by: string | null
  created_at: string | null
  updated_at: string | null
}

export type ModelBindingKey = 'answer_llm' | 'query_llm' | 'embedding' | 'rerank'

export type ModelProviderSettings = {
  providers: ModelProvider[]
  defaults: ModelDefaultBinding[]
  presets: ProviderPreset[]
  ai_types: ModelAiType[]
  binding_keys: ModelBindingKey[]
  provider_types: ProviderType[]
}

export type CreateModelProviderInput = {
  name: string
  provider_type: ProviderType
  base_url?: string | null
  api_key?: string | null
  is_enabled?: boolean
}

export type CreateProviderModelInput = {
  model_name: string
  display_name?: string | null
  ai_type: ModelAiType
  dimension?: number | null
  context_window?: number | null
  max_tokens?: number | null
  is_enabled?: boolean
}
