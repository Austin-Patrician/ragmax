import {
  Alert,
  Avatar,
  Badge,
  Button,
  Divider,
  Group,
  Loader,
  Modal,
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
  AlertCircle,
  Box,
  Brain,
  Check,
  ChevronDown,
  Clock,
  Compass,
  Copy,
  Cpu,
  Database,
  FileText,
  Flame,
  Globe,
  HardDrive,
  HelpCircle,
  KeyRound,
  Laptop,
  Layers,
  Lock,
  Mail,
  MessageSquare,
  Network,
  Pencil,
  Plus,
  RotateCcw,
  Save,
  Search,
  Settings,
  Shield,
  ShieldCheck,
  Sliders,
  Smile,
  Sparkles,
  Terminal,
  Trash2,
  User,
  X,
  LogOut,
} from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import { useAuth } from '@/auth/useAuth'
import { ROUTES } from '@/constants/routes'
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
  asideHeader: styles.asideHeader ?? '',
  asideTitle: styles.asideTitle ?? '',
  avatarRow: styles.avatarRow ?? '',
  badgeDelete: styles.badgeDelete ?? '',
  configBoolean: styles.configBoolean ?? '',
  content: styles.content ?? '',
  editButton: styles.editButton ?? '',
  filterTab: styles.filterTab ?? '',
  filterTabActive: styles.filterTabActive ?? '',
  filterTabs: styles.filterTabs ?? '',
  formBody: styles.formBody ?? '',
  identity: styles.identity ?? '',
  identityAvatar: styles.identityAvatar ?? '',
  largeAvatar: styles.largeAvatar ?? '',
  modelSection: styles.modelSection ?? '',
  modelSectionHeader: styles.modelSectionHeader ?? '',
  modelSectionSubtitle: styles.modelSectionSubtitle ?? '',
  modelSectionTitle: styles.modelSectionTitle ?? '',
  modelsAside: styles.modelsAside ?? '',
  modelsLayout: styles.modelsLayout ?? '',
  modelsMain: styles.modelsMain ?? '',
  monoValue: styles.monoValue ?? '',
  navButton: styles.navButton ?? '',
  navButtonActive: styles.navButtonActive ?? '',
  page: styles.page ?? '',
  panel: styles.panel ?? '',
  panelHeader: styles.panelHeader ?? '',
  profileHint: styles.profileHint ?? '',
  profileLabel: styles.profileLabel ?? '',
  profileRow: styles.profileRow ?? '',
  profileValue: styles.profileValue ?? '',
  profileValueText: styles.profileValueText ?? '',
  // Simple Profile UI elements
  simpleProfileContainer: styles.simpleProfileContainer ?? '',
  simpleProfileHeader: styles.simpleProfileHeader ?? '',
  simpleProfileTitle: styles.simpleProfileTitle ?? '',
  simpleProfileSubtitle: styles.simpleProfileSubtitle ?? '',
  simpleProfileRows: styles.simpleProfileRows ?? '',
  simpleProfileRow: styles.simpleProfileRow ?? '',
  simpleProfileLabel: styles.simpleProfileLabel ?? '',
  simpleProfileContent: styles.simpleProfileContent ?? '',
  simpleProfileControl: styles.simpleProfileControl ?? '',
  simpleProfileInput: styles.simpleProfileInput ?? '',
  simpleProfileInputDisabled: styles.simpleProfileInputDisabled ?? '',
  simpleProfileEditBtn: styles.simpleProfileEditBtn ?? '',
  simpleProfileAvatarWrapper: styles.simpleProfileAvatarWrapper ?? '',
  simpleProfileAvatarBlock: styles.simpleProfileAvatarBlock ?? '',
  simpleProfileAvatarDelete: styles.simpleProfileAvatarDelete ?? '',
  simpleProfileAvatarHint: styles.simpleProfileAvatarHint ?? '',
  simpleProfileEmailWrapper: styles.simpleProfileEmailWrapper ?? '',
  simpleProfileEmailText: styles.simpleProfileEmailText ?? '',
  simpleProfileEmailHint: styles.simpleProfileEmailHint ?? '',
  
  providerCard: styles.providerCard ?? '',
  providerIcon: styles.providerIcon ?? '',
  providerInfo: styles.providerInfo ?? '',
  providerName: styles.providerName ?? '',
  providerTag: styles.providerTag ?? '',
  providerTags: styles.providerTags ?? '',
  providersList: styles.providersList ?? '',
  searchBox: styles.searchBox ?? '',
  searchInput: styles.searchInput ?? '',
  sectionSubtitle: styles.sectionSubtitle ?? '',
  sectionTitle: styles.sectionTitle ?? '',
  sidebar: styles.sidebar ?? '',
  
  // Configuration UI elements
  configContainer: styles.configContainer ?? '',
  configPanelHeader: styles.configPanelHeader ?? '',
  configPanelLayout: styles.configPanelLayout ?? '',
  configSubSidebar: styles.configSubSidebar ?? '',
  configSearchWrapper: styles.configSearchWrapper ?? '',
  searchIcon: styles.searchIcon ?? '',
  configSearchInput: styles.configSearchInput ?? '',
  clearSearchButton: styles.clearSearchButton ?? '',
  configSubMenuList: styles.configSubMenuList ?? '',
  configSubNavButton: styles.configSubNavButton ?? '',
  configSubNavButtonActive: styles.configSubNavButtonActive ?? '',
  configSubNavText: styles.configSubNavText ?? '',
  configFormArea: styles.configFormArea ?? '',
  configSectionHeader: styles.configSectionHeader ?? '',
  configHeaderTitleGroup: styles.configHeaderTitleGroup ?? '',
  configHeaderIcon: styles.configHeaderIcon ?? '',
  configHeaderTitle: styles.configHeaderTitle ?? '',
  configHeaderSubtitle: styles.configHeaderSubtitle ?? '',
  noResults: styles.noResults ?? '',
  configRowsList: styles.configRowsList ?? '',
  configRow: styles.configRow ?? '',
  configRowModified: styles.configRowModified ?? '',
  configMeta: styles.configMeta ?? '',
  configLabelGroup: styles.configLabelGroup ?? '',
  configLabelText: styles.configLabelText ?? '',
  configKeyText: styles.configKeyText ?? '',
  configInputWrapper: styles.configInputWrapper ?? '',
  configInputControl: styles.configInputControl ?? '',
  resetButton: styles.resetButton ?? '',
  configStickyFooter: styles.configStickyFooter ?? '',
  configStickyFooterContent: styles.configStickyFooterContent ?? '',
  configStickyFooterTextGroup: styles.configStickyFooterTextGroup ?? '',
  configStickyFooterIcon: styles.configStickyFooterIcon ?? '',
  configStickyFooterText: styles.configStickyFooterText ?? '',

  // Model Providers UI elements
  modelSubTabsContainer: styles.modelSubTabsContainer ?? '',
  modelSubTab: styles.modelSubTab ?? '',
  modelSubTabActive: styles.modelSubTabActive ?? '',
  providerGrid: styles.providerGrid ?? '',
  providerMainCard: styles.providerMainCard ?? '',
  providerCardHeader: styles.providerCardHeader ?? '',
  providerLogoWrapper: styles.providerLogoWrapper ?? '',
  providerCardTitleGroup: styles.providerCardTitleGroup ?? '',
  providerTitleRow: styles.providerTitleRow ?? '',
  providerCardName: styles.providerCardName ?? '',
  providerCardUrl: styles.providerCardUrl ?? '',
  providerModelsSection: styles.providerModelsSection ?? '',
  modelsSectionTitle: styles.modelsSectionTitle ?? '',
  providerModelsGrid: styles.providerModelsGrid ?? '',
  modelBadgeItem: styles.modelBadgeItem ?? '',
  modelBadgeDelete: styles.modelBadgeDelete ?? '',
  noModelsHint: styles.noModelsHint ?? '',
  providerCardFooter: styles.providerCardFooter ?? '',
  inlineAddButton: styles.inlineAddButton ?? '',
  inlineAddForm: styles.inlineAddForm ?? '',
  inlineFormHeader: styles.inlineFormHeader ?? '',
  inlineFormTitle: styles.inlineFormTitle ?? '',
  advancedFormToggle: styles.advancedFormToggle ?? '',
  connectLayout: styles.connectLayout ?? '',
  presetsSection: styles.presetsSection ?? '',
  presetGrid: styles.presetGrid ?? '',
  presetCard: styles.presetCard ?? '',
  presetCardActive: styles.presetCardActive ?? '',
  presetCardTitle: styles.presetCardTitle ?? '',
  presetCardTags: styles.presetCardTags ?? '',
  presetCardTag: styles.presetCardTag ?? '',
  
  // Dashboard split layout classes
  providerDashboard: styles.providerDashboard ?? '',
  leftColumn: styles.leftColumn ?? '',
  rightColumn: styles.rightColumn ?? '',
  dashboardSectionTitle: styles.dashboardSectionTitle ?? '',
  dashboardSectionSubtitle: styles.dashboardSectionSubtitle ?? '',
  defaultModelsCard: styles.defaultModelsCard ?? '',
  defaultModelsGrid: styles.defaultModelsGrid ?? '',
  defaultModelRow: styles.defaultModelRow ?? '',
  defaultModelLabelGroup: styles.defaultModelLabelGroup ?? '',
  defaultModelLabel: styles.defaultModelLabel ?? '',
  requiredStar: styles.requiredStar ?? '',
  helpIcon: styles.helpIcon ?? '',
  addedProvidersList: styles.addedProvidersList ?? '',
  addedProviderCard: styles.addedProviderCard ?? '',
  addedProviderInfo: styles.addedProviderInfo ?? '',
  addedProviderName: styles.addedProviderName ?? '',
  addedProviderActions: styles.addedProviderActions ?? '',
  keyIconActive: styles.keyIconActive ?? '',
  keyIconInactive: styles.keyIconInactive ?? '',
  availablePresetsList: styles.availablePresetsList ?? '',
  presetCardSimple: styles.presetCardSimple ?? '',
  presetCardSimpleHeader: styles.presetCardSimpleHeader ?? '',
  presetCardSimpleTitleGroup: styles.presetCardSimpleTitleGroup ?? '',
  presetCardSimpleTitle: styles.presetCardSimpleTitle ?? '',
  presetCardSimpleArrow: styles.presetCardSimpleArrow ?? '',
  presetCardSimpleTags: styles.presetCardSimpleTags ?? '',
  presetCardSimpleTag: styles.presetCardSimpleTag ?? '',
  modelsExpanderPanel: styles.modelsExpanderPanel ?? '',
  filterScrollArea: styles.filterScrollArea ?? '',
  filterChip: styles.filterChip ?? '',
  filterChipActive: styles.filterChipActive ?? '',
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
  const navigate = useNavigate()
  const { logout } = useAuth()

  async function handleLogout() {
    await logout()
    navigate(ROUTES.login, { replace: true })
  }

  return (
    <div className={classes.page}>
      <aside className={classes.sidebar}>
        <div className={classes.identity}>
          <Avatar radius="md" size={40} className={classes.identityAvatar}>
            {profile.data?.username.slice(0, 1).toUpperCase() ?? 'U'}
          </Avatar>
          <Text size="sm" className={classes.identityText}>
            {profile.data?.username ?? t('auth.signedIn')}
          </Text>
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

        <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', paddingBottom: '24px' }}>
          <Divider my="sm" />
          <button
            className={`${classes.navButton} ${classes.logoutButton}`}
            type="button"
            onClick={handleLogout}
          >
            <LogOut size={17} />
            <span>{t('auth.logout', 'Logout')}</span>
          </button>
        </div>
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
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone

  const handleEditClick = () => {
    notifications.show({
      color: 'blue',
      title: 'Info',
      message: 'Profile editing is managed by your system administrator.',
    })
  }

  return (
    <div className={classes.simpleProfileContainer}>
      <div className={classes.simpleProfileHeader}>
        <h2 className={classes.simpleProfileTitle}>Profile</h2>
        <p className={classes.simpleProfileSubtitle}>
          Update your photo and personal details here.
        </p>
      </div>

      <div className={classes.simpleProfileRows}>
        {/* Name Row */}
        <div className={classes.simpleProfileRow}>
          <div className={classes.simpleProfileLabel}>Name</div>
          <div className={classes.simpleProfileContent}>
            <div className={classes.simpleProfileControl}>
              <input
                type="text"
                className={classes.simpleProfileInput}
                value={user?.username ?? ''}
                readOnly
              />
            </div>
            <button
              className={classes.simpleProfileEditBtn}
              type="button"
              onClick={handleEditClick}
            >
              <Pencil size={13} />
              <span>Edit</span>
            </button>
          </div>
        </div>

        {/* Avatar Row */}
        <div className={classes.simpleProfileRow}>
          <div className={classes.simpleProfileLabel}>Avatar</div>
          <div className={classes.simpleProfileContent}>
            <div className={classes.simpleProfileAvatarWrapper}>
              <div className={classes.simpleProfileAvatarBlock}>
                {userInitial}
                <button
                  className={classes.simpleProfileAvatarDelete}
                  title="Remove avatar"
                  type="button"
                  onClick={handleEditClick}
                >
                  ×
                </button>
              </div>
              <span className={classes.simpleProfileAvatarHint}>
                This will be displayed on your profile.
              </span>
            </div>
          </div>
        </div>

        {/* Time zone Row */}
        <div className={classes.simpleProfileRow}>
          <div className={classes.simpleProfileLabel}>Time zone</div>
          <div className={classes.simpleProfileContent}>
            <div className={classes.simpleProfileControl}>
              <input
                type="text"
                className={classes.simpleProfileInput}
                value={timezone}
                readOnly
              />
            </div>
            <button
              className={classes.simpleProfileEditBtn}
              type="button"
              onClick={handleEditClick}
            >
              <Pencil size={13} />
              <span>Edit</span>
            </button>
          </div>
        </div>

        {/* Email Row */}
        <div className={classes.simpleProfileRow}>
          <div className={classes.simpleProfileLabel}>Email</div>
          <div className={classes.simpleProfileContent}>
            <div className={classes.simpleProfileEmailWrapper}>
              <span className={classes.simpleProfileEmailText}>{user?.username ?? ''}</span>
              <span className={classes.simpleProfileEmailHint}>
                Once registered, E-mail cannot be changed.
              </span>
            </div>
          </div>
        </div>

        {/* Password Row */}
        <div className={classes.simpleProfileRow}>
          <div className={classes.simpleProfileLabel}>Password</div>
          <div className={classes.simpleProfileContent}>
            <div className={classes.simpleProfileControl}>
              <input
                type="password"
                className={`${classes.simpleProfileInput} ${classes.simpleProfileInputDisabled}`}
                value="••••••••••••"
                readOnly
              />
            </div>
            <button
              className={classes.simpleProfileEditBtn}
              type="button"
              onClick={handleEditClick}
            >
              <Pencil size={13} />
              <span>Edit</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function ProviderLogo({ name, size = 24 }: { name: string; size?: number }) {
  const normalized = name.toLowerCase()

  if (normalized.includes('openai')) {
    return <img src="/openai.svg" alt={name} style={{ width: size, height: size, objectFit: 'contain', borderRadius: 6 }} />
  }

  if (normalized.includes('anthropic') || normalized.includes('claude')) {
    return <img src="/anthropic.svg" alt={name} style={{ width: size, height: size, objectFit: 'contain', borderRadius: 6 }} />
  }

  if (normalized.includes('gemini') || normalized.includes('google')) {
    return <img src="/gemini-color.svg" alt={name} style={{ width: size, height: size, objectFit: 'contain', borderRadius: 6 }} />
  }

  if (normalized.includes('grok') || normalized.includes('xai')) {
    return <img src="/grok.svg" alt={name} style={{ width: size, height: size, objectFit: 'contain', borderRadius: 6 }} />
  }

  if (normalized.includes('minimax')) {
    return <img src="/minimax-color.svg" alt={name} style={{ width: size, height: size, objectFit: 'contain', borderRadius: 6 }} />
  }

  if (normalized.includes('moonshot') || normalized.includes('kimi')) {
    return <img src="/moonshot.svg" alt={name} style={{ width: size, height: size, objectFit: 'contain', borderRadius: 6 }} />
  }

  if (normalized.includes('qianwen') || normalized.includes('tongyi') || normalized.includes('qwen')) {
    return <img src="/qwen-color.svg" alt={name} style={{ width: size, height: size, objectFit: 'contain', borderRadius: 6 }} />
  }

  if (normalized.includes('zhipu') || normalized.includes('chatglm')) {
    return <img src="/zhipu-color.svg" alt={name} style={{ width: size, height: size, objectFit: 'contain', borderRadius: 6 }} />
  }

  if (normalized.includes('deepseek')) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="24" height="24" rx="6" fill="#0066FE"/>
        <path d="M7 16.5V7.5L12 5L17 7.5V16.5L12 19L7 16.5Z" stroke="white" strokeWidth="1.8" strokeLinejoin="round"/>
        <path d="M12 5V19" stroke="white" strokeWidth="1.2"/>
        <path d="M7 12H17" stroke="white" strokeWidth="1.2"/>
      </svg>
    )
  }

  if (normalized.includes('local hash') || normalized.includes('hash')) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="24" height="24" rx="6" fill="#3B82F6"/>
        <path d="M6 8c0-1.1 2.7-2 6-2s6 .9 6 2-2.7 2-6 2-6-.9-6-2z" stroke="white" strokeWidth="1.5"/>
        <path d="M18 8v4c0 1.1-2.7 2-6 2s-6-.9-6-2V8" stroke="white" strokeWidth="1.5"/>
        <path d="M18 12v4c0 1.1-2.7 2-6 2s-6-.9-6-2v-4" stroke="white" strokeWidth="1.5"/>
      </svg>
    )
  }

  if (normalized.includes('local bge') || normalized.includes('bge')) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="24" height="24" rx="6" fill="#14B8A6"/>
        <path d="M9 7v10M9 7l-3 3M9 17l3-3M15 7v10M15 7l3 3M15 17l-3-3" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    )
  }

  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="24" height="24" rx="6" fill="#8B5CF6"/>
      <path d="M12 6v12M6 12h12" stroke="white" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  )
}

