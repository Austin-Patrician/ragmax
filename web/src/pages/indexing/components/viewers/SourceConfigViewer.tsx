import { Code, Paper, SimpleGrid, Stack, Text } from '@mantine/core'
import { useTranslation } from 'react-i18next'
import type { ArtifactData } from '@/types'

type SourceConfigViewerProps = {
  data: ArtifactData
}

export function SourceConfigViewer({ data }: SourceConfigViewerProps) {
  const { t } = useTranslation()
  const sourceData = Array.isArray(data.data) ? data.data[0] : data.data

  if (!sourceData || typeof sourceData !== 'object') {
    return (
      <Text c="dimmed" size="sm">
        {t('indexing.noData')}
      </Text>
    )
  }

  const metadata = (sourceData as any).metadata || {}
  const config = (sourceData as any).config || {}

  return (
    <Stack gap="md">
      <Paper withBorder p="md" radius="md">
        <Text fw={700} size="sm" mb="sm">
          {t('indexing.sourceConfig')}
        </Text>
        <SimpleGrid cols={2} spacing="sm">
          <InfoItem label={t('indexing.effectiveProfile')} value={(sourceData as any).effective_profile} />
          <InfoItem label={t('indexing.effectiveParser')} value={(sourceData as any).effective_parser} />
          <InfoItem label="Source ID" value={(sourceData as any).source_id} />
          <InfoItem label="Notebook ID" value={(sourceData as any).notebook_id} />
        </SimpleGrid>
      </Paper>

      {Object.keys(config).length > 0 && (
        <Paper withBorder p="md" radius="md">
          <Text fw={700} size="sm" mb="sm">
            {t('indexing.runConfig')}
          </Text>
          <Code block>{JSON.stringify(config, null, 2)}</Code>
        </Paper>
      )}

      {Object.keys(metadata).length > 0 && (
        <Paper withBorder p="md" radius="md">
          <Text fw={700} size="sm" mb="sm">
            {t('indexing.metadata')}
          </Text>
          <Code block>{JSON.stringify(metadata, null, 2)}</Code>
        </Paper>
      )}

      <Paper withBorder p="md" radius="md">
        <Text fw={700} size="sm" mb="sm">
          {t('indexing.summary')}
        </Text>
        <Code block>{JSON.stringify(sourceData, null, 2)}</Code>
      </Paper>
    </Stack>
  )
}

function InfoItem({ label, value }: { label: string; value: any }) {
  return (
    <div>
      <Text size="xs" c="dimmed" mb={4}>
        {label}
      </Text>
      <Text size="sm" fw={600}>
        {value ? String(value) : '-'}
      </Text>
    </div>
  )
}
