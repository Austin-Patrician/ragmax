import {
  Alert,
  Badge,
  Button,
  Code,
  FileInput,
  Group,
  Loader,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { FileUp, Play, ScanSearch } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  useIndexingArtifacts,
  useIndexingProfiles,
  usePreviewSourceIndexing,
  useRunSourceIndexing,
  useSourceParsers,
  useUploadSource,
} from '@/hooks/useIndexing'
import { DEFAULT_METADATA_JSON, DEFAULT_NOTEBOOK_ID } from '@/constants/app'
import { DataPanel } from '@/components/ui/DataPanel'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { formatApiError } from '@/utils/apiError'
import { buildIndexRequest } from '@/utils/indexing'
import classes from '@/components/ui/Page.module.css'

export function IndexingPage() {
  const { t } = useTranslation()
  const profiles = useIndexingProfiles()
  const parsers = useSourceParsers()
  const upload = useUploadSource()
  const preview = usePreviewSourceIndexing()
  const runIndex = useRunSourceIndexing()

  const [file, setFile] = useState<File | null>(null)
  const [notebookId, setNotebookId] = useState(DEFAULT_NOTEBOOK_ID)
  const [sourceId, setSourceId] = useState('')
  const [activeSourceId, setActiveSourceId] = useState('')
  const [metadata, setMetadata] = useState(DEFAULT_METADATA_JSON)
  const [profileName, setProfileName] = useState<string | null>(null)
  const [parserName, setParserName] = useState<string | null>(null)
  const [chunkSize, setChunkSize] = useState<string | number>('')
  const [chunkOverlap, setChunkOverlap] = useState<string | number>('')
  const [jobId, setJobId] = useState<string | null>(null)

  const artifacts = useIndexingArtifacts(jobId)
  const profileOptions = (profiles.data ?? []).map((profile) => ({
    value: profile.name,
    label: profile.name,
  }))
  const parserOptions = (parsers.data ?? []).map((parser) => ({
    value: parser.name,
    label: parser.is_default ? `${parser.name} (${t('common.default')})` : parser.name,
  }))
  const selectedSourceId = activeSourceId || sourceId
  const request = buildIndexRequest(profileName, parserName, chunkSize, chunkOverlap)
  const pageTitleClass = classes.pageTitle ?? ''

  async function handleUpload() {
    if (!file) {
      return
    }

    try {
      const trimmedSourceId = sourceId.trim()
      const trimmedMetadata = metadata.trim()
      const source = await upload.mutateAsync({
        file,
        notebookId,
        ...(trimmedSourceId ? { sourceId: trimmedSourceId } : {}),
        ...(trimmedMetadata ? { metadata: trimmedMetadata } : {}),
      })
      setActiveSourceId(source.source_id)
      notifications.show({
        color: 'green',
        title: t('indexing.sourceUploadedTitle'),
        message: source.source_id,
      })
    } catch (error) {
      notifications.show({
        color: 'red',
        title: t('indexing.uploadFailedTitle'),
        message: formatApiError(error),
      })
    }
  }

  async function handlePreview() {
    if (!selectedSourceId) {
      return
    }

    try {
      await preview.mutateAsync({ sourceId: selectedSourceId, request })
    } catch (error) {
      notifications.show({
        color: 'red',
        title: t('indexing.previewFailedTitle'),
        message: formatApiError(error),
      })
    }
  }

  async function handleRunIndex() {
    if (!selectedSourceId) {
      return
    }

    try {
      const result = await runIndex.mutateAsync({ sourceId: selectedSourceId, request })
      setJobId(result.job.job_id)
      notifications.show({
        color: 'green',
        title: t('indexing.indexFinishedTitle'),
        message: `${result.node_count} ${t('common.nodes')}`,
      })
    } catch (error) {
      notifications.show({
        color: 'red',
        title: t('indexing.indexFailedTitle'),
        message: formatApiError(error),
      })
    }
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="end" gap="md">
        <div>
          <Text size="sm" c="dimmed" fw={600}>
            {t('indexing.eyebrow')}
          </Text>
          <Title order={1} className={pageTitleClass}>
            {t('indexing.title')}
          </Title>
        </div>
        <Badge variant="outline" color="green" size="lg">
          {selectedSourceId || t('common.noSource')}
        </Badge>
      </Group>

      <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="lg">
        <DataPanel title={t('indexing.uploadTitle')} description={t('indexing.uploadDescription')}>
          <Stack>
            <FileInput
              label={t('indexing.file')}
              placeholder={t('indexing.filePlaceholder')}
              value={file}
              onChange={setFile}
              leftSection={<FileUp size={16} />}
            />
            <SimpleGrid cols={{ base: 1, sm: 2 }}>
              <TextInput
                label={t('indexing.notebook')}
                value={notebookId}
                onChange={(event) => setNotebookId(event.currentTarget.value)}
              />
              <TextInput
                label={t('indexing.sourceId')}
                placeholder={t('indexing.optional')}
                value={sourceId}
                onChange={(event) => setSourceId(event.currentTarget.value)}
              />
            </SimpleGrid>
            <Textarea
              label={t('indexing.metadataJson')}
              minRows={4}
              value={metadata}
              onChange={(event) => setMetadata(event.currentTarget.value)}
            />
            <Button
              leftSection={<FileUp size={16} />}
              onClick={handleUpload}
              disabled={!file || !notebookId}
              loading={upload.isPending}
            >
              {t('indexing.upload')}
            </Button>
          </Stack>
        </DataPanel>

        <DataPanel
          title={t('indexing.runOptionsTitle')}
          description={t('indexing.runOptionsDescription')}
        >
          <Stack>
            <SimpleGrid cols={{ base: 1, sm: 2 }}>
              <Select
                label={t('indexing.profile')}
                placeholder={t('indexing.auto')}
                data={profileOptions}
                value={profileName}
                onChange={setProfileName}
                clearable
              />
              <Select
                label={t('indexing.parser')}
                placeholder={t('common.default')}
                data={parserOptions}
                value={parserName}
                onChange={setParserName}
                clearable
              />
            </SimpleGrid>
            <SimpleGrid cols={{ base: 1, sm: 2 }}>
              <NumberInput
                label={t('indexing.chunkSize')}
                min={1}
                value={chunkSize}
                onChange={setChunkSize}
              />
              <NumberInput
                label={t('indexing.chunkOverlap')}
                min={0}
                value={chunkOverlap}
                onChange={setChunkOverlap}
              />
            </SimpleGrid>
            <Group grow>
              <Button
                variant="light"
                leftSection={<ScanSearch size={16} />}
                onClick={handlePreview}
                disabled={!selectedSourceId}
                loading={preview.isPending}
              >
                {t('indexing.preview')}
              </Button>
              <Button
                leftSection={<Play size={16} />}
                onClick={handleRunIndex}
                disabled={!selectedSourceId}
                loading={runIndex.isPending}
              >
                {t('indexing.runIndex')}
              </Button>
            </Group>
          </Stack>
        </DataPanel>
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, xl: 2 }} spacing="lg">
        <DataPanel
          title={t('indexing.profilesTitle')}
          description={t('indexing.profilesDescription')}
        >
          {profiles.isLoading ? (
            <Loader size="sm" />
          ) : profiles.isError ? (
            <Alert color="red">{formatApiError(profiles.error)}</Alert>
          ) : (
            <Table striped highlightOnHover withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{t('indexing.name')}</Table.Th>
                  <Table.Th>{t('indexing.chunker')}</Table.Th>
                  <Table.Th>{t('indexing.size')}</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {(profiles.data ?? []).map((profile) => (
                  <Table.Tr key={profile.name}>
                    <Table.Td>
                      <Text fw={650}>{profile.name}</Text>
                      <Text size="xs" c="dimmed">
                        {profile.node_graph_mode}
                      </Text>
                    </Table.Td>
                    <Table.Td>{profile.chunker}</Table.Td>
                    <Table.Td>
                      {profile.chunk_size}/{profile.chunk_overlap}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </DataPanel>

        <DataPanel title={t('indexing.parsersTitle')} description={t('indexing.parsersDescription')}>
          {parsers.isLoading ? (
            <Loader size="sm" />
          ) : parsers.isError ? (
            <Alert color="red">{formatApiError(parsers.error)}</Alert>
          ) : (
            <Table striped highlightOnHover withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{t('indexing.name')}</Table.Th>
                  <Table.Th>{t('indexing.key')}</Table.Th>
                  <Table.Th>{t('common.default')}</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {(parsers.data ?? []).map((parser) => (
                  <Table.Tr key={parser.name}>
                    <Table.Td>
                      <Text fw={650}>{parser.name}</Text>
                      <Text size="xs" c="dimmed" lineClamp={1}>
                        {parser.description}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      {parser.requires_api_key ? t('common.required') : t('common.local')}
                    </Table.Td>
                    <Table.Td>{parser.is_default ? t('common.yes') : t('common.no')}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </DataPanel>
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, xl: 2 }} spacing="lg">
        <DataPanel
          title={t('indexing.previewResultTitle')}
          description={t('indexing.previewResultDescription')}
        >
          {preview.data ? (
            <Stack gap="sm">
              <Group>
                <Badge color="green">{preview.data.effective_profile.name}</Badge>
                <Badge color="gray">{preview.data.effective_parser}</Badge>
              </Group>
              <SimpleGrid cols={3}>
                <Metric label={t('common.blocks')} value={preview.data.summary.block_count} />
                <Metric label={t('common.nodes')} value={preview.data.summary.node_count} />
                <Metric label={t('common.pages')} value={preview.data.summary.page_count} />
              </SimpleGrid>
              <Code block>{JSON.stringify(preview.data.analysis, null, 2)}</Code>
            </Stack>
          ) : (
            <Text c="dimmed">{t('indexing.noPreview')}</Text>
          )}
        </DataPanel>

        <DataPanel title={t('indexing.indexJobTitle')} description={t('indexing.indexJobDescription')}>
          {runIndex.data ? (
            <Stack gap="sm">
              <Group>
                <StatusBadge value={runIndex.data.job.status} />
                <StatusBadge value={runIndex.data.job.vector_status} />
              </Group>
              <Text size="sm">
                <Text span fw={650}>
                  {t('indexing.job')}
                </Text>{' '}
                {runIndex.data.job.job_id}
              </Text>
              <SimpleGrid cols={3}>
                <Metric label={t('common.nodes')} value={runIndex.data.node_count} />
                <Metric label={t('common.blocks')} value={runIndex.data.summary.block_count} />
                <Metric label={t('common.vectors')} value={runIndex.data.summary.vectorized_count} />
              </SimpleGrid>
              {artifacts.isFetching ? <Loader size="sm" /> : null}
              {artifacts.data ? (
                <Text size="sm" c="dimmed">
                  {t('common.artifacts')}: {artifacts.data.blocks.length} {t('common.blocks')},{' '}
                  {artifacts.data.nodes.length} {t('common.nodes')}
                </Text>
              ) : null}
            </Stack>
          ) : (
            <Text c="dimmed">{t('indexing.noIndexJob')}</Text>
          )}
        </DataPanel>
      </SimpleGrid>
    </Stack>
  )
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className={classes.metric ?? ''}>
      <Text size="xs" c="dimmed" fw={700}>
        {label}
      </Text>
      <Text size="xl" fw={750}>
        {value}
      </Text>
    </div>
  )
}
