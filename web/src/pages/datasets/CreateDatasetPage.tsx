import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { useCreateDataset } from '@/hooks/useDatasets'
import type { CreateDatasetInput } from '@/types'

export default function CreateDatasetPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const createDataset = useCreateDataset()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return

    try {
      const input: CreateDatasetInput = { name: name.trim() }
      const trimmedDescription = description.trim()
      if (trimmedDescription) {
        input.description = trimmedDescription
      }
      const dataset = await createDataset.mutateAsync(input)
      navigate(`/datasets/${dataset.dataset_id}`)
    } catch (error) {
      console.error('Failed to create dataset:', error)
      alert(t('datasets.create_error', 'Failed to create dataset'))
    }
  }

  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
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
        <h1 style={{ fontSize: '32px', fontWeight: 600 }}>
          {t('datasets.create.title', 'Create New Dataset')}
        </h1>
        <p style={{ color: '#666', marginTop: '8px' }}>
          {t('datasets.create.subtitle', 'Organize your files into a knowledge dataset')}
        </p>
      </div>

      <form onSubmit={handleSubmit} style={{ background: '#fffffb', borderRadius: '18px', padding: '32px' }}>
        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: 600 }}>
            {t('datasets.create.name_label', 'Dataset Name')} *
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t('datasets.create.name_placeholder', 'e.g., Product Documentation')}
            required
            style={{
              width: '100%',
              padding: '12px',
              border: '1px solid #dfe2d6',
              borderRadius: '12px',
              fontSize: '14px',
            }}
          />
        </div>

        <div style={{ marginBottom: '32px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: 600 }}>
            {t('datasets.create.description_label', 'Description')} ({t('common.optional', 'Optional')})
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={t('datasets.create.description_placeholder', 'Describe what this dataset contains...')}
            rows={4}
            style={{
              width: '100%',
              padding: '12px',
              border: '1px solid #dfe2d6',
              borderRadius: '12px',
              fontSize: '14px',
              resize: 'vertical',
            }}
          />
        </div>

        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
          <button
            type="button"
            onClick={() => navigate('/datasets')}
            style={{
              background: '#f0f0f0',
              border: 'none',
              borderRadius: '12px',
              padding: '12px 24px',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {t('common.cancel', 'Cancel')}
          </button>
          <button
            type="submit"
            disabled={!name.trim() || createDataset.isPending}
            style={{
              background: !name.trim() || createDataset.isPending ? '#ccc' : '#1f7a5b',
              color: '#fff',
              border: 'none',
              borderRadius: '12px',
              padding: '12px 24px',
              fontSize: '14px',
              fontWeight: 600,
              cursor: !name.trim() || createDataset.isPending ? 'not-allowed' : 'pointer',
            }}
          >
            {createDataset.isPending
              ? t('datasets.creating', 'Creating...')
              : t('datasets.create_button', 'Create Dataset')}
          </button>
        </div>
      </form>
    </div>
  )
}
