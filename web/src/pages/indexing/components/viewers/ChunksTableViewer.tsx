import { Badge, Button, Group, Paper, SimpleGrid, Stack, Table, Text, ScrollArea } from '@mantine/core'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { ArtifactData } from '@/types'
import classes from './TableViewer.module.css'

type ChunksTableViewerProps = {
  data: ArtifactData
}

const PAGE_SIZE = 50

export function ChunksTableViewer({ data }: ChunksTableViewerProps) {
  const { t } = useTranslation()
  const [page, setPage] = useState(0)

  const chunks = Array.isArray(data.data) ? data.data : []
  const totalPages = Math.ceil(chunks.length / PAGE_SIZE)
  const startIndex = page * PAGE_SIZE
  const endIndex = Math.min(startIndex + PAGE_SIZE, chunks.length)
  const pageChunks = chunks.slice(startIndex, endIndex)

  // Calculate stats
  const avgLength = chunks.length > 0
    ? Math.round(chunks.reduce((sum: number, c: any) => sum + (c.text?.length || 0), 0) / chunks.length)
    : 0

  if (chunks.length === 0) {
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
          {t('indexing.chunkStats')}
        </Text>
        <SimpleGrid cols={2} spacing="md">
          <StatItem label={t('indexing.totalChunks')} value={chunks.length} />
          <StatItem label={t('indexing.avgLength')} value={`${avgLength} chars`} />
        </SimpleGrid>
      </Paper>

      <Paper withBorder p="sm" radius="md" className={classes.paginationBar || ''}>
        <Group justify="space-between">
          <div>
            <Text size="sm" fw={700}>
              {t('indexing.chunksTable')}
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
              <Table.Th style={{ width: '120px' }}>{t('indexing.contentType')}</Table.Th>
              <Table.Th style={{ width: '100px' }}>{t('indexing.pageRange')}</Table.Th>
              <Table.Th>{t('indexing.text')}</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {pageChunks.map((chunk: any, index: number) => (
              <Table.Tr key={chunk.node_id || index}>
                <Table.Td>
                  <Text size="xs" ff="monospace">
                    {String(chunk.node_id || index)}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Badge size="xs" variant="light">
                    {chunk.content_type || '-'}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Text size="xs">
                    {chunk.page_start !== undefined && chunk.page_end !== undefined
                      ? `${chunk.page_start}-${chunk.page_end}`
                      : chunk.page_no !== undefined
                      ? chunk.page_no
                      : '-'}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm" lineClamp={3}>
                    {chunk.text || '-'}
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
