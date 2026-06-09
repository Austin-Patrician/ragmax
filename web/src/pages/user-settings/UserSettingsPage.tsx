import {
  Alert,
  Avatar,
  Badge,
  Button,
  Divider,
  Group,
  Loader,
  NumberInput,
  Paper,
  PasswordInput,
  ScrollArea,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import {
  Box,
  Check,
  Database,
  KeyRound,
  Plus,
  RotateCcw,
  Save,
  Settings,
  Sparkles,
  Trash2,
  User,
} from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  useCreateModelProvider,
  useCreateProviderModel,
  useDeleteModelProvider,
  useDeleteProviderModel,
  useModelProviderSettings,
  useRuntimeConfiguration,
  useUpdateModelDefaults,
  useUpdateRuntimeConfiguration,
  useUserSettingsProfile,
} from '@/hooks/useUserSettings'
import type {
  ModelAiType,
  ModelBindingKey,
  ProviderPreset,
  ProviderType,
  RuntimeConfigurationField,
} from '@/types'
import { formatApiError } from '@/utils/apiError'
import styles from './UserSettingsPage.module.css'

const classes = {
  avatarRow: styles.avatarRow ?? '',
  badgeDelete: styles.badgeDelete ?? '',
  configBoolean: styles.configBoolean ?? '',
  content: styles.content ?? '',
  formBody: styles.formBody ?? '',
  identity: styles.identity ?? '',
  identityAvatar: styles.identityAvatar ?? '',
  largeAvatar: styles.largeAvatar ?? '',
  modelsGrid: styles.modelsGrid ?? '',
  monoValue: styles.monoValue ?? '',
  navButton: styles.navButton ?? '',
  navButtonActive: styles.navButtonActive ?? '',
  page: styles.page ?? '',
  panel: styles.panel ?? '',
  panelHeader: styles.panelHeader ?? '',
  presetButton: styles.presetButton ?? '',
  presetMark: styles.presetMark ?? '',
  presets: styles.presets ?? '',
  profileRow: styles.profileRow ?? '',
  providerCard: styles.providerCard ?? '',
  sectionTitle: styles.sectionTitle ?? '',
  sidebar: styles.sidebar ?? '',
}

type SettingsSection = 'profile' | 'models' | 'configuration'

const SETTINGS_SECTIONS: Array<{
  key: SettingsSection
  icon: typeof User
  labelKey: string
}> = [
  { key: 'profile', icon: User, labelKey: 'settings.profile.title' },
  { key: 'models', icon: Box, labelKey: 'settings.modelProviders.title' },
  { key: 'configuration', icon: Settings, labelKey: 'settings.configuration.title' },
]

const BINDING_LABELS: Record<ModelBindingKey, string> = {
  answer_llm: 'Answer LLM',
  query_llm: 'Query LLM',
  embedding: 'Embedding',
  rerank: 'Rerank',
}

const BINDING_TYPES: Record<ModelBindingKey, ModelAiType> = {
  answer_llm: 'llm',
  query_llm: 'llm',
  embedding: 'embedding',
  rerank: 'rerank',
}

const CONFIG_SECTION_LABELS: Record<string, string> = {
  storage: 'Storage',
  parser: 'Parser / LlamaParse',
  vector: 'Vector / Qdrant',
  retrieval: 'Retrieval',
  query: 'Query processing',
  hybrid: 'Hybrid retrieval',
  reranking: 'Reranking',
  context: 'Context building',
  llm_runtime: 'LLM runtime',
}

