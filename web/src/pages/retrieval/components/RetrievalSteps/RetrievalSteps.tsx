import { Accordion, Badge, Group, Text, ThemeIcon, Timeline } from '@mantine/core'
import {
  IconBrain,
  IconBug,
  IconDatabase,
  IconFileText,
  IconSearch,
  IconSortDescending,
} from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import type { RetrievalStep } from '../../types'
import classes from './RetrievalSteps.module.css'

interface RetrievalStepsProps {
  steps: RetrievalStep[]
}

export default function RetrievalSteps({ steps }: RetrievalStepsProps) {
  const { t } = useTranslation()

  const getStepIcon = (type: RetrievalStep['type']) => {
    switch (type) {
      case 'query_understanding':
        return <IconBrain size={16} />
      case 'vector_search':
        return <IconSearch size={16} />
      case 'rerank':
        return <IconSortDescending size={16} />
      case 'context_assembly':
        return <IconFileText size={16} />
      default:
        return <IconDatabase size={16} />
    }
  }

  const totalDuration = steps.reduce((sum, step) => sum + step.duration, 0)

  return (
    <Accordion variant="filled" defaultValue="retrieval">
      <Accordion.Item value="retrieval">
        <Accordion.Control>
          <Group gap="xs">
            <ThemeIcon size="sm" color="orange" variant="light">
              <IconBug size={14} />
            </ThemeIcon>
            <Text size="sm" fw={600}>
              {t('retrieval.retrievalPipeline')}
            </Text>
            <Badge size="xs" variant="light" color="gray">
              {totalDuration}ms
            </Badge>
          </Group>
        </Accordion.Control>

        <Accordion.Panel>
          <Timeline active={steps.length} bulletSize={28} lineWidth={2} color="orange">
            {steps.map((step, idx) => (
              <Timeline.Item
                key={idx}
                bullet={
                  <ThemeIcon size="sm" color="orange" variant="light">
                    {getStepIcon(step.type)}
                  </ThemeIcon>
                }
                title={
                  <Group gap="xs">
                    <Text size="sm" fw={600}>
                      {step.title}
                    </Text>
                    <Badge size="xs" variant="light" color="gray">
                      {step.duration}ms
                    </Badge>
                  </Group>
                }
              >
                <Text size="sm" c="dimmed" mb="xs">
                  {step.description}
                </Text>

                {/* Step-specific data visualization */}
                {step.data && (
                  <div className={classes.stepData}>
                    <Text size="xs" c="dimmed">
                      {JSON.stringify(step.data)}
                    </Text>
                  </div>
                )}
              </Timeline.Item>
            ))}
          </Timeline>
        </Accordion.Panel>
      </Accordion.Item>
    </Accordion>
  )
}
