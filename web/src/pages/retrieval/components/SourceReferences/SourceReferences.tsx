import { Accordion, ActionIcon, Badge, Group, Paper, Stack, Text, ThemeIcon } from '@mantine/core'
import { IconBookmark, IconExternalLink, IconFile } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import type { SourceReference } from '../../types'
import classes from './SourceReferences.module.css'

interface SourceReferencesProps {
  sources: SourceReference[]
}

export default function SourceReferences({ sources }: SourceReferencesProps) {
  const { t } = useTranslation()

  const getScoreColor = (score: number) => {
    if (score >= 0.9) return 'green'
    if (score >= 0.8) return 'teal'
    if (score >= 0.7) return 'yellow'
    return 'orange'
  }

  const viewSource = (sourceId: string) => {
    // TODO: Implement view source functionality
    console.log('View source:', sourceId)
  }

  return (
    <Accordion variant="contained">
      <Accordion.Item value="sources">
        <Accordion.Control>
          <Group gap="xs">
            <ThemeIcon size="sm" color="green" variant="light">
              <IconBookmark size={14} />
            </ThemeIcon>
            <Text size="sm" fw={600}>
              {sources.length} {t('retrieval.sourcesReferenced')}
            </Text>
          </Group>
        </Accordion.Control>

        <Accordion.Panel>
          <Stack gap="xs">
            {sources.map((source) => (
              <Paper
                key={source.id}
                p="sm"
                withBorder
                radius="md"
                className={classes.sourceCard ?? ''}
              >
                <Group justify="space-between" wrap="nowrap">
                  <Group gap="sm" className={classes.sourceMain ?? ''}>
                    <ThemeIcon color="green" variant="light" size="md">
                      <IconFile size={18} />
                    </ThemeIcon>

                    <div className={classes.sourceText}>
                      <Text size="sm" fw={600} lineClamp={1}>
                        {source.filename}
                      </Text>
                      <Group gap={8} mt={2}>
                        {source.pageRange && (
                          <Badge size="xs" variant="light" color="gray">
                            {source.pageRange}
                          </Badge>
                        )}
                        <Badge
                          size="xs"
                          variant="light"
                          color={getScoreColor(source.relevanceScore)}
                        >
                          {(source.relevanceScore * 100).toFixed(0)}%
                        </Badge>
                      </Group>
                    </div>
                  </Group>

                  <ActionIcon
                    variant="subtle"
                    size="sm"
                    aria-label="View source"
                    onClick={() => viewSource(source.id)}
                  >
                    <IconExternalLink size={16} />
                  </ActionIcon>
                </Group>

                {source.excerpt && (
                  <Text size="xs" c="dimmed" mt="sm" lineClamp={2}>
                    "{source.excerpt}"
                  </Text>
                )}
              </Paper>
            ))}
          </Stack>
        </Accordion.Panel>
      </Accordion.Item>
    </Accordion>
  )
}
