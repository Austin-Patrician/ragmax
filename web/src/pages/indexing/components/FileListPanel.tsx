import { Alert, Badge, Group, Loader, Paper, ScrollArea, Stack, Text } from '@mantine/core'
import { FileText, CheckCircle2, Clock, XCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { StatusBadge } from '@/components/ui/StatusBadge'
import type { Source, IndexPipelineRun } from '@/types'
import classes from './FileListPanel.module.css'

type FileWithRun = {
  source: Source
  latestRun: IndexPipelineRun | null
}

type FileListPanelProps = {
  files: FileWithRun[]
  selectedSourceId: string | null
  onSelectFile: (sourceId: string) => void
  isLoading?: boolean
  error?: Error | null
}

export function FileListPanel({
  files,
  selectedSourceId,
  onSelectFile,
  isLoading,
  error,
}: FileListPanelProps) {
  const { t } = useTranslation()

  if (isLoading) {
    return (
      <Paper withBorder radius="lg" p="md" className={classes.container || ''}>
        <PanelHeader />
        <Stack align="center" justify="center" style={{ minHeight: 200 }}>
          <Loader size="md" />
        </Stack>
      </Paper>
    )
  }

  if (error) {
    return (
      <Paper withBorder radius="lg" p="md" className={classes.container || ''}>
        <PanelHeader />
        <Alert color="red">{error.message}</Alert>
      </Paper>
    )
  }

  if (files.length === 0) {
    return (
      <Paper withBorder radius="lg" p="md" className={classes.container || ''}>
        <PanelHeader />
        <Stack align="center" justify="center" style={{ minHeight: 200 }}>
          <Text c="dimmed" size="sm" ta="center">
            {t('indexing.noFiles')}
          </Text>
        </Stack>
      </Paper>
    )
  }

  return (
    <Paper withBorder radius="lg" p="md" className={classes.container || ''}>
      <PanelHeader />
      <ScrollArea className={classes.scrollArea || ''}>
        <Stack gap="xs">
          {files.map((item) => (
            <FileCard
              key={item.source.source_id}
              source={item.source}
              latestRun={item.latestRun}
              selected={item.source.source_id === selectedSourceId}
              onClick={() => onSelectFile(item.source.source_id)}
            />
          ))}
        </Stack>
      </ScrollArea>
    </Paper>
  )
}

function PanelHeader() {
  const { t } = useTranslation()

  return (
    <div className={classes.header}>
      <Text fw={700} size="lg">
        {t('indexing.fileList')}
      </Text>
      <Text size="xs" c="dimmed" mt={2}>
        {t('indexing.fileListSubtitle')}
      </Text>
    </div>
  )
}

type FileCardProps = {
  source: Source
  latestRun: IndexPipelineRun | null
  selected: boolean
  onClick: () => void
}

function FileCard({ source, latestRun, selected, onClick }: FileCardProps) {
  const icon = getStatusIcon(latestRun?.status)

  return (
    <button
      type="button"
      className={`${classes.fileCard} ${selected ? classes.fileCardSelected : ''}`}
      onClick={onClick}
      aria-pressed={selected}
      aria-label={`Select file ${source.filename || source.source_id}`}
    >
      <div className={classes.fileIcon}>{icon}</div>
      <div className={classes.fileBody}>
        <Group justify="space-between" gap="xs" wrap="nowrap">
          <Text fw={700} size="sm" lineClamp={1} className={classes.fileName || ''}>
            {source.filename || source.source_id}
          </Text>
          {latestRun ? <StatusBadge value={latestRun.status} /> : null}
        </Group>
        <Group gap={6} mt={4} wrap="nowrap">
          <Text size="xs" c="dimmed" lineClamp={1}>
            {formatFileSize(source.file_size)}
          </Text>
          {latestRun?.finished_at && (
            <>
              <Text size="xs" c="dimmed">
                •
              </Text>
              <Text size="xs" c="dimmed" lineClamp={1}>
                {formatDate(latestRun.finished_at)}
              </Text>
            </>
          )}
        </Group>
        {latestRun?.effective_profile && (
          <Badge size="xs" variant="light" mt={4}>
            {latestRun.effective_profile}
          </Badge>
        )}
      </div>
    </button>
  )
}

function getStatusIcon(status: string | undefined) {
  switch (status) {
    case 'succeeded':
    case 'completed':
      return <CheckCircle2 size={18} className={classes.iconSuccess} />
    case 'failed':
      return <XCircle size={18} className={classes.iconError} />
    case 'running':
    case 'pending':
      return <Clock size={18} className={classes.iconPending} />
    default:
      return <FileText size={18} className={classes.iconDefault} />
  }
}

function formatFileSize(bytes: number | null | undefined): string {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`

  return date.toLocaleDateString()
}
