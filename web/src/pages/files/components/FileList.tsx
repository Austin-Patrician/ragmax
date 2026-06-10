import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  FileText,
  Folder,
  MoreHorizontal,
  Trash2,
} from 'lucide-react'
import { useDeleteSource } from '@/hooks/useSources'
import type { Source } from '@/types'
import classes from './FileList.module.css'

interface FileListProps {
  sources: Source[]
  isLoading: boolean
  onDeleteSources?: (sourceIds: string[]) => Promise<void>
  deleteActionLabel?: string
  deleteConfirmMessage?: string
}

type SortKey = 'name' | 'uploadedAt' | 'size'
type SortDirection = 'asc' | 'desc'

const PAGE_SIZE = 50

export function FileList({ sources, isLoading, onDeleteSources, deleteActionLabel, deleteConfirmMessage }: FileListProps) {
  const { t } = useTranslation()
  const selectAllRef = useRef<HTMLInputElement>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [sortKey, setSortKey] = useState<SortKey>('uploadedAt')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [page, setPage] = useState(1)
  const deleteSource = useDeleteSource()

  const sortedSources = useMemo(() => {
    return [...sources].sort((a, b) => compareSources(a, b, sortKey, sortDirection))
  }, [sortDirection, sortKey, sources])
  const selectedSources = useMemo(
    () => sortedSources.filter((source) => selectedIds.has(source.source_id)),
    [selectedIds, sortedSources],
  )
  const selectedCount = selectedSources.length

  const pageCount = Math.max(1, Math.ceil(sortedSources.length / PAGE_SIZE))
  const currentPage = Math.min(page, pageCount)
  const pageStart = (currentPage - 1) * PAGE_SIZE
  const pageSources = sortedSources.slice(pageStart, pageStart + PAGE_SIZE)
  const visibleIds = pageSources.map((source) => source.source_id)
  const allVisibleSelected =
    visibleIds.length > 0 && visibleIds.every((sourceId) => selectedIds.has(sourceId))
  const someVisibleSelected = visibleIds.some((sourceId) => selectedIds.has(sourceId))

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = someVisibleSelected && !allVisibleSelected
    }
  }, [allVisibleSelected, someVisibleSelected])

  const handleSort = (nextSortKey: SortKey) => {
    setPage(1)
    if (sortKey === nextSortKey) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'))
      return
    }
    setSortKey(nextSortKey)
    setSortDirection(nextSortKey === 'name' ? 'asc' : 'desc')
  }

  const toggleVisibleSelection = () => {
    setSelectedIds((current) => {
      const next = new Set(current)
      if (allVisibleSelected) {
        visibleIds.forEach((sourceId) => next.delete(sourceId))
      } else {
        visibleIds.forEach((sourceId) => next.add(sourceId))
      }
      return next
    })
  }

  const toggleRowSelection = (sourceId: string) => {
    setSelectedIds((current) => {
      const next = new Set(current)
      if (next.has(sourceId)) {
        next.delete(sourceId)
      } else {
        next.add(sourceId)
      }
      return next
    })
  }

  const handleDelete = async (sourceId: string) => {
    const defaultMsg = t('files.confirm_delete', 'Are you sure you want to delete this file?')
    if (window.confirm(deleteConfirmMessage || defaultMsg)) {
      if (onDeleteSources) {
        await onDeleteSources([sourceId])
      } else {
        await deleteSource.mutateAsync(sourceId)
      }
      setSelectedIds((current) => {
        const next = new Set(current)
        next.delete(sourceId)
        return next
      })
    }
  }

  const handleDeleteSelected = async () => {
    if (selectedSources.length === 0) return
    const defaultMsg = `Delete ${selectedSources.length} selected file(s)?`
    const confirmed = window.confirm(deleteConfirmMessage ? `${deleteConfirmMessage} (${selectedSources.length})` : defaultMsg)
    if (!confirmed) return

    if (onDeleteSources) {
      await onDeleteSources(selectedSources.map((s) => s.source_id))
    } else {
      for (const source of selectedSources) {
        await deleteSource.mutateAsync(source.source_id)
      }
    }
    setSelectedIds(new Set())
  }

  return (
    <section className={classes.panel} aria-label={t('files.list_title', 'Files')}>
      {selectedCount > 0 ? (
        <div className={classes.bulkBar} role="toolbar" aria-label="Selected file actions">
          <span className={classes.selectedText} aria-live="polite">
            Selected: <strong>{selectedCount}</strong> files
          </span>
          <span className={classes.bulkDivider} aria-hidden="true" />
          <button
            className={classes.bulkDeleteButton}
            disabled={!onDeleteSources && deleteSource.isPending}
            onClick={handleDeleteSelected}
            type="button"
          >
            <Trash2 size={15} />
            {deleteActionLabel || 'Delete'}
          </button>
        </div>
      ) : null}

      <div className={classes.tableFrame}>
        <table className={classes.table}>
          <thead>
            <tr>
              <th className={classes.checkboxColumn}>
                <input
                  aria-label="Select visible files"
                  aria-checked={
                    someVisibleSelected && !allVisibleSelected ? 'mixed' : allVisibleSelected
                  }
                  checked={allVisibleSelected}
                  className={classes.checkbox}
                  onChange={toggleVisibleSelection}
                  ref={selectAllRef}
                  type="checkbox"
                />
              </th>
              <th>
                <SortButton active={sortKey === 'name'} onClick={() => handleSort('name')}>
                  {t('files.table.filename', 'Name')}
                </SortButton>
              </th>
              <th>
                <SortButton
                  active={sortKey === 'uploadedAt'}
                  onClick={() => handleSort('uploadedAt')}
                >
                  {t('files.table.uploaded', 'Upload date')}
                </SortButton>
              </th>
              <th>
                <SortButton active={sortKey === 'size'} onClick={() => handleSort('size')}>
                  {t('files.table.size', 'Size')}
                </SortButton>
              </th>
              <th>{t('datasets.title', 'Dataset')}</th>
              <th>{t('files.table.actions', 'Action')}</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td className={classes.stateCell} colSpan={6}>
                  {t('common.loading', 'Loading...')}
                </td>
              </tr>
            ) : pageSources.length === 0 ? (
              <tr>
                <td className={classes.stateCell} colSpan={6}>
                  {t('files.empty_title', 'No files yet')}
                </td>
              </tr>
            ) : (
              pageSources.map((source) => (
                <tr
                  className={selectedIds.has(source.source_id) ? classes.selectedRow : undefined}
                  key={source.source_id}
                >
                  <td className={classes.checkboxColumn}>
                    <input
                      aria-label={`Select ${source.filename}`}
                      checked={selectedIds.has(source.source_id)}
                      className={classes.checkbox}
                      onChange={() => toggleRowSelection(source.source_id)}
                      type="checkbox"
                    />
                  </td>
                  <td>
                    <div className={classes.nameCell}>
                      <FileIcon source={source} />
                      <span>{source.filename || source.source_id}</span>
                    </div>
                  </td>
                  <td>{formatUploadedAt(source)}</td>
                  <td>{formatFileSize(source.file_size)}</td>
                  <td>{datasetLabel(source)}</td>
                  <td>
                    <div className={classes.actionCell}>
                      <button
                        aria-label={`Delete ${source.filename}`}
                        className={classes.iconButton}
                        disabled={deleteSource.isPending}
                        onClick={() => handleDelete(source.source_id)}
                        type="button"
                      >
                        <Trash2 size={15} />
                      </button>
                      <button
                        aria-label={`More actions for ${source.filename}`}
                        className={classes.iconButton}
                        type="button"
                      >
                        <MoreHorizontal size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className={classes.pagination}>
        <span className={classes.total}>Total {sources.length}</span>
        <button
          aria-label="Previous page"
          className={classes.pageArrow}
          disabled={currentPage <= 1}
          onClick={() => setPage((current) => Math.max(1, current - 1))}
          type="button"
        >
          <ChevronLeft size={16} />
        </button>
        <span className={classes.pageNumber}>{currentPage}</span>
        <button
          aria-label="Next page"
          className={classes.pageArrow}
          disabled={currentPage >= pageCount}
          onClick={() => setPage((current) => Math.min(pageCount, current + 1))}
          type="button"
        >
          <ChevronRight size={16} />
        </button>
        <button className={classes.pageSize} type="button">
          {PAGE_SIZE} / Page
        </button>
      </div>
    </section>
  )
}

function SortButton({
  active,
  children,
  onClick,
}: {
  active: boolean
  children: string
  onClick: () => void
}) {
  return (
    <button
      className={`${classes.sortButton} ${active ? classes.sortButtonActive : ''}`}
      onClick={onClick}
      type="button"
    >
      {children}
      <ArrowUpDown size={14} />
    </button>
  )
}

function FileIcon({ source }: { source: Source }) {
  if (isFolderLike(source)) {
    return (
      <span className={classes.folderIcon}>
        <Folder size={17} />
      </span>
    )
  }

  return (
    <span className={classes.fileIcon}>
      <FileText size={16} />
    </span>
  )
}

function compareSources(
  a: Source,
  b: Source,
  sortKey: SortKey,
  sortDirection: SortDirection,
) {
  const direction = sortDirection === 'asc' ? 1 : -1
  if (sortKey === 'name') {
    return direction * (a.filename || '').localeCompare(b.filename || '')
  }
  if (sortKey === 'size') {
    return direction * ((a.file_size ?? 0) - (b.file_size ?? 0))
  }
  return direction * (uploadedAtValue(a) - uploadedAtValue(b))
}

function uploadedAtValue(source: Source) {
  const value = metadataString(source, ['created_at', 'uploaded_at', 'upload_date'])
  return value ? new Date(value).getTime() || 0 : 0
}

function formatUploadedAt(source: Source) {
  const value = metadataString(source, ['created_at', 'uploaded_at', 'upload_date'])
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    hour: '2-digit',
    hour12: false,
    minute: '2-digit',
    month: '2-digit',
    second: '2-digit',
    year: 'numeric',
  })
    .format(date)
    .replace(',', '')
}

function formatFileSize(bytes: number | null) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function datasetLabel(source: Source) {
  return metadataString(source, ['dataset', 'dataset_name']) || ''
}

function isFolderLike(source: Source) {
  return (
    source.media_type === 'inode/directory' ||
    metadataString(source, ['source_kind']) === 'folder' ||
    (!source.has_file && source.file_size === 0)
  )
}

function metadataString(source: Source, keys: string[]) {
  for (const key of keys) {
    const value = source.metadata?.[key]
    if (typeof value === 'string' && value.trim()) {
      return value
    }
  }
  return ''
}
