import { ActionIcon, Button, Group, Select, Tooltip } from '@mantine/core'
import {
  IconBrain,
  IconBug,
  IconChevronDown,
  IconCpu,
  IconDatabase,
  IconHome,
  IconWorld,
} from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import type { RetrievalMode } from '../../types'
import classes from './BottomToolbar.module.css'

interface BottomToolbarProps {
  mode: RetrievalMode
  onModeChange: (mode: RetrievalMode) => void
  selectedModel: string
  onModelChange: (model: string) => void
  selectedDataset: string | null
  onDatasetChange: (dataset: string | null) => void
  webSearchEnabled: boolean
  onWebSearchChange: (enabled: boolean) => void
  thinkingMode: boolean
  onThinkingModeChange: (enabled: boolean) => void
  onNewConversation: () => void
}

export default function BottomToolbar({
  mode,
  onModeChange,
  selectedModel,
  onModelChange,
  selectedDataset,
  onDatasetChange,
  webSearchEnabled,
  onWebSearchChange,
  thinkingMode,
  onThinkingModeChange,
  onNewConversation,
}: BottomToolbarProps) {
  const { t } = useTranslation()

  const modelOptions = [
    { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
    { value: 'gpt-4o', label: 'GPT-4o' },
    { value: 'claude-3.5-sonnet', label: 'Claude 3.5 Sonnet' },
    { value: 'claude-3-haiku', label: 'Claude 3 Haiku' },
  ]

  // TODO: Replace with actual dataset list from API
  const datasetOptions = [
    { value: 'docs', label: 'Documentation' },
    { value: 'papers', label: 'Research Papers' },
    { value: 'code', label: 'Code Snippets' },
  ]

  return (
    <Group gap="xs" justify="space-between" className={classes.toolbar ?? ''}>
      {/* Left: Main controls */}
      <Group gap="xs" className={classes.controlGroup ?? ''}>
        {/* New Conversation */}
        <Tooltip label={t('retrieval.newConversation')} withArrow>
          <ActionIcon
            className={classes.iconButton ?? ''}
            variant="subtle"
            size="md"
            onClick={onNewConversation}
            aria-label={t('retrieval.newConversation')}
          >
            <IconHome size={18} />
          </ActionIcon>
        </Tooltip>

        {/* Dev/Production Mode Toggle */}
        <Tooltip label={t('retrieval.toggleDebugMode')} withArrow>
          <Button
            className={classes.modeButton ?? ''}
            variant={mode === 'dev' ? 'filled' : 'subtle'}
            color={mode === 'dev' ? 'orange' : 'gray'}
            size="xs"
            leftSection={<IconBug size={16} />}
            onClick={() => onModeChange(mode === 'dev' ? 'production' : 'dev')}
          >
            {mode === 'dev' ? 'Dev' : 'Prod'}
          </Button>
        </Tooltip>

        {/* Model Selector */}
        <Select
          value={selectedModel}
          onChange={(value) => value && onModelChange(value)}
          data={modelOptions}
          aria-label="Model"
          className={`${classes.select ?? ''} ${classes.modelSelect ?? ''}`}
          classNames={{ input: classes.selectInput ?? '' }}
          size="xs"
          leftSection={<IconCpu size={16} />}
          rightSection={<IconChevronDown size={14} />}
          comboboxProps={{ shadow: 'md' }}
        />
      </Group>

      {/* Middle: Feature toggles */}
      <Group gap="xs" className={classes.controlGroup ?? ''}>
        {/* Web Search */}
        <Tooltip label={t('retrieval.webSearch')} withArrow>
          <ActionIcon
            className={classes.iconButton ?? ''}
            variant={webSearchEnabled ? 'filled' : 'subtle'}
            color={webSearchEnabled ? 'cyan' : 'gray'}
            size="md"
            onClick={() => onWebSearchChange(!webSearchEnabled)}
            aria-label={t('retrieval.webSearch')}
            aria-pressed={webSearchEnabled}
          >
            <IconWorld size={18} />
          </ActionIcon>
        </Tooltip>

        {/* Thinking Mode */}
        <Tooltip label={t('retrieval.thinkingMode')} withArrow>
          <ActionIcon
            className={classes.iconButton ?? ''}
            variant={thinkingMode ? 'filled' : 'subtle'}
            color={thinkingMode ? 'orange' : 'gray'}
            size="md"
            onClick={() => onThinkingModeChange(!thinkingMode)}
            aria-label={t('retrieval.thinkingMode')}
            aria-pressed={thinkingMode}
          >
            <IconBrain size={18} />
          </ActionIcon>
        </Tooltip>
      </Group>

      {/* Right: Dataset Selector */}
      <Group gap="xs" className={classes.datasetGroup ?? ''}>
        <Select
          value={selectedDataset}
          onChange={onDatasetChange}
          data={datasetOptions}
          aria-label={t('retrieval.selectDataset')}
          className={`${classes.select ?? ''} ${classes.datasetSelect ?? ''}`}
          classNames={{ input: classes.selectInput ?? '' }}
          size="xs"
          placeholder={t('retrieval.selectDataset')}
          leftSection={<IconDatabase size={16} />}
          rightSection={<IconChevronDown size={14} />}
          comboboxProps={{ shadow: 'md' }}
        />
      </Group>
    </Group>
  )
}
