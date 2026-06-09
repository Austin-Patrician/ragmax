import { Badge, Button, Group, Paper, Stack, Table, Text, ScrollArea } from '@mantine/core'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { ArtifactData } from '@/types'
import classes from './TableViewer.module.css'

type BlocksTableViewerProps = {
  data: ArtifactData
}

const PAGE_SIZE = 50

export function BlocksTableViewer({ data }: BlocksTableViewerProps) {
  const { t } = useTranslation()
  const [page, setPage] = useState(0)

  const blocks = Array.isArray(data.data) ? data.data : []
  const totalPages = Math.ceil(blocks.length / PAGE_SIZE)
  const startIndex = page * PAGE_SIZE
  const endIndex = Math.min(startIndex + PAGE_SIZE, blocks.length)
  const pageBlocks = blocks.slice(startIndex, endIndex)

  if (blocks.length === 0) {
    return (
      <Text c="dimmed" size="sm">
        {t('indexing.noResults')}
      </Text>
    )
  }

  return (
    <Stack gap="md">
      <Paper withBorder p="sm" radius="md" className={classes.paginationBar || ''}>
        <Group justify="space-between">
          <div>
            <Text size="sm" fw={700}>
              {t('indexing.blocksTable')}
            </Text>
            <Text size="xs" c="dimmed" mt={2}>
              {blocks.length} {t('common.blocks')} total
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
              <Table.Th style={{ width: '100px' }}>{t('indexing.blockId')}</Table.Th>
              <Table.Th style={{ width: '120px' }}>{t('indexing.blockType')}</Table.Th>
              <Table.Th style={{ width: '80px' }}>{t('indexing.pageNo')}</Table.Th>
              <Table.Th>{t('indexing.text')}</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {pageBlocks.map((block: any, index: number) => (
              <Table.Tr key={block.block_id || index}>
                <Table.Td>
                  <Text size="xs" ff="monospace">
                    {String(block.block_id || index)}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Badge size="xs" variant="light">
                    {block.block_type || '-'}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Text size="xs">{block.page_no !== undefined ? block.page_no : '-'}</Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm" lineClamp={3}>
                    {block.text || '-'}
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
