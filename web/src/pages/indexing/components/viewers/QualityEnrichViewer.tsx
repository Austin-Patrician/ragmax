import { Badge, Group, Progress, Stack, Table, Text, TextInput, Loader, Center } from '@mantine/core'
import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Layers, Search, Activity, AlertTriangle } from 'lucide-react'
import type { ArtifactData } from '@/types'

type QualityEnrichViewerProps = {
  data: ArtifactData
}

const PAGE_SIZE = 50

export function QualityEnrichViewer({ data }: QualityEnrichViewerProps) {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)
  const sentinelRef = useRef<HTMLDivElement>(null)

  const nodes = Array.isArray(data.data) ? data.data : []
  
  // Filtering logic
  const filteredNodes = nodes.filter((node: any) => {
    if (!searchQuery) return true
    const textContent = node.text || node.enriched_text || JSON.stringify(node)
    return textContent.toLowerCase().includes(searchQuery.toLowerCase())
  })

  const visibleNodes = filteredNodes.slice(0, visibleCount)

  // Calculate stats
  const nodesWithQuality = nodes.filter((n: any) => n.quality_score !== undefined)
  const avgQuality = nodesWithQuality.length > 0
    ? (nodesWithQuality.reduce((sum: number, n: any) => sum + (n.quality_score || 0), 0) / nodesWithQuality.length * 100).toFixed(0)
    : 0
  const totalWarnings = nodes.reduce((sum: number, n: any) => sum + (n.warnings?.length || 0), 0)

  // Scroll-based infinite load
  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel || visibleCount >= filteredNodes.length) return

    let scrollParent: HTMLElement | null = sentinel.parentElement
    while (scrollParent) {
      if (scrollParent.scrollHeight > scrollParent.clientHeight) break
      scrollParent = scrollParent.parentElement
    }
    if (!scrollParent) return

    const onScroll = () => {
      const el = sentinelRef.current
      if (!el || !scrollParent) return
      const containerRect = scrollParent.getBoundingClientRect()
      const sentinelRect = el.getBoundingClientRect()
      
      if (sentinelRect.top < containerRect.bottom + 200) {
        setVisibleCount((v) => Math.min(v + PAGE_SIZE, filteredNodes.length))
      }
    }

    onScroll()
    scrollParent.addEventListener('scroll', onScroll, { passive: true })
    return () => scrollParent!.removeEventListener('scroll', onScroll)
  }, [filteredNodes.length, visibleCount])

  // Reset pagination on search change
  useEffect(() => {
    setVisibleCount(PAGE_SIZE)
  }, [searchQuery])

  if (nodes.length === 0) {
    return (
      <Text c="dimmed" size="sm" ta="center" mt="xl">
        {t('indexing.noResults', 'No quality data available')}
      </Text>
    )
  }

  return (
    <Stack gap="md">
      {/* Compact Top Stats */}
      <Group justify="space-between" align="center" px="xs">
        <Text size="sm" fw={700} style={{ color: '#1e293b' }}>
          {t('indexing.qualityEnrich', 'Quality Enrichment')}
        </Text>
        <Group gap="xs">
          <Badge variant="light" color="indigo" size="sm" leftSection={<Layers size={10} />}>
            {nodes.length} {t('common.nodes', 'Nodes')}
          </Badge>
          <Badge variant="light" color="teal" size="sm" leftSection={<Activity size={10} />}>
            {avgQuality}% {t('indexing.avgQuality', 'Avg Quality')}
          </Badge>
          {totalWarnings > 0 && (
            <Badge variant="light" color="orange" size="sm" leftSection={<AlertTriangle size={10} />}>
              {totalWarnings} {t('indexing.warningCount', 'Warnings')}
            </Badge>
          )}
        </Group>
      </Group>

      {/* Search Bar */}
      <TextInput
        placeholder={t('indexing.searchNodes', 'Search enriched nodes...')}
        leftSection={<Search size={16} color="#94a3b8" />}
        value={searchQuery}
        onChange={(event) => setSearchQuery(event.currentTarget.value)}
        radius="md"
        size="md"
        style={{ border: '1px solid #e2e8f0', borderRadius: '8px', background: '#f8fafc' }}
        styles={{ input: { border: 'none', background: 'transparent' } }}
      />

      {filteredNodes.length === 0 && (
        <Text c="dimmed" size="sm" ta="center" mt="xl">
          {t('indexing.noSearchResults', 'No nodes match your search query.')}
        </Text>
      )}

      {/* Table Display */}
      {filteredNodes.length > 0 && (
        <Table striped highlightOnHover withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th style={{ width: '100px' }}>{t('indexing.nodeId', 'Node ID')}</Table.Th>
              <Table.Th style={{ width: '120px' }}>{t('indexing.qualityScore', 'Quality')}</Table.Th>
              <Table.Th style={{ width: '150px' }}>{t('indexing.warnings', 'Warnings')}</Table.Th>
              <Table.Th>{t('indexing.text', 'Text')}</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {visibleNodes.map((node: any, index: number) => (
              <Table.Tr key={node.node_id || index}>
                <Table.Td>
                  <Text size="xs" ff="monospace" c="dimmed">
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
                    <Text size="xs" c="dimmed">-</Text>
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
                    <Text size="xs" c="dimmed">-</Text>
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
      )}

      {/* Infinite Scroll Sentinel */}
      {visibleCount < filteredNodes.length && (
        <Center ref={sentinelRef} py="xl">
          <Loader size="sm" color="gray" type="dots" />
        </Center>
      )}
    </Stack>
  )
}

function getQualityColor(score: number): string {
  if (score >= 0.8) return 'green'
  if (score >= 0.6) return 'yellow'
  return 'red'
}
