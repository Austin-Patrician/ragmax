import { Badge, Box, Group, Paper, Stack, Text, TextInput, Loader, Center } from '@mantine/core'
import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Layers, Search, Database, Quote } from 'lucide-react'
import type { ArtifactData } from '@/types'

type VectorStatsViewerProps = {
  data: ArtifactData
}

const PAGE_SIZE = 50

export function VectorStatsViewer({ data }: VectorStatsViewerProps) {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)
  const sentinelRef = useRef<HTMLDivElement>(null)

  // Smartly extract the array of nodes from whatever structure the backend sends
  let nodes: any[] = []
  if (Array.isArray(data.data)) {
    const first = data.data[0] as any
    if (data.data.length === 1 && first && Array.isArray(first.vectorized_node_ids)) {
      nodes = first.vectorized_node_ids.map((id: string) => ({
        node_id: id,
        text: `Successfully vectorized and stored in collection: ${first.collection || 'unknown'}`,
        vector: [],
        content_type: 'vector_id'
      }))
    } else if (data.data.length === 1 && first && Array.isArray(first.nodes)) {
      nodes = first.nodes
    } else {
      nodes = data.data
    }
  } else if (data.data && typeof data.data === 'object') {
    if (Array.isArray((data.data as any).vectorized_node_ids)) {
      // Backend only sent node IDs, map them into objects for the viewer
      nodes = (data.data as any).vectorized_node_ids.map((id: string) => ({
        node_id: id,
        text: `Successfully vectorized and stored in collection: ${(data.data as any).collection || 'unknown'}`,
        vector: [], // Mock to trigger isVectorized UI
        content_type: 'vector_id'
      }))
    } else if (Array.isArray((data.data as any).nodes)) {
      nodes = (data.data as any).nodes
    } else if (Array.isArray((data.data as any).data)) {
      nodes = (data.data as any).data
    }
  }
  // Filtering logic
  const filteredNodes = nodes.filter((node: any) => {
    if (!searchQuery) return true
    const textContent = node.text || node.content || JSON.stringify(node)
    return textContent.toLowerCase().includes(searchQuery.toLowerCase())
  })

  const visibleNodes = filteredNodes.slice(0, visibleCount)

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
        {t('indexing.noResults', 'No vectorization data available')}
      </Text>
    )
  }

  // Attempt to find dimension from the first valid embedding
  const sampleNode = nodes.find((n: any) => Array.isArray(n.embedding) || Array.isArray(n.vector))
  const dimension = sampleNode ? (sampleNode.embedding?.length || sampleNode.vector?.length) : null

  return (
    <Stack gap="md">
      {/* Compact Top Stats */}
      <Group justify="space-between" align="center" px="xs">
        <Text size="sm" fw={700} style={{ color: '#1e293b' }}>
          {t('indexing.vectorResults', 'Vectorized Results')}
        </Text>
        <Group gap="xs">
          <Badge variant="light" color="indigo" size="sm" leftSection={<Layers size={10} />}>
            {nodes.length} {t('indexing.totalVectors', 'Vectors')}
          </Badge>
          {dimension && (
            <Badge variant="light" color="teal" size="sm" leftSection={<Database size={10} />}>
              {dimension} {t('indexing.dimensions', 'Dimensions')}
            </Badge>
          )}
        </Group>
      </Group>

      {/* Search Bar */}
      <TextInput
        placeholder={t('indexing.searchVectors', 'Search vectorized text...')}
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
          {t('indexing.noSearchResults', 'No vectors match your search query.')}
        </Text>
      )}

      {/* Vector Cards List */}
      <Stack gap="sm">
        {visibleNodes.map((node: any, index: number) => (
          <VectorCard key={node.node_id || index} node={node} index={index + 1} />
        ))}
      </Stack>
      
      {/* Infinite Scroll Sentinel */}
      {visibleCount < filteredNodes.length && (
        <Center ref={sentinelRef} py="xl">
          <Loader size="sm" color="gray" type="dots" />
        </Center>
      )}
    </Stack>
  )
}

function VectorCard({ node, index }: { node: any; index: number }) {
  const textContent = node.text || node.content || '-'
  const type = node.content_type || 'vector'
  const isVectorized = Array.isArray(node.embedding) || Array.isArray(node.vector)

  return (
    <Box style={{ position: 'relative' }}>
      <Paper radius="md" p="md" style={{ border: '1px solid #e2e8f0', background: '#ffffff', boxShadow: '0 2px 6px rgba(0,0,0,0.02)', borderLeft: isVectorized ? '3px solid #10b981' : '3px solid #cbd5e1' }}>
        <Group justify="space-between" mb="xs">
          <Group gap="xs">
            <Badge variant="filled" color={isVectorized ? "teal" : "gray"} size="xs" radius="sm">
              #{index}
            </Badge>
            <Badge variant="light" color="gray" size="xs" style={{ textTransform: 'uppercase' }}>
              {type}
            </Badge>
            {isVectorized && (
              <Badge variant="dot" color="teal" size="xs">
                {t('indexing.embedded', 'Embedded')}
              </Badge>
            )}
          </Group>
          <Text size="xs" fw={600} style={{ color: '#cbd5e1', fontFamily: 'monospace' }}>
            {node.node_id || 'Unknown'}
          </Text>
        </Group>

        <Box style={{ position: 'relative', paddingLeft: '12px' }}>
          <Quote size={16} color="#e2e8f0" style={{ position: 'absolute', left: '-4px', top: '0px' }} />
          <Text size="sm" style={{ color: '#475569', whiteSpace: 'pre-wrap', lineHeight: 1.6, zIndex: 1, position: 'relative' }}>
            {textContent}
          </Text>
        </Box>
      </Paper>
    </Box>
  )
}
// simple fallback for t inside VectorCard
const t = (_key: string, fallback: string) => fallback
