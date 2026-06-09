import { Paper, Group, Text, Tooltip } from '@mantine/core'
import {
  Boxes,
  Brain,
  FileCode2,
  Layers3,
  ScanSearch,
  Sparkles,
  CheckCircle2,
  Clock,
  XCircle,
  Circle,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { IndexingStageName, IndexStageRun } from '@/types'
import classes from './StageTimeline.module.css'

const STAGES: Array<{
  name: IndexingStageName
  labelKey: string
  descriptionKey: string
  icon: typeof FileCode2
}> = [
  {
    name: 'source',
    labelKey: 'indexing.sourceStage',
    descriptionKey: 'indexing.sourceStageDescription',
    icon: FileCode2,
  },
  {
    name: 'parse_blocks',
    labelKey: 'indexing.parseStage',
    descriptionKey: 'indexing.parseStageDescription',
    icon: ScanSearch,
  },
  {
    name: 'analyze_profile',
    labelKey: 'indexing.analyzeStage',
    descriptionKey: 'indexing.analyzeStageDescription',
    icon: Brain,
  },
  {
    name: 'chunk_nodes',
    labelKey: 'indexing.chunkStage',
    descriptionKey: 'indexing.chunkStageDescription',
    icon: Layers3,
  },
  {
    name: 'quality_enrich',
    labelKey: 'indexing.qualityStage',
    descriptionKey: 'indexing.qualityStageDescription',
    icon: Sparkles,
  },
  {
    name: 'vectorize',
    labelKey: 'indexing.vectorStage',
    descriptionKey: 'indexing.vectorStageDescription',
    icon: Boxes,
  },
]

type StageTimelineProps = {
  stages: IndexStageRun[]
  selectedStage: IndexingStageName
  onSelectStage: (stage: IndexingStageName) => void
}

export function StageTimeline({ stages, selectedStage, onSelectStage }: StageTimelineProps) {
  const { t } = useTranslation()

  return (
    <Paper withBorder radius="lg" p="md" className={classes.container || ''}>
      <Text fw={700} size="sm" mb="sm">
        {t('indexing.stageTimeline')}
      </Text>
      <div className={classes.timeline || ''}>
        {STAGES.map((stage, index) => {
          const stageRun = stages.find((s) => s.stage_name === stage.name)
          const isSelected = selectedStage === stage.name
          const isLast = index === STAGES.length - 1

          return (
            <div key={stage.name} className={classes.stageWrapper || ''}>
              <StageCard
                stage={stage}
                stageRun={stageRun}
                selected={isSelected}
                onClick={() => onSelectStage(stage.name)}
              />
              {!isLast && <div className={classes.connector || ''} />}
            </div>
          )
        })}
      </div>
    </Paper>
  )
}

type StageCardProps = {
  stage: (typeof STAGES)[number]
  stageRun: IndexStageRun | undefined
  selected: boolean
  onClick: () => void
}

function StageCard({ stage, stageRun, selected, onClick }: StageCardProps) {
  const { t } = useTranslation()
  const Icon = stage.icon
  const statusIcon = getStatusIcon(stageRun?.status)

  return (
    <Tooltip label={t(stage.descriptionKey)} position="bottom" withArrow>
      <button
        type="button"
        className={`${classes.stageCard || ''} ${selected ? classes.stageCardSelected || '' : ''} ${
          stageRun ? getStatusClass(stageRun.status) : ''
        }`}
        onClick={onClick}
      >
        <div className={classes.stageIcon || ''}>
          <Icon size={20} />
        </div>
        <div className={classes.stageBody || ''}>
          <Group justify="space-between" gap={4} wrap="nowrap">
            <Text fw={700} size="xs" lineClamp={1}>
              {t(stage.labelKey)}
            </Text>
            <div className={classes.statusIcon || ''}>{statusIcon}</div>
          </Group>
          {stageRun && (
            <Group gap={4} mt={2}>
              {stageRun.duration_ms !== null && (
                <Text size="10px" c="dimmed">
                  {formatDuration(stageRun.duration_ms)}
                </Text>
              )}
              {stageRun.artifact_count > 0 && (
                <>
                  <Text size="10px" c="dimmed">
                    •
                  </Text>
                  <Text size="10px" c="dimmed">
                    {stageRun.artifact_count} {t('common.artifacts')}
                  </Text>
                </>
              )}
            </Group>
          )}
        </div>
      </button>
    </Tooltip>
  )
}

function getStatusIcon(status: string | undefined) {
  switch (status) {
    case 'succeeded':
    case 'completed':
      return <CheckCircle2 size={14} className={classes.iconSuccess} />
    case 'failed':
      return <XCircle size={14} className={classes.iconError} />
    case 'running':
      return <Clock size={14} className={classes.iconRunning} />
    case 'pending':
      return <Circle size={14} className={classes.iconPending} />
    default:
      return <Circle size={14} className={classes.iconDefault} />
  }
}

function getStatusClass(status: string): string {
  switch (status) {
    case 'succeeded':
    case 'completed':
      return classes.stageSuccess || ''
    case 'failed':
      return classes.stageError || ''
    case 'running':
      return classes.stageRunning || ''
    default:
      return ''
  }
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}m`
}
