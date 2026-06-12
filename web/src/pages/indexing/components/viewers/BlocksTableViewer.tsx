import { Badge, Box, Group, Paper, Stack, Text, ThemeIcon, TextInput, Loader, Center } from '@mantine/core'
import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Type, AlignLeft, Table as TableIcon, Search, Hash } from 'lucide-react'
import type { ArtifactData } from '@/types'

type BlocksTableViewerProps = {
  data: ArtifactData
}

const PAGE_SIZE = 50

export function BlocksTableViewer({ data }: BlocksTableViewerProps) {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)
  const sentinelRef = useRef<HTMLDivElement>(null)

  const blocks = Array.isArray(data.data) ? data.data : []

  // Handle Search Filtering
  const filteredBlocks = blocks.filter((block: any) => {
    if (!searchQuery) return true
    const textContent = block.text || block.content || JSON.stringify(block)
    return textContent.toLowerCase().includes(searchQuery.toLowerCase())
  })

  const visibleBlocks = filteredBlocks.slice(0, visibleCount)

  // Scroll-based infinite load: listen to the nearest scrollable ancestor
  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel || visibleCount >= filteredBlocks.length) return

    // Walk up to find the real scrollable container (Mantine ScrollArea viewport)
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
      // If sentinel top is within 200px below the container bottom, load more
      if (sentinelRect.top < containerRect.bottom + 200) {
        setVisibleCount((v) => Math.min(v + PAGE_SIZE, filteredBlocks.length))
      }
    }

    // Check immediately in case sentinel is already visible
    onScroll()

    scrollParent.addEventListener('scroll', onScroll, { passive: true })
    return () => scrollParent!.removeEventListener('scroll', onScroll)
  }, [filteredBlocks.length, visibleCount])

  // Reset infinite scroll when search changes
  useEffect(() => {
    setVisibleCount(PAGE_SIZE)
  }, [searchQuery])

  if (blocks.length === 0) {
    return (
      <Text c="dimmed" size="sm" ta="center" mt="xl">
        {t('indexing.noResults', 'No blocks extracted')}
      </Text>
    )
  }

  return (
    <Stack gap="lg">
      <TextInput
        placeholder={t('indexing.searchBlocks', 'Search text in blocks...')}
        leftSection={<Search size={16} color="#94a3b8" />}
        value={searchQuery}
        onChange={(event) => setSearchQuery(event.currentTarget.value)}
        radius="md"
        size="md"
        style={{ border: '1px solid #e2e8f0', borderRadius: '8px', background: '#f8fafc' }}
        styles={{ input: { border: 'none', background: 'transparent' } }}
      />

      {filteredBlocks.length === 0 && (
        <Text c="dimmed" size="sm" ta="center" mt="xl">
          {t('indexing.noSearchResults', 'No blocks match your search query.')}
        </Text>
      )}

      <Stack gap="md">
        {visibleBlocks.map((block: any, index: number) => (
          <BlockCard key={block.id || index} block={block} index={index + 1} />
        ))}
      </Stack>

      {/* Infinite Scroll Sentinel */}
      {visibleCount < filteredBlocks.length && (
        <Center ref={sentinelRef} py="xl">
          <Loader size="sm" color="gray" type="dots" />
        </Center>
      )}
    </Stack>
  )
}

function BlockCard({ block, index }: { block: any; index: number }) {
  const type = block.type?.toLowerCase() || 'text'
  const textContent = block.text || block.content || JSON.stringify(block)
  
  let Icon = AlignLeft
  let color = 'blue'
  if (type.includes('title') || type.includes('heading')) {
    Icon = Type
    color = 'grape'
  } else if (type.includes('table')) {
    Icon = TableIcon
    color = 'orange'
  }

  return (
    <Paper radius="lg" p="md" style={{ border: '1px solid #e2e8f0', background: '#ffffff', boxShadow: '0 2px 8px rgba(0,0,0,0.02)' }}>
      <Group justify="space-between" align="flex-start" mb="sm">
        <Group gap="sm">
          <ThemeIcon size={28} radius="md" variant="light" color={color}>
            <Icon size={14} />
          </ThemeIcon>
          <Badge variant="dot" color={color} size="md" style={{ textTransform: 'capitalize' }}>
            {type}
          </Badge>
          <Text size="xs" fw={700} style={{ color: '#94a3b8' }}>
            #{index}
          </Text>
        </Group>
        <Badge variant="outline" color="gray" size="xs">
          {textContent.length} Chars
        </Badge>
      </Group>

      <Box style={{ background: '#f8fafc', padding: '16px', borderRadius: '12px', border: '1px solid #f1f5f9' }}>
        <Text size="sm" style={{ color: '#334155', whiteSpace: 'pre-wrap', lineHeight: 1.6, wordBreak: 'break-word' }}>
          {textContent}
        </Text>
      </Box>

      {block.metadata && Object.keys(block.metadata).length > 0 && (
        <Group gap="xs" mt="sm">
          <Hash size={12} color="#94a3b8" />
          <Text size="xs" fw={600} style={{ color: '#64748b' }}>
            Metadata:
          </Text>
          <Text size="xs" style={{ color: '#94a3b8' }}>
            {JSON.stringify(block.metadata)}
          </Text>
        </Group>
      )}
    </Paper>
  )
}
