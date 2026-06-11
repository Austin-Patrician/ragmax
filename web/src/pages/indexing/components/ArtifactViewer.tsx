import { Alert, Code, Group, Loader, Paper, ScrollArea, Stack, Text,Badge  } from '@mantine/core'
import { useTranslation } from 'react-i18next'
import type { ArtifactData, IndexingStageName } from '@/types'
import { SourceConfigViewer } from './viewers/SourceConfigViewer'
import { BlocksTableViewer } from './viewers/BlocksTableViewer'
import { ProfileAnalysisViewer } from './viewers/ProfileAnalysisViewer'
import { ChunksTableViewer } from './viewers/ChunksTableViewer'
import { QualityEnrichViewer } from './viewers/QualityEnrichViewer'
import { VectorStatsViewer } from './viewers/VectorStatsViewer'
import classes from './ArtifactViewer.module.css'

type ArtifactViewerProps = {
  stageName: IndexingStageName
  artifactData: ArtifactData | null
  isLoading: boolean
  error: Error | null
}

export function ArtifactViewer({ stageName, artifactData, isLoading, error }: ArtifactViewerProps) {
  const { t } = useTranslation()

  if (isLoading) {
    return (
      <Paper withBorder radius="lg" p="md" className={classes.container || ''}>
        <Stack align="center" justify="center" style={{ minHeight: 300 }}>
          <Loader size="md" />
          <Text size="sm" c="dimmed">
            {t('common.loading')}
          </Text>
        </Stack>
      </Paper>
    )
  }

  if (error) {
    return (
      <Paper withBorder radius="lg" p="md" className={classes.container || ''}>
        <Alert color="red" title="Error loading artifacts">
          {error.message}
        </Alert>
      </Paper>
    )
  }

  if (!artifactData) {
    return (
      <Paper withBorder radius="lg" p="md" className={classes.container || ''}>
        <Stack align="center" justify="center" style={{ minHeight: 300 }}>
          <Text size="sm" c="dimmed">
            {t('indexing.noArtifacts')}
          </Text>
        </Stack>
      </Paper>
    )
  }

  return (
    <Paper radius="md" p="xl" className={classes.container || ''}>
      <div className={classes.header}>
        <Text fw={700} size="xl" style={{ color: '#1e293b' }}>
          {t('indexing.artifactViewer', 'Artifact Viewer')}
        </Text>
        <Group gap="xs" mt={8}>
          <Badge variant="light" color="indigo" size="sm">
            {artifactData.manifest.artifact_type}
          </Badge>
          <Text size="xs" c="dimmed">
            •
          </Text>
          <Text size="xs" fw={600} style={{ color: '#64748b' }}>
            {artifactData.manifest.record_count} {t('indexing.records', 'records')}
          </Text>
          <Text size="xs" c="dimmed">
            •
          </Text>
          <Text size="xs" fw={600} style={{ color: '#64748b' }}>
            {formatBytes(artifactData.manifest.size_bytes)}
          </Text>
        </Group>
      </div>

      <ScrollArea className={classes.content || ''} style={{ flex: 1, minHeight: 0 }} offsetScrollbars>
        {renderViewer(stageName, artifactData)}
      </ScrollArea>
    </Paper>
  )
}

function renderViewer(stageName: IndexingStageName, artifactData: ArtifactData) {
  switch (stageName) {
    case 'source':
      return <SourceConfigViewer data={artifactData} />
    case 'parse_blocks':
      return <BlocksTableViewer data={artifactData} />
    case 'analyze_profile':
      return <ProfileAnalysisViewer data={artifactData} />
    case 'chunk_nodes':
      return <ChunksTableViewer data={artifactData} />
    case 'quality_enrich':
      return <QualityEnrichViewer data={artifactData} />
    case 'vectorize':
      return <VectorStatsViewer data={artifactData} />
    default:
      return <DefaultViewer data={artifactData} />
  }
}

function DefaultViewer({ data }: { data: ArtifactData }) {
  return (
    <Code block className={classes.jsonBlock || ''}>
      {JSON.stringify(data.data, null, 2)}
    </Code>
  )
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
