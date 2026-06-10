import { Alert } from '@mantine/core'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useSources } from '@/hooks/useSources'
import {
  useIndexArtifactData,
  useIndexPipelineRun,
  useIndexPipelineStageArtifacts,
  useLatestIndexPipelineRuns,
} from '@/hooks/useIndexing'
import type { IndexingStageName } from '@/types'
import { FileListPanel } from './components/FileListPanel'
import { StageTimeline } from './components/StageTimeline'
import { ArtifactViewer } from './components/ArtifactViewer'
import classes from './IndexingPage.module.css'

export function IndexingPage() {
  const { t } = useTranslation()
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null)
  const [selectedStage, setSelectedStage] = useState<IndexingStageName>('source')

  const {
    data: sources,
    isLoading: sourcesLoading,
    error: sourcesError,
  } = useSources({ limit: 100 })
  const {
    data: latestRuns,
    isLoading: runsLoading,
    error: runsError,
  } = useLatestIndexPipelineRuns(100)

  const filesWithRuns = useMemo(() => {
    if (!sources || !latestRuns) return []

    const runsBySourceId = new Map(latestRuns.map((run) => [run.source_id, run]))
    return sources
      .map((source) => ({
        source,
        latestRun: runsBySourceId.get(source.source_id) ?? null,
      }))
      .filter((item) => item.latestRun !== null)
  }, [latestRuns, sources])

  const latestRun = useMemo(() => {
    if (!selectedSourceId || !latestRuns) return null
    return latestRuns.find((run) => run.source_id === selectedSourceId) ?? null
  }, [latestRuns, selectedSourceId])

  const runDetailQuery = useIndexPipelineRun(latestRun?.run_id || null)
  const runDetail = runDetailQuery.data

  const stageArtifactsQuery = useIndexPipelineStageArtifacts(
    latestRun?.run_id || null,
    selectedStage,
  )
  const stageArtifacts = stageArtifactsQuery.data
  const firstArtifact = stageArtifacts?.manifests?.[0] || null
  const artifactDataQuery = useIndexArtifactData(firstArtifact?.artifact_id || null)

  const handleSelectFile = (sourceId: string) => {
    setSelectedSourceId(sourceId)
    setSelectedStage('source')
  }

  const handleSelectStage = (stage: IndexingStageName) => {
    setSelectedStage(stage)
  }

  return (
    <div className={classes.pageContainer || ''}>
      <div className={classes.mainLayout || ''}>
        <aside className={classes.sidebar || ''}>
          <FileListPanel
            files={filesWithRuns}
            selectedSourceId={selectedSourceId}
            onSelectFile={handleSelectFile}
            isLoading={sourcesLoading || runsLoading}
            error={sourcesError || runsError}
          />
        </aside>

        <main className={classes.mainContent || ''}>
          {!selectedSourceId ? (
            <Alert color="gray" className={classes.emptyState || ''}>
              {t('indexing.selectFile')}
            </Alert>
          ) : !latestRun ? (
            <Alert color="gray" className={classes.emptyState || ''}>
              No indexing run found for this file.
            </Alert>
          ) : (
            <div className={classes.detailColumn || ''}>
              <StageTimeline
                stages={runDetail?.stages || []}
                selectedStage={selectedStage}
                onSelectStage={handleSelectStage}
              />
              <div className={classes.artifactPane || ''}>
                <ArtifactViewer
                  stageName={selectedStage}
                  artifactData={artifactDataQuery.data || null}
                  isLoading={artifactDataQuery.isLoading}
                  error={artifactDataQuery.error}
                />
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
