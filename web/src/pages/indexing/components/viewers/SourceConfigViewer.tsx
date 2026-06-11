import { Paper, SimpleGrid, Stack, Text, Group, ThemeIcon, Badge, Divider } from '@mantine/core'
import { FileCode2, Settings, FileJson, BoxSelect } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { ArtifactData } from '@/types'

type SourceConfigViewerProps = {
  data: ArtifactData
}

export function SourceConfigViewer({ data }: SourceConfigViewerProps) {
  const { t } = useTranslation()
  const sourceData = Array.isArray(data.data) ? data.data[0] : data.data

  if (!sourceData || typeof sourceData !== 'object') {
    return (
      <Text c="dimmed" size="sm" ta="center" mt="xl">
        {t('indexing.noData', 'No configuration data available')}
      </Text>
    )
  }

  const metadata = (sourceData as any).metadata || {}
  const config = (sourceData as any).config || {}

  return (
    <Stack gap="xl">
      <SectionCard 
        title={t('indexing.sourceConfig', 'Core Configuration')} 
        icon={<FileCode2 size={18} />}
        color="blue"
      >
        <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="lg">
          <PropertyBox label={t('indexing.effectiveProfile', 'Effective Profile')} value={(sourceData as any).effective_profile} />
          <PropertyBox label={t('indexing.effectiveParser', 'Effective Parser')} value={(sourceData as any).effective_parser} />
          <PropertyBox label="Source ID" value={(sourceData as any).source_id} isCode />
          <PropertyBox label="Notebook ID" value={(sourceData as any).notebook_id} isCode />
        </SimpleGrid>
      </SectionCard>

      {Object.keys(config).length > 0 && (
        <SectionCard 
          title={t('indexing.runConfig', 'Run Parameters')} 
          icon={<Settings size={18} />}
          color="teal"
        >
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md">
            {Object.entries(config).map(([key, val]) => (
              <PropertyBox key={key} label={key} value={val} />
            ))}
          </SimpleGrid>
        </SectionCard>
      )}

      {Object.keys(metadata).length > 0 && (
        <SectionCard 
          title={t('indexing.metadata', 'File Metadata')} 
          icon={<FileJson size={18} />}
          color="grape"
        >
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md">
            {Object.entries(metadata).map(([key, val]) => (
              <PropertyBox key={key} label={key} value={val} />
            ))}
          </SimpleGrid>
        </SectionCard>
      )}
    </Stack>
  )
}

function SectionCard({ title, icon, color, children }: { title: string; icon: React.ReactNode; color: string; children: React.ReactNode }) {
  return (
    <Paper radius="xl" p="xl" style={{ border: '1px solid #e2e8f0', background: '#ffffff', boxShadow: '0 4px 20px rgba(0,0,0,0.02)' }}>
      <Group gap="sm" mb="lg">
        <ThemeIcon size={36} radius="md" variant="light" color={color}>
          {icon}
        </ThemeIcon>
        <Text fw={700} size="lg" style={{ color: '#1e293b' }}>
          {title}
        </Text>
      </Group>
      {children}
    </Paper>
  )
}

function PropertyBox({ label, value, isCode }: { label: string; value: any; isCode?: boolean }) {
  const displayValue = value === null || value === undefined ? '-' : typeof value === 'object' ? JSON.stringify(value) : String(value)
  
  return (
    <div style={{ background: '#f8fafc', padding: '12px 16px', borderRadius: '12px', border: '1px solid #f1f5f9' }}>
      <Text size="xs" fw={600} tt="uppercase" style={{ color: '#94a3b8', letterSpacing: '0.05em' }} mb={4}>
        {label.replace(/_/g, ' ')}
      </Text>
      {isCode ? (
        <Badge variant="light" color="gray" size="sm" style={{ textTransform: 'none', fontFamily: 'monospace' }}>
          {displayValue}
        </Badge>
      ) : (
        <Text size="sm" fw={600} style={{ color: '#334155', wordBreak: 'break-word' }}>
          {displayValue}
        </Text>
      )}
    </div>
  )
}
