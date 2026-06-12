import type { ChangeEvent, DragEvent, InputHTMLAttributes } from 'react'
import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import { FileText, FolderUp, UploadCloud, Settings } from 'lucide-react'
import { runSourceIndexing, uploadSource } from '@/api/indexing'
import { queryKeys } from '@/hooks/queryKeys'
import { sourceKeys } from '@/hooks/useSources'
import { IndexingConfigForm } from '@/components/indexing/IndexingConfigForm'
import type { IndexingConfig } from '@/types/indexing'
import { INDEXING_PRESETS } from '@/config/indexing-presets'
import type { RunSourceIndexingInput } from '@/types'
import classes from './FileUploadDialog.module.css'

interface FileUploadDialogProps {
  isOpen: boolean
  onClose: () => void
}

type UploadMode = 'files' | 'folder'
type DirectoryInputAttributes = InputHTMLAttributes<HTMLInputElement> & {
  directory?: string
  webkitdirectory?: string
}

const MAX_FOLDER_FILES = 10

export function FileUploadDialog({ isOpen, onClose }: FileUploadDialogProps) {
  const { t } = useTranslation()
  const [mode, setMode] = useState<UploadMode>('files')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [processedCount, setProcessedCount] = useState(0)
  const [errorMessage, setErrorMessage] = useState('')
  const [showConfig, setShowConfig] = useState(false)
  const [indexingConfig, setIndexingConfig] = useState<IndexingConfig>(
    INDEXING_PRESETS.default.config
  )
  const fileInputRef = useRef<HTMLInputElement>(null)
  const folderInputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()

  if (!isOpen) return null

  const resetDialog = () => {
    setMode('files')
    setSelectedFiles([])
    setIsDragging(false)
    setUploading(false)
    setProcessedCount(0)
    setErrorMessage('')
    setShowConfig(false)
    setIndexingConfig(INDEXING_PRESETS.default.config)
  }

  const closeDialog = () => {
    if (uploading) return
    resetDialog()
    onClose()
  }

  const changeMode = (nextMode: UploadMode) => {
    setMode(nextMode)
    setSelectedFiles([])
    setErrorMessage('')
    setProcessedCount(0)
  }

  const selectFromInput = (
    event: ChangeEvent<HTMLInputElement>,
    nextMode: UploadMode,
  ) => {
    applyFiles(event.currentTarget.files, nextMode)
    event.currentTarget.value = ''
  }

  const applyFiles = (fileList: FileList | null, nextMode = mode) => {
    const files = Array.from(fileList ?? []).filter((file) => file.name)
    if (files.length === 0) return

    if (nextMode === 'folder' && files.length > MAX_FOLDER_FILES) {
      setSelectedFiles([])
      setErrorMessage(`Folder upload supports up to ${MAX_FOLDER_FILES} files at a time.`)
      return
    }

    setErrorMessage('')
    setSelectedFiles(files)
  }

  const handleDrop = (event: DragEvent<HTMLButtonElement>) => {
    event.preventDefault()
    setIsDragging(false)
    applyFiles(event.dataTransfer.files)
  }

  const handleSubmit = async () => {
    if (selectedFiles.length === 0 || uploading) return
    if (mode === 'folder' && selectedFiles.length > MAX_FOLDER_FILES) {
      setErrorMessage(`Folder upload supports up to ${MAX_FOLDER_FILES} files at a time.`)
      return
    }

    setUploading(true)
    setProcessedCount(0)
    setErrorMessage('')
    let uploadSucceeded = false
    try {
      for (const file of selectedFiles) {
        const source = await uploadSource({
          file,
          notebookId: 'default',
          metadata: JSON.stringify(uploadMetadata(file, mode)),
        })

        const request: RunSourceIndexingInput = {
          sourceId: source.source_id,
        }
        if (indexingConfig.parser !== undefined) request.parser = indexingConfig.parser
        if (indexingConfig.parser_config !== undefined) request.parser_config = indexingConfig.parser_config
        if (indexingConfig.chunker !== undefined) request.chunker = indexingConfig.chunker
        if (indexingConfig.chunk_config !== undefined) request.chunk_config = indexingConfig.chunk_config
        if (indexingConfig.capture_artifacts !== undefined) {
          request.capture_artifacts = indexingConfig.capture_artifacts
        }

        await runSourceIndexing(request)
        setProcessedCount((current) => current + 1)
      }
      await queryClient.invalidateQueries({ queryKey: sourceKeys.all })
      await queryClient.invalidateQueries({ queryKey: queryKeys.indexing.all })
      uploadSucceeded = true
      resetDialog()
      onClose()
    } catch (error) {
      console.error('Upload failed:', error)
      setErrorMessage(t('files.upload_or_index_error', 'Failed to upload or index file'))
    } finally {
      if (!uploadSucceeded) {
        setUploading(false)
      }
    }
  }

  const directoryAttributes: DirectoryInputAttributes = {
    directory: '',
    webkitdirectory: '',
  }
  const selectedSummary =
    selectedFiles.length === 0
      ? ''
      : selectedFiles.length === 1
        ? selectedFiles[0]?.name
        : `${selectedFiles.length} files selected`

  return (
    <div className={classes.layer}>
      <button
        aria-label={t('common.cancel', 'Close upload dialog')}
        className={classes.backdrop}
        onClick={closeDialog}
        type="button"
      />
      <section
        aria-labelledby="upload-file-title"
        aria-modal="true"
        className={classes.dialog}
        role="dialog"
      >
        <header className={classes.header}>
          <h2 id="upload-file-title">{t('files.upload_dialog.title', 'Upload file')}</h2>
        </header>

        <div className={classes.body}>
          <div className={classes.tabs} role="tablist" aria-label="Upload type">
            <button
              aria-selected={mode === 'files'}
              className={mode === 'files' ? classes.tabActive : classes.tab}
              onClick={() => changeMode('files')}
              role="tab"
              type="button"
            >
              <FileText size={16} />
              Files
            </button>
            <button
              aria-selected={mode === 'folder'}
              className={mode === 'folder' ? classes.tabActive : classes.tab}
              onClick={() => changeMode('folder')}
              role="tab"
              type="button"
            >
              <FolderUp size={16} />
              Folder
            </button>
          </div>

          <button
            className={`${classes.dropzone} ${isDragging ? classes.dropzoneDragging : ''}`}
            onClick={() =>
              mode === 'files'
                ? fileInputRef.current?.click()
                : folderInputRef.current?.click()
            }
            onDragLeave={() => setIsDragging(false)}
            onDragOver={(event) => {
              event.preventDefault()
              setIsDragging(true)
            }}
            onDrop={handleDrop}
            type="button"
          >
            <UploadCloud size={46} strokeWidth={1.5} />
            <strong>
              {selectedSummary || 'Drag and drop your file here to upload'}
            </strong>
            <span>
              {mode === 'folder'
                ? `Select one folder with no more than ${MAX_FOLDER_FILES} files.`
                : 'Supports single or batch file upload.'}
            </span>
            {selectedSummary ? <em>{selectedSummary}</em> : null}
          </button>

          <input
            className={classes.hiddenInput}
            multiple
            onChange={(event) => selectFromInput(event, 'files')}
            ref={fileInputRef}
            type="file"
          />
          <input
            {...directoryAttributes}
            className={classes.hiddenInput}
            multiple
            onChange={(event) => selectFromInput(event, 'folder')}
            ref={folderInputRef}
            type="file"
          />

          {/* 配置切换按钮 */}
          <button
            className={classes.configToggle}
            onClick={() => setShowConfig(!showConfig)}
            type="button"
            disabled={uploading}
          >
            <Settings size={16} />
            {showConfig ? '隐藏索引配置' : '显示索引配置'}
          </button>

          {/* 索引配置表单 */}
          {showConfig && (
            <div className={classes.configSection}>
              <IndexingConfigForm value={indexingConfig} onChange={setIndexingConfig} />
            </div>
          )}

          {errorMessage ? <p className={classes.error}>{errorMessage}</p> : null}
          {uploading ? (
            <p className={classes.progress}>
              {t('files.uploading_and_indexing', 'Uploading and indexing...')}{' '}
              {processedCount}/{selectedFiles.length}
            </p>
          ) : null}
        </div>

        <footer className={classes.footer}>
          <button
            className={classes.saveButton}
            disabled={selectedFiles.length === 0 || uploading}
            onClick={handleSubmit}
            type="button"
          >
            {uploading
              ? t('files.uploading_and_indexing', 'Uploading and indexing...')
              : t('common.save', 'Save')}
          </button>
        </footer>
      </section>
    </div>
  )
}

function uploadMetadata(file: File, mode: UploadMode) {
  const fileWithPath = file as File & { webkitRelativePath?: string }
  return {
    upload_mode: mode,
    relative_path: fileWithPath.webkitRelativePath || file.name,
    source_kind: mode === 'folder' ? 'folder' : 'file',
    uploaded_at: new Date().toISOString(),
  }
}