export function UserSettingsPage() {
  const { t } = useTranslation()
  const [activeSection, setActiveSection] = useState<SettingsSection>('profile')
  const profile = useUserSettingsProfile()

  return (
    <div className={classes.page}>
      <aside className={classes.sidebar}>
        <div className={classes.identity}>
          <Avatar radius="xl" size={44} className={classes.identityAvatar}>
            {profile.data?.username.slice(0, 1).toUpperCase() ?? 'U'}
          </Avatar>
          <div>
            <Text fw={850}>{profile.data?.username ?? t('auth.signedIn')}</Text>
            <Text size="xs" c="dimmed">
              {t('settings.accountConsole', 'Account console')}
            </Text>
          </div>
        </div>
        <Stack gap={8}>
          {SETTINGS_SECTIONS.map((section) => {
            const Icon = section.icon
            return (
              <button
                key={section.key}
                className={`${classes.navButton} ${
                  activeSection === section.key ? classes.navButtonActive : ''
                }`}
                type="button"
                onClick={() => setActiveSection(section.key)}
              >
                <Icon size={17} />
                <span>{t(section.labelKey)}</span>
              </button>
            )
          })}
        </Stack>
      </aside>

      <main className={classes.content}>
        {activeSection === 'profile' ? <ProfilePanel /> : null}
        {activeSection === 'models' ? <ModelProvidersPanel /> : null}
        {activeSection === 'configuration' ? <ConfigurationPanel /> : null}
      </main>
    </div>
  )
}

function ProfilePanel() {
  const { t } = useTranslation()
  const profile = useUserSettingsProfile()

  if (profile.isLoading) {
    return <Loader size="sm" />
  }

  if (profile.isError) {
    return <Alert color="red">{formatApiError(profile.error)}</Alert>
  }

  const user = profile.data
  const userInitial = user?.username.slice(0, 1).toUpperCase() ?? 'U'

  return (
    <Paper withBorder radius="lg" className={classes.panel}>
      <PanelHeader
        title={t('settings.profile.title')}
        subtitle={t('settings.profile.subtitle')}
      />
      <Divider />
      <Stack gap="xl" className={classes.formBody}>
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="xl">
          <ProfileRow label={t('settings.profile.name')} value={user?.username ?? '-'} />
          <ProfileRow label="User ID" value={user?.user_id ?? '-'} mono />
        </SimpleGrid>
        <div className={classes.avatarRow}>
          <Text fw={750}>{t('settings.profile.avatar')}</Text>
          <Avatar radius="md" size={70} className={classes.largeAvatar}>
            {userInitial}
          </Avatar>
          <Text size="sm" c="dimmed">
            {t('settings.profile.avatarHint')}
          </Text>
        </div>
        <div>
          <Text fw={750} mb="xs">
            {t('settings.profile.routePermissions')}
          </Text>
          <Group gap={8}>
            {(user?.route_permissions ?? []).map((permission) => (
              <Badge key={permission} variant="light" color="teal">
                {permission}
              </Badge>
            ))}
          </Group>
        </div>
      </Stack>
    </Paper>
  )
}

