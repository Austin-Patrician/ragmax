import {
  Alert,
  Badge,
  Button,
  Code,
  Group,
  MultiSelect,
  NumberInput,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { Bot, Search } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useRetrievalAnswer, useRetrievalSearch } from '@/hooks/useRetrieval'
import { DEFAULT_NOTEBOOK_ID, DEFAULT_QUERY, DEFAULT_TOP_K } from '@/constants/app'
import { RETRIEVAL_CONTENT_TYPES } from '@/constants/retrieval'
import { DataPanel } from '@/components/ui/DataPanel'
import type { RetrievalAnswerRequest, RetrievalSearchRequest } from '@/types'
import { formatApiError } from '@/utils/apiError'
import { splitCommaSeparated } from '@/utils/text'
import classes from '@/components/ui/Page.module.css'

export function RetrievalPage() {
  const { t } = useTranslation()
  const search = useRetrievalSearch()
  const answer = useRetrievalAnswer()
  const [query, setQuery] = useState(DEFAULT_QUERY)
  const [notebookId, setNotebookId] = useState(DEFAULT_NOTEBOOK_ID)
  const [topK, setTopK] = useState<string | number>(DEFAULT_TOP_K)
  const [sourceIds, setSourceIds] = useState('')
  const [contentTypes, setContentTypes] = useState<string[]>([])
  const pageTitleClass = classes.pageTitle ?? ''
  const contentTypeOptions = RETRIEVAL_CONTENT_TYPES.map((value) => ({
    value,
    label: value,
  }))

  const normalizedSourceIds = splitCommaSeparated(sourceIds)

  function buildSearchRequest(): RetrievalSearchRequest {
    return {
      query,
      notebook_id: notebookId,
      top_k: typeof topK === 'number' ? topK : DEFAULT_TOP_K,
      source_ids: normalizedSourceIds,
      content_types: contentTypes,
    }
  }

  function buildAnswerRequest(): RetrievalAnswerRequest {
    return {
      query,
      notebook_id: notebookId,
      retrieval_top_k: typeof topK === 'number' ? topK : DEFAULT_TOP_K,
      source_ids: normalizedSourceIds,
      content_types: contentTypes,
    }
  }

  async function handleSearch() {
    try {
      await search.mutateAsync(buildSearchRequest())
    } catch (error) {
      notifications.show({
        color: 'red',
        title: t('retrieval.searchFailedTitle'),
        message: formatApiError(error),
      })
    }
  }

  async function handleAnswer() {
    try {
      await answer.mutateAsync(buildAnswerRequest())
    } catch (error) {
      notifications.show({
        color: 'red',
        title: t('retrieval.answerFailedTitle'),
        message: formatApiError(error),
      })
    }
  }

  return (
    <Stack gap="lg">
      <div>
        <Text size="sm" c="dimmed" fw={600}>
          {t('retrieval.eyebrow')}
        </Text>
        <Title order={1} className={pageTitleClass}>
          {t('retrieval.title')}
        </Title>
      </div>

      <DataPanel title={t('retrieval.queryTitle')} description={t('retrieval.queryDescription')}>
        <Stack>
          <Textarea
            label={t('retrieval.question')}
            minRows={4}
            value={query}
            onChange={(event) => setQuery(event.currentTarget.value)}
          />
          <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
            <TextInput
              label={t('retrieval.notebook')}
              value={notebookId}
              onChange={(event) => setNotebookId(event.currentTarget.value)}
            />
            <NumberInput label={t('retrieval.topK')} min={1} max={50} value={topK} onChange={setTopK} />
            <TextInput
              label={t('retrieval.sourceIds')}
              placeholder={t('retrieval.sourceIdsPlaceholder')}
              value={sourceIds}
              onChange={(event) => setSourceIds(event.currentTarget.value)}
            />
            <MultiSelect
              label={t('retrieval.contentTypes')}
              data={contentTypeOptions}
              value={contentTypes}
              onChange={setContentTypes}
              clearable
            />
          </SimpleGrid>
          <Group>
            <Button
              leftSection={<Search size={16} />}
              onClick={handleSearch}
              disabled={!query || !notebookId}
              loading={search.isPending}
            >
              {t('retrieval.search')}
            </Button>
            <Button
              variant="light"
              leftSection={<Bot size={16} />}
              onClick={handleAnswer}
              disabled={!query || !notebookId}
              loading={answer.isPending}
            >
              {t('retrieval.answer')}
            </Button>
          </Group>
        </Stack>
      </DataPanel>

      <SimpleGrid cols={{ base: 1, xl: 2 }} spacing="lg">
        <DataPanel
          title={t('retrieval.searchResultsTitle')}
          description={t('retrieval.searchResultsDescription')}
        >
          {search.isError ? <Alert color="red">{formatApiError(search.error)}</Alert> : null}
          {search.data ? (
            <Stack gap="sm">
              <Group>
                <Badge color="green">
                  {search.data.count} {t('common.results')}
                </Badge>
                <Badge color="gray">{search.data.notebook_id}</Badge>
              </Group>
              {search.data.results.map((result) => (
                <div className={classes.result ?? ''} key={result.node_id}>
                  <Group justify="space-between" gap="xs">
                    <Text fw={700}>{result.content_type}</Text>
                    <Badge variant="light">{result.score.toFixed(3)}</Badge>
                  </Group>
                  <Text size="sm" c="dimmed" lineClamp={3}>
                    {result.text}
                  </Text>
                </div>
              ))}
            </Stack>
          ) : (
            <Text c="dimmed">{t('retrieval.noSearchResults')}</Text>
          )}
        </DataPanel>

        <DataPanel title={t('retrieval.answerTitle')} description={t('retrieval.answerDescription')}>
          {answer.isError ? <Alert color="red">{formatApiError(answer.error)}</Alert> : null}
          {answer.data ? (
            <Stack gap="sm">
              <Text>{answer.data.answer}</Text>
              <Group>
                <Badge color="green">
                  {answer.data.rerank_count} {t('common.contexts')}
                </Badge>
                <Badge color="gray">{answer.data.answer_generator}</Badge>
              </Group>
              <Code block>{JSON.stringify(answer.data.citations, null, 2)}</Code>
            </Stack>
          ) : (
            <Text c="dimmed">{t('retrieval.noAnswer')}</Text>
          )}
        </DataPanel>
      </SimpleGrid>
    </Stack>
  )
}
