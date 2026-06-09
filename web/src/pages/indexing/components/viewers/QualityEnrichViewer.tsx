import { Badge, Button, Group, Paper, Progress, SimpleGrid, Stack, Table, Text, ScrollArea } from '@mantine/core'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { ArtifactData } from '@/types'
import classes from './TableViewer.module.css'

type QualityEnrichViewerProps = {
  data: ArtifactData
}

const PAGE_SIZE = 50

export function QualityEnrichViewer({ data }: QualityEnrichViewerProps) {
  const { t } = useTranslation()
  const [page, setPage] = useState(0)

  const nodes = Array.isArray(data.data) ? data.data : []
  const totalPages = Math.ceil(nodes.length / PAGE_SIZE)
  const startIndex = page * PAGE_SIZE
  const endIndex = Math.min(startIndex + PAGE_SIZE, nodes.length)
  const pageNodes = nodes.slice(startIndex, endIndex)

  // Calculate stats
  const nodesWithQuality = nodes.filter((n: any) => n.quality_score !== undefined)
  const avgQuality = nodesWithQuality.length > 0
    ? (nodesWithQuality.reduce((sum: number, n: any) => sum + (n.quality_score || 0), 0) / nodesWithQuality.length).toFixed(2)
    : 0
  const totalWarnings = nodes.reduce((sum: number, n: any) => sum + (n.warnings?.length || 0), 0)

  if (nodes.length === 0) {
    return (
      <Text c="dimmed" size="sm">
        {t('indexing.noResults')}
      </Text>
    )
  }

  return (
    <Stack gap="md">
      <Paper withBorder p="md" radius="md" className={classes.statsCard || ''}>
        <Text fw={700} size="sm" mb="sm">
          {t('indexing.qualityStats')}
        </Text>
        <SimpleGrid cols={3} spacing="md">
          <StatItem label={t('common.nodes')} value={nodes.length} />
          <StatItem label={t('indexing.avgQuality')} value={avgQuality} />
          <StatItem label={t('indexing.warningCount')} value={totalWarnings} />
        </SimpleGrid>
      </Paper>

      <Paper withBorder p="sm" radius="md" className={classes.paginationBar || ''}>
        <Group justify="space-between">
          <div>
            <Text size="sm" fw={700}>
              {t('indexing.qualityEnrich')}
            </Text>
          </div>
          {totalPages > 1 && (
            <Group gap="xs">
              <Button
                size="compact-sm"
                variant="light"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
              >
                {t('indexing.previous')}
              </Button>
              <Text size="xs" c="dimmed">
                {t('indexing.page')} {page + 1} {t('indexing.of')} {totalPages}
              </Text>
              <Button
                size="compact-sm"
                variant="light"
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page === totalPages - 1}
              >
                {t('indexing.next')}
              </Button>
            </Group>
          )}
        </Group>
      </Paper>

      <ScrollArea className={classes.tableContainer || ''}>
        <Table striped highlightOnHover withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th style={{ width: '100px' }}>{t('indexing.nodeId')}</Table.Th>
              <Table.Th style={{ width: '120px' }}>{t('indexing.qualityScore')}</Table.Th>
              <Table.Th style={{ width: '150px' }}>{t('indexing.warnings')}</Table.Th>
              <Table.Th>{t('indexing.text')}</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {pageNodes.map((node: any, index: number) => (
              <Table.Tr key={node.node_id || index}>
                <Table.Td>
                  <Text size="xs" ff="monospace">
                    {String(node.node_id || index)}
                  </Text>
                </Table.Td>
                <Table.Td>
                  {node.quality_score !== undefined ? (
                    <Stack gap={4}>
                      <Text size="sm" fw={600}>
                        {(node.quality_score * 100).toFixed(0)}%
                      </Text>
                      <Progress
                        value={node.quality_score * 100}
                        size="xs"
                        color={getQualityColor(node.quality_score)}
                      />
                    </Stack>
                  ) : (
                    <Text size="xs" c="dimmed">
                      -
                    </Text>
                  )}
                </Table.Td>
                <Table.Td>
                  {Array.isArray(node.warnings) && node.warnings.length > 0 ? (
                    <Stack gap={4}>
                      {node.warnings.slice(0, 2).map((warning: any, i: number) => (
                        <Badge key={i} size="xs" color="yellow" variant="light">
                          {typeof warning === 'string' ? warning : warning.type || 'warning'}
                        </Badge>
                      ))}
                      {node.warnings.length > 2 && (
                        <Text size="xs" c="dimmed">
                          +{node.warnings.length - 2} more
                        </Text>
                      )}
                    </Stack>
                  ) : (
                    <Text size="xs" c="dimmed">
                      -
                    </Text>
                  )}
                </Table.Td>
                <Table.Td>
                  <Text size="sm" lineClamp={3}>
                    {node.text || node.enriched_text || '-'}
                  </Text>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </ScrollArea>
    </Stack>
  )
}

function StatItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <Text size="xs" c="dimmed" mb={4}>
        {label}
      </Text>
      <Text size="lg" fw={700}>
        {value}
      </Text>
    </div>
  )
}

function getQualityColor(score: number): string {
  if (score >= 0.8) return 'green'
  if (score >= 0.6) return 'yellow'
  return 'red'
}