function ModelProvidersPanel() {
  const { t } = useTranslation()
  const settings = useModelProviderSettings()
  const createProvider = useCreateModelProvider()
  const deleteProvider = useDeleteModelProvider()
  const createModel = useCreateProviderModel()
  const deleteModel = useDeleteProviderModel()
  const updateDefaults = useUpdateModelDefaults()
  const [providerName, setProviderName] = useState('')
  const [providerType, setProviderType] = useState<ProviderType>('openai_compatible')
  const [providerBaseUrl, setProviderBaseUrl] = useState('')
  const [providerApiKey, setProviderApiKey] = useState('')
  const [selectedProviderId, setSelectedProviderId] = useState<string | null>(null)
  const [modelName, setModelName] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [aiType, setAiType] = useState<ModelAiType>('llm')
  const [dimension, setDimension] = useState<string | number>('')
  const [contextWindow, setContextWindow] = useState<string | number>('')
  const [maxTokens, setMaxTokens] = useState<string | number>('')
  const [defaultOverrides, setDefaultOverrides] = useState<Record<string, string | null>>({})

  if (settings.isLoading) {
    return <Loader size="sm" />
  }

  if (settings.isError) {
    return <Alert color="red">{formatApiError(settings.error)}</Alert>
  }

  const data = settings.data
  if (!data) {
    return null
  }

  const providerOptions = data.providers.map((provider) => ({
    value: provider.provider_id,
    label: provider.name,
  }))
  const effectiveSelectedProviderId =
    selectedProviderId ?? data.providers[0]?.provider_id ?? null
  const bindingKeys = data.binding_keys
  const defaultBindings = data.defaults

  async function handleCreateProvider() {
    if (!providerName.trim()) {
      return
    }
    try {
      await createProvider.mutateAsync({
        name: providerName.trim(),
        provider_type: providerType,
        base_url: providerBaseUrl.trim() || null,
        api_key: providerApiKey.trim() || null,
      })
      setProviderName('')
      setProviderBaseUrl('')
      setProviderApiKey('')
      notifications.show({
        color: 'green',
        title: t('settings.saved'),
        message: t('settings.modelProviders.providerSaved'),
      })
    } catch (error) {
      notifications.show({ color: 'red', title: t('settings.failed'), message: formatApiError(error) })
    }
  }

  async function handleCreateModel() {
    if (!effectiveSelectedProviderId || !modelName.trim()) {
      return
    }
    try {
      await createModel.mutateAsync({
        providerId: effectiveSelectedProviderId,
        model: {
          model_name: modelName.trim(),
          display_name: displayName.trim() || null,
          ai_type: aiType,
          dimension: optionalNumber(dimension),
          context_window: optionalNumber(contextWindow),
          max_tokens: optionalNumber(maxTokens),
        },
      })
      setModelName('')
      setDisplayName('')
      setDimension('')
      setContextWindow('')
      setMaxTokens('')
      notifications.show({
        color: 'green',
        title: t('settings.saved'),
        message: t('settings.modelProviders.modelSaved'),
      })
    } catch (error) {
      notifications.show({ color: 'red', title: t('settings.failed'), message: formatApiError(error) })
    }
  }

  async function handleSaveDefaults() {
    const bindings: Record<string, string | null> = {}
    for (const key of bindingKeys) {
      bindings[key] = defaultValueForBinding(defaultBindings, defaultOverrides, key)
    }
    try {
      await updateDefaults.mutateAsync(bindings)
      setDefaultOverrides({})
      notifications.show({
        color: 'green',
        title: t('settings.saved'),
        message: t('settings.modelProviders.defaultsSaved'),
      })
    } catch (error) {
      notifications.show({ color: 'red', title: t('settings.failed'), message: formatApiError(error) })
    }
  }

  function applyPreset(preset: ProviderPreset) {
    setProviderName(preset.name)
    setProviderType(preset.provider_type)
    setProviderBaseUrl(preset.base_url ?? '')
  }

  return (
    <div className={classes.modelsGrid}>
      <Stack gap="lg">
        <Paper withBorder radius="lg" className={classes.panel}>
          <PanelHeader
            title={t('settings.modelProviders.defaultTitle')}
            subtitle={t('settings.modelProviders.defaultSubtitle')}
          />
          <Divider />
          <Stack gap="md" className={classes.formBody}>
            {data.binding_keys.map((bindingKey) => (
              <Select
                key={bindingKey}
                clearable
                label={BINDING_LABELS[bindingKey]}
                placeholder={t('settings.modelProviders.selectModel')}
                data={modelOptionsForBinding(data.providers, bindingKey)}
                value={defaultValueForBinding(data.defaults, defaultOverrides, bindingKey)}
                onChange={(value) =>
                  setDefaultOverrides((current) => ({ ...current, [bindingKey]: value }))
                }
              />
            ))}
            <Group justify="flex-end">
              <Button
                leftSection={<Save size={15} />}
                loading={updateDefaults.isPending}
                onClick={handleSaveDefaults}
              >
                {t('settings.saveDefaults')}
              </Button>
            </Group>
          </Stack>
        </Paper>

        <Paper withBorder radius="lg" className={classes.panel}>
          <PanelHeader
            title={t('settings.modelProviders.addProvider')}
            subtitle={t('settings.modelProviders.addProviderSubtitle')}
          />
          <Divider />
          <Stack gap="md" className={classes.formBody}>
            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
              <TextInput
                label={t('settings.modelProviders.providerName')}
                value={providerName}
                onChange={(event) => setProviderName(event.currentTarget.value)}
              />
              <Select
                label={t('settings.modelProviders.providerType')}
                data={data.provider_types}
                value={providerType}
                onChange={(value) => setProviderType((value as ProviderType) ?? 'openai_compatible')}
              />
              <TextInput
                label="Base URL"
                value={providerBaseUrl}
                onChange={(event) => setProviderBaseUrl(event.currentTarget.value)}
              />
              <PasswordInput
                label="API Key"
                value={providerApiKey}
                onChange={(event) => setProviderApiKey(event.currentTarget.value)}
              />
            </SimpleGrid>
            <Group justify="flex-end">
              <Button
                leftSection={<Plus size={15} />}
                loading={createProvider.isPending}
                onClick={handleCreateProvider}
              >
                {t('settings.modelProviders.addProvider')}
              </Button>
            </Group>
          </Stack>
        </Paper>

        <Paper withBorder radius="lg" className={classes.panel}>
          <PanelHeader
            title={t('settings.modelProviders.addModel')}
            subtitle={t('settings.modelProviders.addModelSubtitle')}
          />
          <Divider />
          <Stack gap="md" className={classes.formBody}>
            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
              <Select
                label={t('settings.modelProviders.provider')}
                data={providerOptions}
                value={effectiveSelectedProviderId}
                onChange={setSelectedProviderId}
              />
              <Select
                label="AI type"
                data={data.ai_types}
                value={aiType}
                onChange={(value) => setAiType((value as ModelAiType) ?? 'llm')}
              />
              <TextInput
                label={t('settings.modelProviders.modelName')}
                value={modelName}
                onChange={(event) => setModelName(event.currentTarget.value)}
              />
              <TextInput
                label={t('settings.modelProviders.displayName')}
                value={displayName}
                onChange={(event) => setDisplayName(event.currentTarget.value)}
              />
              <NumberInput label="Dimension" value={dimension} onChange={setDimension} />
              <NumberInput
                label="Context window"
                value={contextWindow}
                onChange={setContextWindow}
              />
              <NumberInput label="Max tokens" value={maxTokens} onChange={setMaxTokens} />
            </SimpleGrid>
            <Group justify="flex-end">
              <Button
                leftSection={<Plus size={15} />}
                loading={createModel.isPending}
                onClick={handleCreateModel}
              >
                {t('settings.modelProviders.addModel')}
              </Button>
            </Group>
          </Stack>
        </Paper>
      </Stack>

      <Stack gap="lg">
        <Paper withBorder radius="lg" className={classes.panel}>
          <PanelHeader
            title={t('settings.modelProviders.available')}
            subtitle={t('settings.modelProviders.availableSubtitle')}
          />
          <Divider />
          <ScrollArea h={310} className={classes.presets}>
            <Stack gap="sm">
              {data.presets.map((preset) => (
                <button
                  key={preset.name}
                  className={classes.presetButton}
                  type="button"
                  onClick={() => applyPreset(preset)}
                >
                  <Group justify="space-between">
                    <Group gap="sm">
                      <div className={classes.presetMark}>
                        <Sparkles size={18} />
                      </div>
                      <div>
                        <Text fw={800}>{preset.name}</Text>
                        <Text size="xs" c="dimmed">
                          {preset.provider_type}
                        </Text>
                      </div>
                    </Group>
                    <Plus size={15} />
                  </Group>
                  <Group gap={5} mt="sm">
                    {preset.capabilities.map((capability) => (
                      <Badge key={capability} size="xs" variant="light">
                        {capability}
                      </Badge>
                    ))}
                  </Group>
                </button>
              ))}
            </Stack>
          </ScrollArea>
        </Paper>

        <Paper withBorder radius="lg" className={classes.panel}>
          <PanelHeader
            title={t('settings.modelProviders.added')}
            subtitle={`${data.providers.length} providers`}
          />
          <Divider />
          <Stack gap="sm" className={classes.formBody}>
            {data.providers.length === 0 ? (
              <Text c="dimmed" size="sm">
                {t('settings.modelProviders.noProviders')}
              </Text>
            ) : (
              data.providers.map((provider) => (
                <div key={provider.provider_id} className={classes.providerCard}>
                  <Group justify="space-between" align="flex-start">
                    <div>
                      <Group gap={8}>
                        <Text fw={850}>{provider.name}</Text>
                        <Badge color={provider.is_enabled ? 'teal' : 'gray'} size="xs">
                          {provider.provider_type}
                        </Badge>
                      </Group>
                      <Text size="xs" c="dimmed">
                        {provider.base_url ?? 'local'}
                      </Text>
                      {provider.api_key_configured ? (
                        <Text size="xs" c="dimmed">
                          <KeyRound size={12} /> {provider.api_key_masked}
                        </Text>
                      ) : null}
                    </div>
                    <Tooltip label={t('common.delete')}>
                      <Button
                        color="red"
                        size="compact-xs"
                        variant="light"
                        leftSection={<Trash2 size={13} />}
                        loading={
                          deleteProvider.isPending &&
                          deleteProvider.variables === provider.provider_id
                        }
                        onClick={() => deleteProvider.mutate(provider.provider_id)}
                      >
                        {t('common.delete')}
                      </Button>
                    </Tooltip>
                  </Group>
                  <Group gap={6} mt="sm">
                    {provider.models.map((model) => (
                      <Badge
                        key={model.model_id}
                        rightSection={
                          <button
                            className={classes.badgeDelete}
                            type="button"
                            onClick={() =>
                              deleteModel.mutate({
                                providerId: provider.provider_id,
                                modelId: model.model_id,
                              })
                            }
                          >
                            x
                          </button>
                        }
                        variant="light"
                      >
                        {model.display_name ?? model.model_name} / {model.ai_type}
                      </Badge>
                    ))}
                  </Group>
                </div>
              ))
            )}
          </Stack>
        </Paper>
      </Stack>
    </div>
  )
}

