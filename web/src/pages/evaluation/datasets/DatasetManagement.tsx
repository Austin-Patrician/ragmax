/**
 * Dataset Management Page
 */

import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Upload, Sparkles, Trash2, Edit } from 'lucide-react';
import { evaluationApi, type Dataset } from '../../../api/evaluation';
import styles from './DatasetManagement.module.css';

export const DatasetManagement: React.FC = () => {
  const { t } = useTranslation();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  async function loadDatasets() {
    try {
      const data = await evaluationApi.listDatasets(100);
      setDatasets(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load datasets');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void Promise.resolve().then(() => loadDatasets());
  }, []);

  const handleDelete = async (datasetId: string) => {
    if (!confirm('Are you sure you want to delete this dataset?')) {
      return;
    }

    try {
      await evaluationApi.deleteDataset(datasetId);
      setDatasets(datasets.filter((ds) => ds.id !== datasetId));
    } catch (err) {
      alert('Failed to delete dataset: ' + (err instanceof Error ? err.message : 'Unknown error'));
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading datasets...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>Error: {error}</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1>{t('evaluation.datasets.title', 'Test Datasets')}</h1>
          <p className={styles.subtitle}>
            {t('evaluation.datasets.subtitle', 'Manage your evaluation test datasets')}
          </p>
        </div>
        <div className={styles.headerActions}>
          <button className={styles.secondaryButton} onClick={() => alert('Import JSON - TODO')}>
            <Upload size={16} />
            {t('evaluation.datasets.importJson', 'Import JSON')}
          </button>
          <button className={styles.primaryButton} onClick={() => setShowCreateModal(true)}>
            <Plus size={16} />
            {t('evaluation.datasets.createNew', 'Create Dataset')}
          </button>
        </div>
      </header>

      {datasets.length === 0 ? (
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>📊</div>
          <h2>{t('evaluation.datasets.noDatasets', 'No datasets yet')}</h2>
          <p>{t('evaluation.datasets.getStarted', 'Create your first test dataset to get started with evaluation.')}</p>
          <div className={styles.emptyActions}>
            <button className={styles.primaryButton} onClick={() => setShowCreateModal(true)}>
              <Plus size={16} />
              {t('evaluation.datasets.createNew', 'Create Dataset')}
            </button>
            <button className={styles.secondaryButton} onClick={() => alert('Import JSON - TODO')}>
              <Upload size={16} />
              {t('evaluation.datasets.importJson', 'Import JSON')}
            </button>
            <button className={styles.secondaryButton} onClick={() => alert('Generate Synthetic - TODO')}>
              <Sparkles size={16} />
              {t('evaluation.datasets.generateSynthetic', 'Generate Synthetic')}
            </button>
          </div>
        </div>
      ) : (
        <div className={styles.datasetGrid}>
          {datasets.map((dataset) => (
            <DatasetCard key={dataset.id} dataset={dataset} onDelete={handleDelete} />
          ))}
        </div>
      )}

      {showCreateModal && <CreateDatasetModal onClose={() => setShowCreateModal(false)} onCreated={loadDatasets} />}
    </div>
  );
};

// Dataset Card Component
const DatasetCard: React.FC<{
  dataset: Dataset;
  onDelete: (id: string) => void;
}> = ({ dataset, onDelete }) => {
  const { t } = useTranslation();

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <div>
          <h3>{dataset.name}</h3>
          <span className={styles.versionBadge}>v{dataset.version}</span>
        </div>
        <div className={styles.cardActions}>
          <button
            className={styles.iconButton}
            onClick={() => (window.location.href = `/evaluation/datasets/${dataset.id}`)}
            title="View details"
          >
            <Edit size={16} />
          </button>
          <button className={styles.iconButton} onClick={() => onDelete(dataset.id)} title="Delete">
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      <p className={styles.cardDescription}>{dataset.description || t('evaluation.datasets.noDescription', 'No description')}</p>

      <div className={styles.cardStats}>
        <div className={styles.stat}>
          <span className={styles.statLabel}>{t('evaluation.datasets.testCases', 'Test Cases')}</span>
          <span className={styles.statValue}>{dataset.test_case_count || 0}</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statLabel}>{t('evaluation.datasets.created', 'Created')}</span>
          <span className={styles.statValue}>{new Date(dataset.created_at).toLocaleDateString()}</span>
        </div>
      </div>

      <div className={styles.cardFooter}>
        <button
          className={styles.secondaryButton}
          onClick={() => (window.location.href = `/evaluation/datasets/${dataset.id}`)}
        >
          {t('evaluation.datasets.viewDetails', 'View Details')}
        </button>
      </div>
    </div>
  );
};

// Create Dataset Modal
const CreateDatasetModal: React.FC<{
  onClose: () => void;
  onCreated: () => void;
}> = ({ onClose, onCreated }) => {
  const { t } = useTranslation();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [version, setVersion] = useState('1.0.0');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      setError('Dataset name is required');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      await evaluationApi.createDataset({
        name: name.trim(),
        description: description.trim(),
        version: version.trim() || '1.0.0',
        test_cases: [],
      });

      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create dataset');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <h2>{t('evaluation.datasets.createNew', 'Create Dataset')}</h2>
          <button className={styles.closeButton} onClick={onClose}>
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className={styles.modalBody}>
          {error && <div className={styles.errorMessage}>{error}</div>}

          <div className={styles.formGroup}>
            <label htmlFor="name">{t('evaluation.datasets.name', 'Name')} *</label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Customer Support QA"
              required
              disabled={submitting}
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="description">{t('evaluation.datasets.description', 'Description')}</label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this dataset is for..."
              rows={3}
              disabled={submitting}
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="version">{t('evaluation.datasets.version', 'Version')}</label>
            <input
              id="version"
              type="text"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              placeholder="1.0.0"
              disabled={submitting}
            />
          </div>

          <div className={styles.modalFooter}>
            <button type="button" className={styles.secondaryButton} onClick={onClose} disabled={submitting}>
              {t('common.cancel', 'Cancel')}
            </button>
            <button type="submit" className={styles.primaryButton} disabled={submitting}>
              {submitting ? t('common.creating', 'Creating...') : t('common.create', 'Create')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
