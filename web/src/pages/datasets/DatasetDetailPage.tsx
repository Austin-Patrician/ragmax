import { useState } from 'react'
import { useParams, useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { useDataset, useDeleteDataset, useAddFilesToDataset, useRemoveFileFromDataset } from '@/hooks/useDatasets'
import { useSources } from '@/hooks/useSources'

export default function DatasetDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: datasetWithFiles, isLoading } = useDataset(id)
  const { data: allSources } = useSources()
  const deleteDataset = useDeleteDataset()
  const addFiles = useAddFilesToDataset()
  const removeFile = useRemoveFileFromDataset()
  const [isAddingFiles, setIsAddingFiles] = useState(false)
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([])

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

  const { dataset, files } = datasetWithFiles
  const fileSourceIds = new Set(files.map((f) => f.source_id))
  const availableSources = allSources?.filter((s) => !fileSourceIds.has(s.source_id)) || []

  const handleDelete = async () => {
    if (window.confirm(t('datasets.confirm_delete', 'Are you sure you want to delete this dataset?'))) {
      await deleteDataset.mutateAsync(dataset.dataset_id)
      navigate('/datasets')
    }
  }

  const handleAddFiles = async () => {
    if (selectedSourceIds.length === 0) return
    await addFiles.mutateAsync({ datasetId: dataset.dataset_id, input: { source_ids: selectedSourceIds } })
    setSelectedSourceIds([])
    setIsAddingFiles(false)
  }

  const handleRemoveFile = async (sourceId: string) => {
    if (window.confirm(t('datasets.confirm_remove_file', 'Remove this file from the dataset?'))) {
      await removeFile.mutateAsync({ datasetId: dataset.dataset_id, sourceId })
    }
  }

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <button
          onClick={() => navigate('/datasets')}
          style={{
            background: 'none',
            border: 'none',
            color: '#1f7a5b',
            fontSize: '14px',
            cursor: 'pointer',
            marginBottom: '16px',
          }}
        >
          ← {t('common.back', 'Back to Datasets')}
        </button>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 style={{ fontSize: '32px', fontWeight: 600 }}>{dataset.name}</h1>
            {dataset.description && <p style={{ color: '#666', marginTop: '8px' }}>{dataset.description}</p>}
          </div>
          <button
            onClick={handleDelete}
            style={{
              background: '#fee',
              color: '#c33',
              border: '1px solid #fcc',
              borderRadius: '12px',
              padding: '10px 20px',
              fontSize: '14px',
              cursor: 'pointer',
            }}
          >
            {t('common.delete', 'Delete')}
          </button>
        </div>
      </div>

      {/* Files Section */}
      <div style={{ background: '#fffffb', borderRadius: '18px', padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 600 }}>
            {t('datasets.files_title', 'Files')} ({files.length})
          </h2>
          <button
            onClick={() => setIsAddingFiles(true)}
            style={{
              background: '#1f7a5b',
              color: '#fff',
              border: 'none',
              borderRadius: '12px',
              padding: '10px 20px',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            + {t('datasets.add_files', 'Add Files')}
          </button>
        </div>

        {files.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>📄</div>
            <p>{t('datasets.no_files', 'No files in this dataset yet')}</p>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '12px' }}>
            {files.map((file) => (
              <div
                key={file.id}
                style={{
                  background: '#f9f9f9',
                  border: '1px solid #e0e0e0',
                  borderRadius: '12px',
                  padding: '16px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontWeight: 500 }}>📄 Source ID: {file.source_id}</div>
                  <div style={{ fontSize: '13px', color: '#666', marginTop: '4px' }}>
                    {t('datasets.added_at', 'Added')}: {new Date(file.added_at || '').toLocaleString()}
                  </div>
                </div>
                <button
                  onClick={() => handleRemoveFile(file.source_id)}
                  style={{
                    background: '#fee',
                    color: '#c33',
                    border: '1px solid #fcc',
                    borderRadius: '8px',
                    padding: '6px 12px',
                    fontSize: '13px',
                    cursor: 'pointer',
                  }}
                >
                  {t('common.remove', 'Remove')}
                </button>
              </div>
            ))}
          </div>
        )}
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