function ConfigurationPanel() {
  const { t } = useTranslation()
  const configuration = useRuntimeConfiguration()
  const updateConfiguration = useUpdateRuntimeConfiguration()
  const [overrides, setOverrides] = useState<Record<string, string | number | boolean | null>>({})

  if (configuration.isLoading) {
    return <Loader size="sm" />
  }

  if (configuration.isError) {
    return <Alert color="red">{formatApiError(configuration.error)}</Alert>
  }

  const fields = configuration.data?.fields ?? []
  const sectionNames = Array.from(new Set(fields.map((field) => field.section)))

  function updateField(key: string, value: string | number | boolean | null) {
    setOverrides((current) => ({ ...current, [key]: value }))
  }

  async function handleSave() {
    if (Object.keys(overrides).length === 0) {
      notifications.show({
        color: 'gray',
        title: t('settings.noChanges'),
        message: t('settings.noChangesMessage'),
      })
      return
    }

    try {
      await updateConfiguration.mutateAsync(overrides)
      setOverrides({})
      notifications.show({
        color: 'green',
        title: t('settings.saved'),
        message: t('settings.configuration.saved'),
      })
    } catch (error) {
      notifications.show({ color: 'red', title: t('settings.failed'), message: formatApiError(error) })
    }
  }

  return (
    <Paper withBorder radius="lg" className={classes.panel}>
      <Group justify="space-between" align="flex-start">
        <PanelHeader
          title={t('settings.configuration.title')}
          subtitle={t('settings.configuration.subtitle')}
        />
        <Button
          leftSection={<Save size={15} />}
          loading={updateConfiguration.isPending}
          onClick={handleSave}
        >
          {t('common.save', 'Save')}
        </Button>
      </Group>
      <Divider />
      <Stack gap="xl" className={classes.formBody}>
        {sectionNames.map((section) => (
          <div key={section}>
            <Group gap={8} mb="md">
              <Database size={17} />
              <Title order={3} className={classes.sectionTitle}>
                {CONFIG_SECTION_LABELS[section] ?? section}
              </Title>
            </Group>
            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
              {fields
                .filter((field) => field.section === section)
                .map((field) => (
                  <ConfigurationFieldControl
                    key={field.key}
                    field={field}
                    value={configurationFieldValue(field, overrides)}
                    onChange={(value) => updateField(field.key, value)}
                    onReset={() => updateField(field.key, null)}
                  />
                ))}
            </SimpleGrid>
          </div>
        ))}
      </Stack>
    </Paper>
  )
}

