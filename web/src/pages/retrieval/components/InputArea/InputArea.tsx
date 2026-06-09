import { ActionIcon, Group, Paper, Textarea, Tooltip } from '@mantine/core'
import { IconMicrophone, IconPaperclip, IconSend } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import type { RetrievalMode } from '../../types'
import BottomToolbar from './BottomToolbar'
import classes from './InputArea.module.css'

interface InputAreaProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
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

export default function InputArea({
  value,
  onChange,
  onSend,
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
}: InputAreaProps) {
  const { t } = useTranslation()
  const canSend = Boolean(value.trim() && selectedDataset)

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  return (
    <section className={classes.container} aria-label="Message input">
      <Paper className={classes.composer ?? ''} withBorder>
        <Group gap="sm" align="flex-end" className={classes.inputBar ?? ''}>
          <Tooltip label="Attach file" withArrow>
            <ActionIcon
              className={classes.iconButton ?? ''}
              size="lg"
              variant="subtle"
              aria-label="Attach file"
            >
              <IconPaperclip size={20} />
            </ActionIcon>
          </Tooltip>

          <Textarea
            aria-label={t('retrieval.typeMessage')}
            placeholder={t('retrieval.typeMessage')}
            autosize
            minRows={1}
            maxRows={5}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            className={classes.textarea ?? ''}
            classNames={{ input: classes.textareaInput ?? '' }}
          />

          <Group gap="xs" wrap="nowrap" className={classes.actionGroup ?? ''}>
            <Tooltip label="Voice input" withArrow>
              <ActionIcon
                className={classes.iconButton ?? ''}
                size="lg"
                variant="subtle"
                aria-label="Voice input"
              >
                <IconMicrophone size={20} />
              </ActionIcon>
            </Tooltip>

            <Tooltip label="Send" withArrow>
              <ActionIcon
                className={classes.sendButton ?? ''}
                size="lg"
                variant="filled"
                onClick={onSend}
                disabled={!canSend}
                aria-label="Send"
              >
                <IconSend size={20} />
              </ActionIcon>
            </Tooltip>
          </Group>
        </Group>

        <BottomToolbar
          mode={mode}
          onModeChange={onModeChange}
          selectedModel={selectedModel}
          onModelChange={onModelChange}
          selectedDataset={selectedDataset}
          onDatasetChange={onDatasetChange}
          webSearchEnabled={webSearchEnabled}
          onWebSearchChange={onWebSearchChange}
          thinkingMode={thinkingMode}
          onThinkingModeChange={onThinkingModeChange}
          onNewConversation={onNewConversation}
        />
      </Paper>
    </section>
  )
}
