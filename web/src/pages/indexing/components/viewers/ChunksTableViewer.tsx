import { Badge, Box, Group, Paper, Stack, Text, TextInput, Loader, Center } from '@mantine/core'
import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Layers, AlignLeft, Search, Quote } from 'lucide-react'
import type { ArtifactData } from '@/types'

type ChunksTableViewerProps = {
  data: ArtifactData
}

const PAGE_SIZE = 50

export function ChunksTableViewer({ data }: ChunksTableViewerProps) {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)
  const sentinelRef = useRef<HTMLDivElement>(null)

  const chunks = Array.isArray(data.data) ? data.data : []
  
  // Filtering logic
  const filteredChunks = chunks.filter((chunk: any) => {
    if (!searchQuery) return true
    const textContent = chunk.text || chunk.content || JSON.stringify(chunk)
    return textContent.toLowerCase().includes(searchQuery.toLowerCase())
  })

  const visibleChunks = filteredChunks.slice(0, visibleCount)

  const avgLength = chunks.length > 0
    ? Math.round(chunks.reduce((sum: number, c: any) => sum + (c.text?.length || 0), 0) / chunks.length)
    : 0

  // Scroll-based infinite load
  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel || visibleCount >= filteredChunks.length) return

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
        setVisibleCount((v) => Math.min(v + PAGE_SIZE, filteredChunks.length))
      }
    }

    onScroll()
    scrollParent.addEventListener('scroll', onScroll, { passive: true })
    return () => scrollParent!.removeEventListener('scroll', onScroll)
  }, [filteredChunks.length, visibleCount])

  // Reset pagination on search change
  useEffect(() => {
    setVisibleCount(PAGE_SIZE)
  }, [searchQuery])

  if (chunks.length === 0) {
    return (
      <Text c="dimmed" size="sm" ta="center" mt="xl">
        {t('indexing.noResults', 'No chunks available')}
      </Text>
    )
  }

  return (
    <Stack gap="md">
      <Group justify="space-between" align="center" px="xs">
        <Text size="sm" fw={700} style={{ color: '#1e293b' }}>
          {t('indexing.chunksTable', 'Extracted Chunks')}
        </Text>
        <Group gap="xs">
          <Badge variant="light" color="indigo" size="sm" leftSection={<Layers size={10} />}>
            {chunks.length} {t('indexing.totalChunks', 'Total')}
          </Badge>
          <Badge variant="light" color="teal" size="sm" leftSection={<AlignLeft size={10} />}>
            ~{avgLength} {t('common.chars', 'Chars/Chunk')}
          </Badge>
        </Group>
      </Group>

      <TextInput
        placeholder={t('indexing.searchChunks', 'Search text in chunks...')}
        leftSection={<Search size={16} color="#94a3b8" />}
        value={searchQuery}
        onChange={(event) => setSearchQuery(event.currentTarget.value)}
        radius="md"
        size="md"
        style={{ border: '1px solid #e2e8f0', borderRadius: '8px', background: '#f8fafc' }}
        styles={{ input: { border: 'none', background: 'transparent' } }}
      />

      {filteredChunks.length === 0 && (
        <Text c="dimmed" size="sm" ta="center" mt="xl">
          {t('indexing.noSearchResults', 'No chunks match your search query.')}
        </Text>
      )}

      <Stack gap="sm">
        {visibleChunks.map((chunk: any, index: number) => (
          <ChunkQuoteCard key={chunk.node_id || index} chunk={chunk} index={index + 1} />
        ))}
      </Stack>
      
      {/* Infinite Scroll Sentinel */}
      {visibleCount < filteredChunks.length && (
        <Center ref={sentinelRef} py="xl">
          <Loader size="sm" color="gray" type="dots" />
        </Center>
      )}
    </Stack>
  )
}

function ChunkQuoteCard({ chunk, index }: { chunk: any; index: number }) {
  const textContent = chunk.text || '-'
  const type = chunk.content_type || 'text'
  const pageRange = chunk.page_start !== undefined && chunk.page_end !== undefined
    ? `Page ${chunk.page_start}-${chunk.page_end}`
    : chunk.page_no !== undefined
    ? `Page ${chunk.page_no}`
    : ''

  return (
    <Box style={{ position: 'relative' }}>
      <Paper radius="md" p="md" style={{ border: '1px solid #e2e8f0', background: '#ffffff', boxShadow: '0 2px 6px rgba(0,0,0,0.02)', borderLeft: '3px solid #4c8df8' }}>
        <Group justify="space-between" mb="xs">
          <Group gap="xs">
            <Badge variant="filled" color="blue" size="xs" radius="sm">
              #{index}
            </Badge>
            <Badge variant="light" color="gray" size="xs" style={{ textTransform: 'uppercase' }}>
              {type}
            </Badge>
            {pageRange && (
              <Text size="xs" fw={500} style={{ color: '#94a3b8' }}>
                • {pageRange}
              </Text>
            )}
          </Group>
          <Text size="xs" fw={600} style={{ color: '#cbd5e1', fontFamily: 'monospace' }}>
            {chunk.node_id || 'Unknown'}
          </Text>
        </Group>

        <Box style={{ position: 'relative', paddingLeft: '12px' }}>
          <Quote size={16} color="#e2e8f0" style={{ position: 'absolute', left: '-4px', top: '0px' }} />
          <Text size="sm" style={{ color: '#475569', whiteSpace: 'pre-wrap', lineHeight: 1.6, zIndex: 1, position: 'relative' }}>
            {textContent}
          </Text>
        </Box>
        
        <Group justify="flex-end" mt="xs">
          <Text size="xs" fw={500} style={{ color: '#cbd5e1' }}>
            {textContent.length} chars
          </Text>
        </Group>
      </Paper>
    </Box>
  )
}