function ConfigurationFieldControl({
  field,
  value,
  onChange,
  onReset,
}: {
  field: RuntimeConfigurationField
  value: string | number | boolean | null | undefined
  onChange: (value: string | number | boolean | null) => void
  onReset: () => void
}) {
  const sourceBadge = (
    <Badge size="xs" color={field.source === 'db' ? 'teal' : 'gray'} variant="light">
      {field.source}
    </Badge>
  )

  const resetButton = (
    <Tooltip label="Reset to .env">
      <Button size="compact-xs" variant="subtle" onClick={onReset}>
        <RotateCcw size={13} />
      </Button>
    </Tooltip>
  )

  if (field.value_type === 'boolean') {
    return (
      <Paper withBorder radius="md" p="sm" className={classes.configBoolean}>
        <Group justify="space-between">
          <div>
            <Group gap={6}>
              <Text fw={750}>{field.label}</Text>
              {sourceBadge}
            </Group>
            <Text size="xs" c="dimmed">
              {field.key}
            </Text>
          </div>
          <Group gap={4}>
            <Switch checked={Boolean(value)} onChange={(event) => onChange(event.currentTarget.checked)} />
            {resetButton}
          </Group>
        </Group>
      </Paper>
    )
  }

  const commonProps = {
    label: (
      <Group gap={6}>
        <span>{field.label}</span>
        {sourceBadge}
      </Group>
    ),
    description: field.key,
    rightSection: resetButton,
  }

  if (field.secret) {
    return (
      <PasswordInput
        {...commonProps}
        placeholder={field.masked_value ?? 'Not configured'}
        value={typeof value === 'string' ? value : ''}
        onChange={(event) => onChange(event.currentTarget.value)}
      />
    )
  }

  if (field.value_type === 'integer' || field.value_type === 'float') {
    return (
      <NumberInput
        {...commonProps}
        value={typeof value === 'number' || typeof value === 'string' ? value : ''}
        onChange={(nextValue) => onChange(nextValue === '' ? null : nextValue)}
      />
    )
  }

  if (field.value_type === 'select') {
    return (
      <Select
        {...commonProps}
        clearable
        data={field.options}
        value={typeof value === 'string' ? value : null}
        onChange={(nextValue) => onChange(nextValue)}
      />
    )
  }

  return (
    <TextInput
      {...commonProps}
      value={typeof value === 'string' || typeof value === 'number' ? String(value) : ''}
      onChange={(event) => onChange(event.currentTarget.value)}
    />
  )
}

