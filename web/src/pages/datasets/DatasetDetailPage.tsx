import { useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { Search, Plus, ArrowLeft } from 'lucide-react'
import { useDataset, useAddFilesToDataset, useRemoveFileFromDataset } from '@/hooks/useDatasets'
import { useSources } from '@/hooks/useSources'
import { FileList } from '../files/components/FileList'
import classes from '../files/FilesPage.module.css'

export default function DatasetDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: datasetWithFiles, isLoading } = useDataset(id)
  const { data: allSources } = useSources()
  const addFiles = useAddFilesToDataset()
  const removeFile = useRemoveFileFromDataset()
  
  const [isAddingFiles, setIsAddingFiles] = useState(false)
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([])
  const [searchQuery, setSearchQuery] = useState('')

  const datasetSources = useMemo(() => {
    if (!datasetWithFiles || !allSources) return []
    const fileSourceIds = new Set(datasetWithFiles.files.map((f) => f.source_id))
    let sources = allSources.filter((s) => fileSourceIds.has(s.source_id))
    
    const query = searchQuery.trim().toLowerCase()
    if (query) {
      sources = sources.filter((source) => {
        const filename = source.filename?.toLowerCase() ?? ''
        const mediaType = source.media_type?.toLowerCase() ?? ''
        const sourceId = source.source_id.toLowerCase()
        return filename.includes(query) || mediaType.includes(query) || sourceId.includes(query)
      })
    }
    return sources
  }, [datasetWithFiles, allSources, searchQuery])

  const availableSources = useMemo(() => {
    if (!datasetWithFiles || !allSources) return []
    const fileSourceIds = new Set(datasetWithFiles.files.map((f) => f.source_id))
    return allSources.filter((s) => !fileSourceIds.has(s.source_id))
  }, [datasetWithFiles, allSources])

  if (isLoading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: '#666' }}>
        {t('common.loading', 'Loading...')}
      </div>
    )
  }

  if (!datasetWithFiles) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <h2>{t('datasets.not_found', 'Dataset not found')}</h2>
      </div>
    )
  }

  const handleAddFiles = async () => {
    if (selectedSourceIds.length === 0) return
    await addFiles.mutateAsync({ datasetId: datasetWithFiles.dataset.dataset_id, input: { source_ids: selectedSourceIds } })
    setSelectedSourceIds([])
    setIsAddingFiles(false)
  }

  const handleRemoveFiles = async (sourceIds: string[]) => {
    for (const sourceId of sourceIds) {
      await removeFile.mutateAsync({ datasetId: datasetWithFiles.dataset.dataset_id, sourceId })
    }
  }

  return (
    <div className={classes.page}>
      <div className={classes.toolbar}>
        <nav className={classes.segmentedNav} aria-label="Dataset navigation">
          <button
            className={classes.segmentedItem}
            onClick={() => navigate('/datasets')}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', border: 'none', background: 'transparent', cursor: 'pointer' }}
          >
            <ArrowLeft size={16} />
            {t('common.back', 'Back')}
          </button>
          <span className={classes.segmentedItemActive}>
            {datasetWithFiles.dataset.name}
          </span>
        </nav>

        <div className={classes.toolbarActions}>
          <label className={classes.searchBox}>
            <Search size={16} aria-hidden="true" />
            <input
              type="search"
              placeholder={t('files.search_placeholder', 'Search')}
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.currentTarget.value)}
            />
          </label>
          <button
            onClick={() => setIsAddingFiles(true)}
            className={classes.uploadButton}
            type="button"
          >
            <Plus size={16} />
            {t('datasets.add_files', 'Add files')}
          </button>
        </div>
      </div>

      <div className={classes.listArea}>
        <FileList 
          sources={datasetSources} 
          isLoading={isLoading} 
          onDeleteSources={handleRemoveFiles}
          deleteActionLabel={t('common.remove', 'Remove')}
          deleteConfirmMessage={t('datasets.confirm_remove_file', 'Remove this file from the dataset?')}
        />
      </div>

      {/* Add Files Dialog */}
      {isAddingFiles && (
        <>
          <div
            onClick={() => setIsAddingFiles(false)}
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0, 0, 0, 0.5)',
              zIndex: 1000,
            }}
          />
          <div
            style={{
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              background: '#fff',
              borderRadius: '18px',
              padding: '32px',
              width: '90%',
              maxWidth: '600px',
              maxHeight: '80vh',
              overflowY: 'auto',
              zIndex: 1001,
            }}
          >
            <h2 style={{ marginBottom: '20px' }}>{t('datasets.select_files', 'Select Files to Add')}</h2>
            {availableSources.length === 0 ? (
              <p style={{ color: '#666' }}>{t('datasets.no_available_files', 'No available files. Upload files first.')}</p>
            ) : (
              <div style={{ display: 'grid', gap: '8px', marginBottom: '20px' }}>
                {availableSources.map((source) => (
                  <label
                    key={source.source_id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: '12px',
                      background: '#f9f9f9',
                      borderRadius: '8px',
                      cursor: 'pointer',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={selectedSourceIds.includes(source.source_id)}
                      onChange={(e) => {
                         if (e.target.checked) {
                           setSelectedSourceIds([...selectedSourceIds, source.source_id])
                         } else {
                           setSelectedSourceIds(selectedSourceIds.filter((id) => id !== source.source_id))
                         }
                      }}
                      style={{ marginRight: '12px' }}
                    />
                    <span>{source.filename}</span>
                  </label>
                ))}
              </div>
            )}
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => {
                  setIsAddingFiles(false)
                  setSelectedSourceIds([])
                }}
                style={{
                  background: '#f0f0f0',
                  border: 'none',
                  borderRadius: '12px',
                  padding: '12px 24px',
                  cursor: 'pointer',
                }}
              >
                {t('common.cancel', 'Cancel')}
              </button>
              <button
                onClick={handleAddFiles}
                disabled={selectedSourceIds.length === 0}
                style={{
                  background: selectedSourceIds.length === 0 ? '#ccc' : '#1f7a5b',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '12px',
                  padding: '12px 24px',
                  cursor: selectedSourceIds.length === 0 ? 'not-allowed' : 'pointer',
                }}
              >
                {t('datasets.add_selected', 'Add Selected')} ({selectedSourceIds.length})
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
