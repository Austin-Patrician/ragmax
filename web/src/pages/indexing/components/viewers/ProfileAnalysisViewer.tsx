import { Badge, Code, Group, Paper, SimpleGrid, Stack, Text } from '@mantine/core'
import { useTranslation } from 'react-i18next'
import type { ArtifactData } from '@/types'

type ProfileAnalysisViewerProps = {
  data: ArtifactData
}

export function ProfileAnalysisViewer({ data }: ProfileAnalysisViewerProps) {
  const { t } = useTranslation()
  const analysisData = Array.isArray(data.data) ? data.data[0] : data.data

  if (!analysisData || typeof analysisData !== 'object') {
    return (
      <Text c="dimmed" size="sm">
        {t('indexing.noData')}
      </Text>
    )
  }

  const profile = (analysisData as any).recommended_profile || (analysisData as any).profile
  const traits = (analysisData as any).detected_traits || (analysisData as any).traits || []
  const strategy = (analysisData as any).strategy || {}

  return (
    <Stack gap="md">
      <Paper withBorder p="md" radius="md">
        <Text fw={700} size="sm" mb="sm">
          {t('indexing.profileAnalysis')}
        </Text>
        <SimpleGrid cols={2} spacing="md">
          <div>
            <Text size="xs" c="dimmed" mb={4}>
              {t('indexing.recommendedProfile')}
            </Text>
            <Badge size="lg" variant="filled">
              {profile || 'default'}
            </Badge>
          </div>
        </SimpleGrid>
      </Paper>

      {Array.isArray(traits) && traits.length > 0 && (
        <Paper withBorder p="md" radius="md">
          <Text fw={700} size="sm" mb="sm">
            {t('indexing.detectedTraits')}
          </Text>
          <Group gap="xs">
            {traits.map((trait: any, index: number) => (
              <Badge key={index} size="sm" variant="light">
                {typeof trait === 'string' ? trait : trait.name || String(trait)}
              </Badge>
            ))}
          </Group>
        </Paper>
      )}

      {Object.keys(strategy).length > 0 && (
        <Paper withBorder p="md" radius="md">
          <Text fw={700} size="sm" mb="sm">
            {t('indexing.strategy')}
          </Text>
          <Code block>{JSON.stringify(strategy, null, 2)}</Code>
        </Paper>
      )}

      <Paper withBorder p="md" radius="md">
        <Text fw={700} size="sm" mb="sm">
          {t('indexing.summary')}
        </Text>
        <Code block>{JSON.stringify(analysisData, null, 2)}</Code>
      </Paper>
    </Stack>
  )
}