function configurationFieldValue(
  field: RuntimeConfigurationField,
  overrides: Record<string, string | number | boolean | null>,
): string | number | boolean | null {
  if (Object.hasOwn(overrides, field.key)) {
    return overrides[field.key] ?? null
  }
  return field.secret ? '' : field.value
}

function PanelHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className={classes.panelHeader}>
      <Title order={2}>{title}</Title>
      <Text c="dimmed">{subtitle}</Text>
    </div>
  )
}

function ProfileRow({
  label,
  value,
  mono = false,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className={classes.profileRow}>
      <Text fw={750}>{label}</Text>
      <Text className={mono ? classes.monoValue : ''}>{value}</Text>
      <Badge color="gray" variant="light">
        <Check size={12} /> read only
      </Badge>
    </div>
  )
}

function modelOptionsForBinding(providers: Array<{ name: string; models: Array<{
  ai_type: ModelAiType
  display_name: string | null
  is_enabled: boolean
  model_id: string
  model_name: string
}> }>, bindingKey: ModelBindingKey) {
  const expectedType = BINDING_TYPES[bindingKey]
  return providers.flatMap((provider) =>
    provider.models
      .filter((model) => model.ai_type === expectedType && model.is_enabled)
      .map((model) => ({
        value: model.model_id,
        label: `${model.display_name ?? model.model_name} · ${provider.name}`,
      })),
  )
}

function optionalNumber(value: string | number): number | null {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null
  }
  const trimmed = value.trim()
  return trimmed ? Number(trimmed) : null
}

function defaultValueForBinding(
  defaults: Array<{ binding_key: ModelBindingKey; model_id: string }>,
  overrides: Record<string, string | null>,
  bindingKey: ModelBindingKey,
): string | null {
  if (Object.hasOwn(overrides, bindingKey)) {
    return overrides[bindingKey] ?? null
  }
  return defaults.find((binding) => binding.binding_key === bindingKey)?.model_id ?? null
}
