import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { Search, Upload } from 'lucide-react'
import { ROUTES } from '@/constants/routes'
import { useSources } from '@/hooks/useSources'
import { FileList } from './components/FileList'
import { FileUploadDialog } from './components/FileUploadDialog'
import classes from './FilesPage.module.css'

export default function FilesPage() {
  const { t } = useTranslation()
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const { data: sources, isLoading } = useSources()
  const filteredSources = useMemo(() => {
    const items = sources ?? []
    const query = searchQuery.trim().toLowerCase()
    if (!query) return items

    return items.filter((source) => {
      const filename = source.filename?.toLowerCase() ?? ''
      const mediaType = source.media_type?.toLowerCase() ?? ''
      const sourceId = source.source_id.toLowerCase()
      return filename.includes(query) || mediaType.includes(query) || sourceId.includes(query)
    })
  }, [searchQuery, sources])

  return (
    <div className={classes.page}>
      <div className={classes.toolbar}>
        <nav className={classes.segmentedNav} aria-label="Files views">
          <span className={classes.segmentedItemActive}>{t('nav.files', 'Files')}</span>
          <Link className={classes.segmentedItem} to={ROUTES.evaluation}>
            {t('nav.evaluation', 'Evaluation')}
          </Link>
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
            onClick={() => setIsUploadDialogOpen(true)}
            className={classes.uploadButton}
            type="button"
          >
            <Upload size={16} />
            {t('files.add_file', 'Add file')}
          </button>
        </div>
      </div>

      <div className={classes.listArea}>
        <FileList sources={filteredSources} isLoading={isLoading} />
      </div>

      <FileUploadDialog
        isOpen={isUploadDialogOpen}
        onClose={() => setIsUploadDialogOpen(false)}
      />
    </div>
  )
}