function getProviderHelperText(name: string): string {
  const normalized = name.toLowerCase()
  if (normalized.includes('openai')) {
    return 'Enter your OpenAI API key to access models like GPT-4o and Text-Embedding-3. Standard base URL is https://api.openai.com/v1.'
  }
  if (normalized.includes('deepseek')) {
    return 'Enter your DeepSeek API key to access models like DeepSeek-V3 and DeepSeek-R1. Base URL is https://api.deepseek.com/v1.'
  }
  if (normalized.includes('moonshot')) {
    return 'Enter your Moonshot/Kimi API key to access Moonshot models. Base URL is https://api.moonshot.cn/v1.'
  }
  if (normalized.includes('qianwen') || normalized.includes('tongyi') || normalized.includes('qwen')) {
    return 'Enter your DashScope API key to access Alibaba Tongyi Qianwen models. Base URL is https://dashscope.aliyuncs.com/compatible-mode/v1.'
  }
  if (normalized.includes('zhipu')) {
    return 'Enter your Zhipu BigModel API key to access GLM models. Base URL is https://open.bigmodel.cn/api/paas/v4.'
  }
  if (normalized.includes('local') || normalized.includes('bge') || normalized.includes('hash')) {
    return 'This provider runs locally on your system. It does not require any external network connection or API keys.'
  }
  return 'Configure custom base URL and API credentials for this OpenAI-compatible service.'
}

