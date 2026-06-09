import { Link } from 'react-router'
import { useTranslation } from 'react-i18next'
import { useDatasets } from '@/hooks/useDatasets'

export default function DatasetsPage() {
  const { t } = useTranslation()
  const { data: datasets, isLoading } = useDatasets()

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
  }

  const getInitials = (name: string) => {
    return name.charAt(0).toUpperCase()
  }

  const getColorFromName = (name: string) => {
    const colors = [
      '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6', '#6366f1', '#ef4444', '#14b8a6'
    ]
    const index = name.charCodeAt(0) % colors.length
    return colors[index]
  }

  return (
    <div style={{ padding: '24px', maxWidth: '1600px', margin: '0 auto' }}>
      {/* Header Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <span style={{ fontSize: '24px' }}>💾</span>
          <h1 style={{ fontSize: '24px', fontWeight: 600, margin: 0 }}>
            {t('datasets.title', 'Dataset')}
          </h1>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button
            style={{
              background: 'transparent',
              border: '1px solid #ddd',
              borderRadius: '8px',
              padding: '8px 12px',
              fontSize: '14px',
              cursor: 'pointer',
            }}
          >
            🔽
          </button>
          <input
            type="search"
            placeholder={t('datasets.search_placeholder', 'Search')}
            style={{
              padding: '8px 16px',
              border: '1px solid #ddd',
              borderRadius: '8px',
              fontSize: '14px',
              width: '200px',
            }}
          />
          <Link
            to="/datasets/new"
            style={{
              background: '#000',
              color: '#fff',
              textDecoration: 'none',
              border: 'none',
              borderRadius: '8px',
              padding: '8px 16px',
              fontSize: '14px',
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            + {t('datasets.create_dataset', 'Create dataset')}
          </Link>
        </div>
      </div>

      {/* Datasets Grid */}
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '60px', color: '#666' }}>
          {t('common.loading', 'Loading...')}
        </div>
      ) : datasets && datasets.length > 0 ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
          {datasets.map((dataset) => (
            <Link
              key={dataset.dataset_id}
              to={`/datasets/${dataset.dataset_id}`}
              style={{
                background: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: '12px',
                padding: '20px',
                textDecoration: 'none',
                color: 'inherit',
                transition: 'all 150ms ease',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)'
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.08)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)'
                e.currentTarget.style.boxShadow = 'none'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '8px',
                    background: getColorFromName(dataset.name),
                    color: '#fff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '18px',
                    fontWeight: 600,
                  }}
                >
                  {getInitials(dataset.name)}
                </div>
                <h3 style={{ fontSize: '16px', fontWeight: 600, margin: 0, flex: 1 }}>
                  {dataset.name}
                </h3>
              </div>
              {dataset.description && (
                <p style={{ fontSize: '13px', color: '#666', margin: 0, lineHeight: '1.5' }}>
                  {dataset.description}
                </p>
              )}
              <div style={{ fontSize: '12px', color: '#999', marginTop: 'auto' }}>
                <div>0 {t('datasets.files_count', 'files')}</div>
                <div>{formatDate(dataset.created_at)}</div>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div
          style={{
            background: '#f9fafb',
            borderRadius: '12px',
            padding: '60px',
            textAlign: 'center',
            color: '#666',
          }}
        >
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>📦</div>
          <h3 style={{ fontSize: '18px', marginBottom: '8px', color: '#333' }}>
            {t('datasets.empty_title', 'No datasets yet')}
          </h3>
          <p style={{ marginBottom: '24px' }}>
            {t('datasets.empty_subtitle', 'Create your first dataset to organize your files')}
          </p>
          <Link
            to="/datasets/new"
            style={{
              background: '#000',
              color: '#fff',
              textDecoration: 'none',
              borderRadius: '8px',
              padding: '10px 20px',
              fontSize: '14px',
              fontWeight: 600,
              display: 'inline-block',
            }}
          >
            {t('datasets.create_first', 'Create Dataset')}
          </Link>
        </div>
      )}
    </div>
  )
}
