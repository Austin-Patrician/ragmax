import { Alert, Badge, Code, Paper, SimpleGrid, Stack, Text } from '@mantine/core'
import { useTranslation } from 'react-i18next'
import type { ArtifactData } from '@/types'

type VectorStatsViewerProps = {
  data: ArtifactData
}

export function VectorStatsViewer({ data }: VectorStatsViewerProps) {
  const { t } = useTranslation()
  const statsData = Array.isArray(data.data) ? data.data[0] : data.data

  if (!statsData || typeof statsData !== 'object') {
    return (
      <Text c="dimmed" size="sm">
        {t('indexing.noData')}
      </Text>
    )
  }

  const totalVectors = (statsData as any).total_vectors || (statsData as any).vector_count || 0
  const dimension = (statsData as any).dimension || (statsData as any).embedding_dimension
  const successCount = (statsData as any).success_count || (statsData as any).successful || totalVectors
  const failureCount = (statsData as any).failure_count || (statsData as any).failed || 0
  const errors = (statsData as any).errors || []

  return (
    <Stack gap="md">
      <Paper withBorder p="md" radius="md">
        <Text fw={700} size="sm" mb="sm">
          {t('indexing.vectorStats')}
        </Text>
        <SimpleGrid cols={2} spacing="md">
          <StatItem
            label={t('indexing.totalVectors')}
            value={totalVectors}
            badge={<Badge color="blue">{totalVectors}</Badge>}
          />
          <StatItem
            label={t('indexing.dimension')}
            value={dimension || '-'}
            badge={dimension ? <Badge color="gray">{dimension}D</Badge> : undefined}
          />
          <StatItem
            label={t('indexing.successCount')}
            value={successCount}
            badge={<Badge color="green">{successCount}</Badge>}
          />
          <StatItem
            label={t('indexing.failureCount')}
            value={failureCount}
            badge={
              <Badge color={failureCount > 0 ? 'red' : 'gray'}>
                {failureCount}
              </Badge>
            }
          />
        </SimpleGrid>
      </Paper>

      {Array.isArray(errors) && errors.length > 0 && (
        <Paper withBorder p="md" radius="md">
          <Text fw={700} size="sm" mb="sm" c="red">
            {t('indexing.errors')} ({errors.length})
          </Text>
          <Stack gap="xs">
            {errors.slice(0, 5).map((error: any, index: number) => (
              <Alert key={index} color="red" variant="light">
                <Text size="xs">
                  {typeof error === 'string' ? error : error.message || JSON.stringify(error)}
                </Text>
              </Alert>
            ))}
            {errors.length > 5 && (
              <Text size="xs" c="dimmed">
                ... and {errors.length - 5} more errors
              </Text>
            )}
          </Stack>
        </Paper>
      )}

      <Paper withBorder p="md" radius="md">
        <Text fw={700} size="sm" mb="sm">
          {t('indexing.summary')}
        </Text>
        <Code block>{JSON.stringify(statsData, null, 2)}</Code>
      </Paper>
    </Stack>
  )
}

function StatItem({
  label,
  value,
  badge,
}: {
  label: string
  value: string | number
  badge?: React.ReactNode
}) {
  return (
    <div>
      <Text size="xs" c="dimmed" mb={4}>
        {label}
      </Text>
      {badge || (
        <Text size="lg" fw={700}>
          {value}
        </Text>
      )}
    </div>
  )
}