function ModelProvidersPanel() {
  const { t } = useTranslation()
  const settings = useModelProviderSettings()
  const createProvider = useCreateModelProvider()
  const deleteProvider = useDeleteModelProvider()
  const createModel = useCreateProviderModel()
  const deleteModel = useDeleteProviderModel()
  const updateDefaults = useUpdateModelDefaults()

  // State
  const [searchQuery, setSearchQuery] = useState('')
  const [filterChip, setFilterChip] = useState<'ALL' | ModelAiType>('ALL')
  const [connectingPreset, setConnectingPreset] = useState<ProviderPreset | null>(null)
  const [presetBaseUrl, setPresetBaseUrl] = useState('')
  const [presetApiKey, setPresetApiKey] = useState('')

  const [editingProvider, setEditingProvider] = useState<ModelProvider | null>(null)
  const [editingBaseUrl, setEditingBaseUrl] = useState('')
  const [editingApiKey, setEditingApiKey] = useState('')

  const [expandedProviderId, setExpandedProviderId] = useState<string | null>(null)
  const [addingModelProviderId, setAddingModelProviderId] = useState<string | null>(null)

  // Model creation form state
  const [modelName, setModelName] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [aiType, setAiType] = useState<ModelAiType>('llm')
  const [dimension, setDimension] = useState<string | number>('')
  const [contextWindow, setContextWindow] = useState<string | number>('')
  const [maxTokens, setMaxTokens] = useState<string | number>('')
  const [showAdvanced, setShowAdvanced] = useState(false)

  // Default bindings override state
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

  const bindingKeys = data.binding_keys
  const defaultBindings = data.defaults

  const getModelProviderName = (modelId: string | null): string | null => {
    if (!modelId) return null
    for (const provider of data.providers) {
      if (provider.models.some((m) => m.model_id === modelId)) {
        return provider.name
      }
    }
    return null
  }

  async function handleBindingChange(key: ModelBindingKey, value: string | null) {
    const nextOverrides = { ...defaultOverrides, [key]: value }
    setDefaultOverrides(nextOverrides)

    const bindings: Record<string, string | null> = {}
    for (const k of bindingKeys) {
      bindings[k] = defaultValueForBinding(defaultBindings, nextOverrides, k)
    }

    try {
      await updateDefaults.mutateAsync(bindings)
      notifications.show({
        color: 'green',
        title: t('settings.saved'),
        message: 'Default model routing updated.',
      })
    } catch (error) {
      notifications.show({ color: 'red', title: t('settings.failed'), message: formatApiError(error) })
    }
  }

  const handlePresetClick = (preset: ProviderPreset) => {
    setConnectingPreset(preset)
    setPresetBaseUrl(preset.base_url ?? '')
    setPresetApiKey('')
  }

  const handleConnectPreset = async () => {
    if (!connectingPreset) return
    try {
      await createProvider.mutateAsync({
        name: connectingPreset.name,
        provider_type: connectingPreset.provider_type,
        base_url: presetBaseUrl.trim() || null,
        api_key: presetApiKey.trim() || null,
      })
      setConnectingPreset(null)
      notifications.show({
        color: 'green',
        title: t('settings.saved'),
        message: t('settings.modelProviders.providerSaved'),
      })
    } catch (error) {
      notifications.show({ color: 'red', title: t('settings.failed'), message: formatApiError(error) })
    }
  }

  const handleEditProvider = (provider: ModelProvider) => {
    setEditingProvider(provider)
    setEditingBaseUrl(provider.base_url ?? '')
    setEditingApiKey('')
  }

  const handleSaveCredentials = async () => {
    if (!editingProvider) return
    try {
      await createProvider.mutateAsync({
        name: editingProvider.name,
        provider_type: editingProvider.provider_type,
        base_url: editingBaseUrl.trim() || null,
        api_key: editingApiKey.trim() || null,
      })
      setEditingProvider(null)
      notifications.show({
        color: 'green',
        title: t('settings.saved'),
        message: 'Credentials updated successfully.',
      })
    } catch (error) {
      notifications.show({ color: 'red', title: t('settings.failed'), message: formatApiError(error) })
    }
  }

  async function handleCreateModel(providerId: string) {
    if (!modelName.trim()) return
    try {
      await createModel.mutateAsync({
        providerId,
        model: {
          model_name: modelName.trim(),
          display_name: displayName.trim() || null,
          ai_type: aiType,
          dimension: optionalNumber(dimension),
          context_window: optionalNumber(contextWindow),
          max_tokens: optionalNumber(maxTokens),
        },
      })
      setAddingModelProviderId(null)
      setModelName('')
      setDisplayName('')
      setDimension('')
      setContextWindow('')
      setMaxTokens('')
      setShowAdvanced(false)
      notifications.show({
        color: 'green',
        title: t('settings.saved'),
        message: t('settings.modelProviders.modelSaved'),
      })
    } catch (error) {
      notifications.show({ color: 'red', title: t('settings.failed'), message: formatApiError(error) })
    }
  }

  const ALL_FILTER_TAGS = ['ALL', 'LLM', 'EMBEDDING', 'RERANK', 'TTS', 'ASR', 'VLM', 'MODERATION', 'OCR'] as const

  const filteredPresets = data.presets.filter((preset) => {
    const matchesSearch = preset.name.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesFilter =
      filterChip === 'ALL' ||
      preset.capabilities.some((cap) => cap.toUpperCase() === filterChip)
    return matchesSearch && matchesFilter
  })

  const getBindingLabel = (key: ModelBindingKey) => {
    if (key === 'answer_llm') return 'LLM'
    return BINDING_LABELS[key] ?? key
  }

  return (
    <div className={classes.providerDashboard}>
      {/* Left Column */}
      <div className={classes.leftColumn}>
        {/* Set Default Models Panel */}
        <div>
          <h3 className={classes.dashboardSectionTitle}>Set default models</h3>
          <p className={classes.dashboardSectionSubtitle}>
            Please complete these settings before beginning
          </p>
          <div className={classes.defaultModelsCard}>
            <div className={classes.defaultModelsGrid}>
              {bindingKeys.map((bindingKey) => (
                <div className={classes.defaultModelRow} key={bindingKey}>
                  <div className={classes.defaultModelLabelGroup}>
                    {bindingKey === 'answer_llm' && <span className={classes.requiredStar}>*</span>}
                    <span className={classes.defaultModelLabel}>{getBindingLabel(bindingKey)}</span>
                    <Tooltip label={`Configure default model for ${getBindingLabel(bindingKey)}`}>
                      <span className={classes.helpIcon}>
                        <HelpCircle size={13} />
                      </span>
                    </Tooltip>
                  </div>
                  <div>
                    <Select
                      leftSection={
                        getModelProviderName(defaultValueForBinding(data.defaults, defaultOverrides, bindingKey)) ? (
                          <ProviderLogo name={getModelProviderName(defaultValueForBinding(data.defaults, defaultOverrides, bindingKey))!} size={18} />
                        ) : null
                      }
                      clearable
                      placeholder={t('settings.modelProviders.selectModel')}
                      data={modelOptionsForBinding(data.providers, bindingKey)}
                      value={defaultValueForBinding(data.defaults, defaultOverrides, bindingKey)}
                      onChange={(value) => handleBindingChange(bindingKey, value)}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Added Models Panel */}
        <div>
          <h3 className={classes.dashboardSectionTitle}>Added models</h3>
          {data.providers.length === 0 ? (
            <div className={classes.noResults} style={{ padding: '24px' }}>
              <AlertCircle size={20} />
              <Text size="sm" c="dimmed">
                No active providers added yet. Use the preset gallery on the right to connect.
              </Text>
            </div>
          ) : (
            <div className={classes.addedProvidersList}>
              {data.providers.map((provider) => {
                const isExpanded = expandedProviderId === provider.provider_id
                const isFormOpen = addingModelProviderId === provider.provider_id

                return (
                  <div key={provider.provider_id} style={{ display: 'flex', flexDirection: 'column' }}>
                    <div className={classes.addedProviderCard}>
                      <div className={classes.addedProviderInfo}>
                        <ProviderLogo name={provider.name} size={32} />
                        <span className={classes.addedProviderName}>{provider.name}</span>
                        <Badge size="xs" color="gray" variant="light">
                          {provider.provider_type}
                        </Badge>
                      </div>

                      <div className={classes.addedProviderActions}>
                        {/* Key status icon */}
                        <KeyRound
                          size={15}
                          className={
                            provider.api_key_configured
                              ? classes.keyIconActive
                              : classes.keyIconInactive
                          }
                          title={
                            provider.api_key_configured
                              ? 'API Key configured'
                              : 'No credentials needed'
                          }
                        />

                        {/* API-Key config button */}
                        <Button
                          variant="light"
                          size="xs"
                          leftSection={<Settings size={13} />}
                          onClick={() => handleEditProvider(provider)}
                        >
                          API-Key
                        </Button>

                        {/* View models button */}
                        <Button
                          variant="subtle"
                          size="xs"
                          rightSection={
                            <ChevronDown
                              size={13}
                              style={{
                                transform: isExpanded ? 'rotate(180deg)' : 'none',
                                transition: 'transform 150ms',
                              }}
                            />
                          }
                          onClick={() =>
                            setExpandedProviderId(isExpanded ? null : provider.provider_id)
                          }
                        >
                          View models
                        </Button>

                        {/* Delete provider button */}
                        <Button
                          variant="subtle"
                          color="red"
                          size="xs"
                          loading={
                            deleteProvider.isPending &&
                            deleteProvider.variables === provider.provider_id
                          }
                          onClick={() => deleteProvider.mutate(provider.provider_id)}
                        >
                          <Trash2 size={13} />
                        </Button>
                      </div>
                    </div>

                    {/* Expander Panel */}
                    {isExpanded && (
                      <div className={classes.modelsExpanderPanel}>
                        <div className={classes.providerModelsSection} style={{ border: 'none', padding: 0 }}>
                          <span className={classes.modelsSectionTitle} style={{ marginBottom: '8px', display: 'block' }}>Configured Models</span>
                          {provider.models.length === 0 ? (
                            <span className={classes.noModelsHint}>No models added yet.</span>
                          ) : (
                            <div className={classes.providerModelsGrid}>
                              {provider.models.map((model) => (
                                <div key={model.model_id} className={classes.modelBadgeItem}>
                                  <span style={{ fontWeight: 500 }}>
                                    {model.display_name ?? model.model_name}
                                  </span>
                                  <Badge size="xs" variant="light" color="gray">
                                    {model.ai_type}
                                  </Badge>
                                  <button
                                    className={classes.modelBadgeDelete}
                                    type="button"
                                    onClick={() =>
                                      deleteModel.mutate({
                                        providerId: provider.provider_id,
                                        modelId: model.model_id,
                                      })
                                    }
                                    title="Remove model"
                                  >
                                    <X size={10} />
                                  </button>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        <Divider />

                        {/* Inline Add Model */}
                        <div className={classes.providerCardFooter} style={{ padding: 0 }}>
                          {!isFormOpen ? (
                            <Button
                              variant="light"
                              size="xs"
                              leftSection={<Plus size={13} />}
                              onClick={() => {
                                setAddingModelProviderId(provider.provider_id)
                                setAiType('llm')
                                setModelName('')
                                setDisplayName('')
                              }}
                              style={{ width: 'fit-content' }}
                            >
                              Add Model
                            </Button>
                          ) : (
                            <div className={classes.inlineAddForm} style={{ padding: 0, border: 'none', backgroundColor: 'transparent' }}>
                              <div className={classes.inlineFormHeader} style={{ marginBottom: '8px' }}>
                                <span className={classes.inlineFormTitle}>Add New Model</span>
                                <button
                                  type="button"
                                  className={classes.advancedFormToggle}
                                  onClick={() => setShowAdvanced(!showAdvanced)}
                                >
                                  {showAdvanced ? 'Hide Advanced' : 'Show Advanced'}
                                </button>
                              </div>

                              <Stack gap={8}>
                                <TextInput
                                  placeholder="Model ID (e.g. gpt-4o)"
                                  value={modelName}
                                  onChange={(e) => setModelName(e.currentTarget.value)}
                                  size="xs"
                                  required
                                />
                                <TextInput
                                  placeholder="Display Name (optional)"
                                  value={displayName}
                                  onChange={(e) => setDisplayName(e.currentTarget.value)}
                                  size="xs"
                                />
                                <Select
                                  placeholder="AI Type"
                                  data={data.ai_types}
                                  value={aiType}
                                  onChange={(val) => setAiType((val as ModelAiType) ?? 'llm')}
                                  size="xs"
                                />

                                {showAdvanced && (
                                  <Stack gap={8} mt={4}>
                                    <NumberInput
                                      placeholder="Dimension (for embeddings)"
                                      value={dimension}
                                      onChange={(dimension) => setDimension(dimension)}
                                      size="xs"
                                    />
                                    <NumberInput
                                      placeholder="Context Window"
                                      value={contextWindow}
                                      onChange={(contextWindow) => setContextWindow(contextWindow)}
                                      size="xs"
                                    />
                                    <NumberInput
                                      placeholder="Max Tokens"
                                      value={maxTokens}
                                      onChange={(maxTokens) => setMaxTokens(maxTokens)}
                                      size="xs"
                                    />
                                  </Stack>
                                )}

                                <Group justify="flex-end" gap={6} mt={6}>
                                  <Button
                                    size="xs"
                                    variant="subtle"
                                    color="gray"
                                    onClick={() => {
                                      setAddingModelProviderId(null)
                                      setShowAdvanced(false)
                                    }}
                                  >
                                    Cancel
                                  </Button>
                                  <Button
                                    size="xs"
                                    loading={createModel.isPending}
                                    onClick={() => handleCreateModel(provider.provider_id)}
                                  >
                                    Save
                                  </Button>
                                </Group>
                              </Stack>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Right Column */}
      <div className={classes.rightColumn}>
        <div>
          <h3 className={classes.dashboardSectionTitle}>Available models</h3>
        </div>

        {/* Search presets */}
        <TextInput
          leftSection={<Search size={14} />}
          placeholder="Search models..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.currentTarget.value)}
          size="sm"
        />

        {/* Category Scroll chips */}
        <div className={classes.filterScrollArea}>
          {ALL_FILTER_TAGS.map((tag) => {
            const isActive = filterChip === tag
            return (
              <button
                key={tag}
                type="button"
                className={`${classes.filterChip} ${isActive ? classes.filterChipActive : ''}`}
                onClick={() => setFilterChip(tag)}
              >
                {tag}
              </button>
            )
          })}
        </div>

        {/* Presets List */}
        <div className={classes.availablePresetsList}>
          {filteredPresets.map((preset) => (
            <button
              key={preset.name}
              className={classes.presetCardSimple}
              type="button"
              onClick={() => handlePresetClick(preset)}
            >
              <div className={classes.presetCardSimpleHeader}>
                <div className={classes.presetCardSimpleTitleGroup}>
                  <ProviderLogo name={preset.name} size={24} />
                  <span className={classes.presetCardSimpleTitle}>{preset.name}</span>
                </div>
                <span className={classes.presetCardSimpleArrow}>↗</span>
              </div>
              <div className={classes.presetCardSimpleTags}>
                {preset.capabilities.map((cap) => (
                  <span key={cap} className={classes.presetCardSimpleTag}>
                    {cap}
                  </span>
                ))}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Preset Connect Modal */}
      <Modal
        opened={connectingPreset !== null}
        onClose={() => setConnectingPreset(null)}
        withCloseButton={false}
        padding={0}
        radius="lg"
        size="md"
        centered
      >
        {connectingPreset && (
          <div className={styles.premiumModalContainer}>
            <div className={styles.premiumModalBanner}>
              <div className={styles.premiumModalBannerGlow} />
              <div className={styles.premiumModalHeader}>
                <div />
                <ActionIcon variant="subtle" color="gray" onClick={() => setConnectingPreset(null)}>
                  <X size={18} />
                </ActionIcon>
              </div>
              <div className={styles.premiumModalLogoWrapper}>
                <ProviderLogo name={connectingPreset.name} size={42} />
              </div>
              <h2 className={styles.premiumModalTitle}>Connect {connectingPreset.name}</h2>
              <p className={styles.premiumModalSubtitle}>{getProviderHelperText(connectingPreset.name)}</p>
            </div>

            <div className={styles.premiumModalBody}>
              <TextInput
                label="Provider Name"
                value={connectingPreset?.name ?? ''}
                readOnly
                disabled
                variant="filled"
                size="md"
              />

              {connectingPreset.provider_type !== 'local_hash' &&
               connectingPreset.provider_type !== 'local_bge' ? (
                <>
                  <TextInput
                    label="Base URL"
                    placeholder="e.g. https://api.openai.com/v1"
                    value={presetBaseUrl}
                    onChange={(e) => setPresetBaseUrl(e.currentTarget.value)}
                    variant="filled"
                    size="md"
                  />
                  <PasswordInput
                    label="API Key"
                    placeholder="api-key-here"
                    value={presetApiKey}
                    onChange={(e) => setPresetApiKey(e.currentTarget.value)}
                    variant="filled"
                    size="md"
                  />
                </>
              ) : (
                <div
                  style={{
                    padding: '16px',
                    borderRadius: '12px',
                    backgroundColor: 'rgba(59, 130, 246, 0.04)',
                    border: '1px dashed rgba(59, 130, 246, 0.25)',
                    fontSize: '13px',
                    color: 'var(--color-primary)',
                    textAlign: 'center',
                    fontWeight: 500,
                  }}
                >
                  This local provider runs embedded models inside RAGMax and requires no credentials.
                </div>
              )}

              <div className={styles.premiumModalActionArea}>
                <Button
                  leftSection={<Plus size={16} />}
                  loading={createProvider.isPending}
                  onClick={handleConnectPreset}
                  size="md"
                  radius="md"
                  fullWidth
                >
                  Connect Provider
                </Button>
              </div>
            </div>
          </div>
        )}
      </Modal>

      {/* Edit Credentials Modal */}
      <Modal
        opened={editingProvider !== null}
        onClose={() => setEditingProvider(null)}
        withCloseButton={false}
        padding={0}
        radius="lg"
        size="md"
        centered
      >
        {editingProvider && (
          <div className={styles.premiumModalContainer}>
            <div className={styles.premiumModalBanner}>
              <div className={styles.premiumModalBannerGlow} />
              <div className={styles.premiumModalHeader}>
                <div />
                <ActionIcon variant="subtle" color="gray" onClick={() => setEditingProvider(null)}>
                  <X size={18} />
                </ActionIcon>
              </div>
              <div className={styles.premiumModalLogoWrapper}>
                <ProviderLogo name={editingProvider.name} size={42} />
              </div>
              <h2 className={styles.premiumModalTitle}>Configure {editingProvider.name}</h2>
              <p className={styles.premiumModalSubtitle}>
                Update base API URL and token credentials for your model provider.
              </p>
            </div>

            <div className={styles.premiumModalBody}>
              {editingProvider.provider_type !== 'local_hash' &&
               editingProvider.provider_type !== 'local_bge' ? (
                <>
                  <TextInput
                    label="Base URL"
                    placeholder="e.g. https://api.openai.com/v1"
                    value={editingBaseUrl}
                    onChange={(e) => setEditingBaseUrl(e.currentTarget.value)}
                    variant="filled"
                    size="md"
                  />
                  <PasswordInput
                    label="API Key"
                    placeholder={
                      editingProvider.api_key_configured
                        ? editingProvider.api_key_masked ?? '••••••••'
                        : 'api-key-here'
                    }
                    value={editingApiKey}
                    onChange={(e) => setEditingApiKey(e.currentTarget.value)}
                    variant="filled"
                    size="md"
                  />
                </>
              ) : (
                <div
                  style={{
                    padding: '16px',
                    borderRadius: '12px',
                    backgroundColor: 'rgba(59, 130, 246, 0.04)',
                    border: '1px dashed rgba(59, 130, 246, 0.25)',
                    fontSize: '13px',
                    color: 'var(--color-primary)',
                    textAlign: 'center',
                    fontWeight: 500,
                  }}
                >
                  This local provider runs embedded models inside RAGMax and requires no credentials.
                </div>
              )}

              <div className={styles.premiumModalActionArea}>
                <Button
                  leftSection={<Save size={16} />}
                  loading={createProvider.isPending}
                  onClick={handleSaveCredentials}
                  size="md"
                  radius="md"
                  fullWidth
                >
                  Save Credentials
                </Button>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

const CONFIG_SECTION_ICONS: Record<string, React.ComponentType<any>> = {
  storage: HardDrive,
  parser: FileText,
  vector: Database,
  retrieval: Search,
  query: MessageSquare,
  hybrid: Network,
  reranking: Sliders,
  context: Layers,
  llm_runtime: Cpu,
}

function isFieldModified(
  field: RuntimeConfigurationField,
  overrides: Record<string, string | number | boolean | null>,
): boolean {
  if (!Object.hasOwn(overrides, field.key)) return false
  const overrideVal = overrides[field.key]
  if (overrideVal === null) return field.source === 'db'
  if (field.secret) {
    return overrideVal !== ''
  }
  return overrideVal !== field.value
}

function ConfigurationPanel() {
  const { t } = useTranslation()
  const configuration = useRuntimeConfiguration()
  const updateConfiguration = useUpdateRuntimeConfiguration()
  const [overrides, setOverrides] = useState<Record<string, string | number | boolean | null>>({})
  const [activeSubSection, setActiveSubSection] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')

  if (configuration.isLoading) {
    return <Loader size="sm" />
  }

  if (configuration.isError) {
    return <Alert color="red">{formatApiError(configuration.error)}</Alert>
  }

  const fields = configuration.data?.fields ?? []
  const sectionNames = Array.from(new Set(fields.map((field) => field.section)))

  const firstSection = sectionNames[0] ?? ''
  const currentSubSection = activeSubSection || firstSection

  function updateField(key: string, value: string | number | boolean | null) {
    setOverrides((current) => ({ ...current, [key]: value }))
  }

  function handleDiscard() {
    setOverrides({})
    notifications.show({
      color: 'gray',
      title: t('settings.discarded', 'Changes Discarded'),
      message: t('settings.discardedMessage', 'Your unsaved configuration changes have been discarded.'),
    })
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

  const isSearching = searchQuery.trim().length > 0
  const filteredFields = fields.filter((field) => {
    if (isSearching) {
      const q = searchQuery.toLowerCase()
      return (
        field.key.toLowerCase().includes(q) ||
        field.label.toLowerCase().includes(q) ||
        (CONFIG_SECTION_LABELS[field.section] || field.section).toLowerCase().includes(q)
      )
    }
    return field.section === currentSubSection
  })

  const modifiedFieldsCount = fields.filter((field) => isFieldModified(field, overrides)).length
  const hasChanges = modifiedFieldsCount > 0

  const subSidebar = (
    <div className={classes.configSubSidebar}>
      <div className={classes.configSearchWrapper}>
        <Search size={14} className={classes.searchIcon} />
        <input
          type="text"
          placeholder="Search settings..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className={classes.configSearchInput}
        />
        {searchQuery && (
          <button
            type="button"
            onClick={() => setSearchQuery('')}
            className={classes.clearSearchButton}
          >
            <X size={14} />
          </button>
        )}
      </div>

      {!isSearching && (
        <Stack gap={4} className={classes.configSubMenuList}>
          {sectionNames.map((section) => {
            const Icon = CONFIG_SECTION_ICONS[section] || Globe
            const isActive = section === currentSubSection
            const sectionModifiedCount = fields
              .filter((f) => f.section === section)
              .filter((f) => isFieldModified(f, overrides)).length

            return (
              <button
                key={section}
                type="button"
                className={`${classes.configSubNavButton} ${
                  isActive ? classes.configSubNavButtonActive : ''
                }`}
                onClick={() => setActiveSubSection(section)}
              >
                <Icon size={16} />
                <span className={classes.configSubNavText}>
                  {CONFIG_SECTION_LABELS[section] ?? section}
                </span>
                {sectionModifiedCount > 0 && (
                  <Badge size="xs" color="orange" circle>
                    {sectionModifiedCount}
                  </Badge>
                )}
              </button>
            )
          })}
        </Stack>
      )}
    </div>
  )

  const rightPanel = (
    <div className={classes.configFormArea}>
      {isSearching ? (
        <div className={classes.configSectionHeader}>
          <div className={classes.configHeaderTitleGroup}>
            <Search size={22} className={classes.configHeaderIcon} />
            <div>
              <h3 className={classes.configHeaderTitle}>
                Search Results
              </h3>
              <p className={classes.configHeaderSubtitle}>
                Found {filteredFields.length} settings matching "{searchQuery}"
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className={classes.configSectionHeader}>
          <div className={classes.configHeaderTitleGroup}>
            {(() => {
              const Icon = CONFIG_SECTION_ICONS[currentSubSection] || Globe
              return <Icon size={22} className={classes.configHeaderIcon} />
            })()}
            <div>
              <h3 className={classes.configHeaderTitle}>
                {CONFIG_SECTION_LABELS[currentSubSection] ?? currentSubSection}
              </h3>
              <p className={classes.configHeaderSubtitle}>
                Manage settings for {CONFIG_SECTION_LABELS[currentSubSection] ?? currentSubSection}
              </p>
            </div>
          </div>
        </div>
      )}

      {filteredFields.length === 0 ? (
        <div className={classes.noResults}>
          <AlertCircle size={24} />
          <Text size="sm" c="dimmed">
            No settings found matching your search.
          </Text>
        </div>
      ) : (
        <div className={classes.configRowsList}>
          {filteredFields.map((field) => (
            <ConfigurationFieldControl
              key={field.key}
              field={field}
              value={configurationFieldValue(field, overrides)}
              isModified={isFieldModified(field, overrides)}
              onChange={(value) => updateField(field.key, value)}
              onDiscard={() => {
                setOverrides((current) => {
                  const copy = { ...current }
                  delete copy[field.key]
                  return copy
                })
              }}
              onResetToEnv={() => {
                updateField(field.key, null)
              }}
            />
          ))}
        </div>
      )}
    </div>
  )

  const stickyFooter = hasChanges ? (
    <div className={classes.configStickyFooter}>
      <div className={classes.configStickyFooterContent}>
        <div className={classes.configStickyFooterTextGroup}>
          <AlertCircle size={18} className={classes.configStickyFooterIcon} />
          <Text size="sm" fw={500} className={classes.configStickyFooterText}>
            You have {modifiedFieldsCount} unsaved configuration {modifiedFieldsCount === 1 ? 'change' : 'changes'}
          </Text>
        </div>
        <Group gap="sm">
          <Button
            variant="subtle"
            color="gray"
            size="sm"
            onClick={handleDiscard}
            disabled={updateConfiguration.isPending}
          >
            Discard
          </Button>
          <Button
            leftSection={<Save size={15} />}
            loading={updateConfiguration.isPending}
            onClick={handleSave}
            size="sm"
            color="blue"
          >
            Save Changes
          </Button>
        </Group>
      </div>
    </div>
  ) : null

  return (
    <div className={classes.configContainer}>
      <div className={classes.configPanelHeader}>
        <PanelHeader
          title={t('settings.configuration.title')}
          subtitle={t('settings.configuration.subtitle')}
        />
      </div>

      <div className={classes.configPanelLayout}>
        {subSidebar}
        {rightPanel}
      </div>

      {stickyFooter}
    </div>
  )
}

function ConfigurationFieldControl({
  field,
  value,
  isModified,
  onChange,
  onDiscard,
  onResetToEnv,
}: {
  field: RuntimeConfigurationField
  value: string | number | boolean | null | undefined
  isModified: boolean
  onChange: (value: string | number | boolean | null) => void
  onDiscard: () => void
  onResetToEnv: () => void
}) {
  const isDbSource = field.source === 'db'
  const canReset = isDbSource || isModified

  const statusBadge = isModified ? (
    <Badge size="xs" color="orange" variant="light">
      Unsaved
    </Badge>
  ) : isDbSource ? (
    <Badge size="xs" color="blue" variant="light">
      Database
    </Badge>
  ) : (
    <Badge size="xs" color="gray" variant="light">
      System
    </Badge>
  )

  const resetButton = canReset ? (
    <Tooltip label={isModified ? "Discard unsaved changes" : "Reset to system default (.env)"}>
      <Button
        size="compact-xs"
        variant="subtle"
        color="gray"
        onClick={() => {
          if (isModified) {
            onDiscard()
          } else {
            onResetToEnv()
          }
        }}
        className={classes.resetButton}
      >
        <RotateCcw size={13} />
      </Button>
    </Tooltip>
  ) : null

  return (
    <div className={`${classes.configRow} ${isModified ? classes.configRowModified : ''}`}>
      <div className={classes.configMeta}>
        <div className={classes.configLabelGroup}>
          <span className={classes.configLabelText}>{field.label}</span>
          {statusBadge}
        </div>
        <code className={classes.configKeyText}>{field.key}</code>
      </div>
      <div className={classes.configInputWrapper}>
        <div className={classes.configInputControl}>
          {renderControl(field, value, onChange)}
        </div>
        {resetButton}
      </div>
    </div>
  )
}

function renderControl(
  field: RuntimeConfigurationField,
  value: string | number | boolean | null | undefined,
  onChange: (value: string | number | boolean | null) => void,
) {
  if (field.value_type === 'boolean') {
    return (
      <Switch
        checked={Boolean(value)}
        onChange={(event) => onChange(event.currentTarget.checked)}
      />
    )
  }

  if (field.secret) {
    return (
      <PasswordInput
        placeholder={field.masked_value ?? 'Not configured'}
        value={typeof value === 'string' ? value : ''}
        onChange={(event) => onChange(event.currentTarget.value)}
        styles={{ input: { fontFamily: 'monospace' } }}
      />
    )
  }

  if (field.value_type === 'integer' || field.value_type === 'float') {
    return (
      <NumberInput
        value={typeof value === 'number' || typeof value === 'string' ? value : ''}
        onChange={(nextValue) => onChange(nextValue === '' ? null : nextValue)}
      />
    )
  }

  if (field.value_type === 'select') {
    return (
      <Select
        clearable
        data={field.options}
        value={typeof value === 'string' ? value : null}
        onChange={(nextValue) => onChange(nextValue)}
      />
    )
  }

  return (
    <TextInput
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
