/**
 * Evaluation Overview Page
 */

import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { evaluationApi, type Dataset, type Experiment } from '../../../api/evaluation';
import styles from './EvaluationOverview.module.css';

export const EvaluationOverview: React.FC = () => {
  const { t } = useTranslation();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    try {
      const [datasetsData, experimentsData] = await Promise.all([
        evaluationApi.listDatasets(20),
        evaluationApi.listExperiments(undefined, 10),
      ]);
      setDatasets(datasetsData);
      setExperiments(experimentsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void Promise.resolve().then(() => loadData());
  }, []);

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading evaluation data...</div>
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
        <h1>{t('evaluation.title', 'RAG Evaluation')}</h1>
        <p className={styles.subtitle}>
          {t('evaluation.subtitle', 'Measure and improve your RAG system quality')}
        </p>
      </header>

      {/* Key Metrics Cards */}
      <section className={styles.metricsSection}>
        <h2>{t('evaluation.keyMetrics', 'Key Metrics')}</h2>
        <div className={styles.metricsGrid}>
          <MetricCard
            title={t('evaluation.totalDatasets', 'Total Datasets')}
            value={datasets.length}
            icon="📊"
          />
          <MetricCard
            title={t('evaluation.totalExperiments', 'Total Experiments')}
            value={experiments.length}
            icon="🧪"
          />
          <MetricCard
            title={t('evaluation.testCases', 'Test Cases')}
            value={datasets.reduce((sum, ds) => sum + (ds.test_case_count || 0), 0)}
            icon="📝"
          />
          <MetricCard
            title={t('evaluation.avgPassRate', 'Avg Pass Rate')}
            value={
              experiments.length > 0
                ? `${Math.round(
                    (experiments.reduce((sum, exp) => sum + (exp.metrics_summary?.pass_rate || 0), 0) /
                      experiments.length) *
                      100
                  )}%`
                : 'N/A'
            }
            icon="✅"
          />
        </div>
      </section>

      {/* Recent Datasets */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2>{t('evaluation.recentDatasets', 'Recent Datasets')}</h2>
          <button className={styles.primaryButton} onClick={() => (window.location.href = '/evaluation/datasets')}>
            {t('evaluation.manageDatasets', 'Manage Datasets')}
          </button>
        </div>

        {datasets.length === 0 ? (
          <div className={styles.emptyState}>
            <p>{t('evaluation.noDatasetsYet', 'No datasets yet. Create your first dataset to get started.')}</p>
            <button className={styles.primaryButton} onClick={() => (window.location.href = '/evaluation/datasets')}>
              {t('evaluation.createDataset', 'Create Dataset')}
            </button>
          </div>
        ) : (
          <div className={styles.datasetList}>
            {datasets.slice(0, 5).map((dataset) => (
              <DatasetCard key={dataset.id} dataset={dataset} />
            ))}
          </div>
        )}
      </section>

      {/* Recent Experiments */}
      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2>{t('evaluation.recentExperiments', 'Recent Experiments')}</h2>
          <button className={styles.primaryButton} onClick={() => alert('Run experiment - TODO')}>
            {t('evaluation.runExperiment', 'Run Experiment')}
          </button>
        </div>

        {experiments.length === 0 ? (
          <div className={styles.emptyState}>
            <p>{t('evaluation.noExperimentsYet', 'No experiments yet. Run your first evaluation.')}</p>
          </div>
        ) : (
          <div className={styles.experimentList}>
            {experiments.map((experiment) => (
              <ExperimentCard key={experiment.id} experiment={experiment} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
};

// Metric Card Component
const MetricCard: React.FC<{ title: string; value: string | number; icon: string }> = ({ title, value, icon }) => (
  <div className={styles.metricCard}>
    <div className={styles.metricIcon}>{icon}</div>
    <div className={styles.metricContent}>
      <div className={styles.metricValue}>{value}</div>
      <div className={styles.metricTitle}>{title}</div>
    </div>
  </div>
);

// Dataset Card Component
const DatasetCard: React.FC<{ dataset: Dataset }> = ({ dataset }) => (
  <div className={styles.card} onClick={() => (window.location.href = `/evaluation/datasets/${dataset.id}`)}>
    <div className={styles.cardHeader}>
      <h3>{dataset.name}</h3>
      <span className={styles.badge}>v{dataset.version}</span>
    </div>
    <p className={styles.cardDescription}>{dataset.description || 'No description'}</p>
    <div className={styles.cardFooter}>
      <span>{dataset.test_case_count || 0} test cases</span>
      <span>{new Date(dataset.created_at).toLocaleDateString()}</span>
    </div>
  </div>
);

// Experiment Card Component
const ExperimentCard: React.FC<{ experiment: Experiment }> = ({ experiment }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return '#10b981';
      case 'running':
        return '#3b82f6';
      case 'failed':
        return '#ef4444';
      default:
        return '#6b7280';
    }
  };

  return (
    <div className={styles.card} onClick={() => (window.location.href = `/evaluation/experiments/${experiment.id}`)}>
      <div className={styles.cardHeader}>
        <h3>{experiment.name}</h3>
        <span className={styles.statusBadge} style={{ backgroundColor: getStatusColor(experiment.status) }}>
          {experiment.status}
        </span>
      </div>
      {experiment.metrics_summary && (
        <div className={styles.experimentMetrics}>
          <div className={styles.miniMetric}>
            <span>Overall Score</span>
            <strong>{(experiment.metrics_summary.overall_score * 100).toFixed(0)}%</strong>
          </div>
          <div className={styles.miniMetric}>
            <span>Pass Rate</span>
            <strong>{(experiment.metrics_summary.pass_rate * 100).toFixed(0)}%</strong>
          </div>
          <div className={styles.miniMetric}>
            <span>P95 Latency</span>
            <strong>{Math.round(experiment.metrics_summary.e2e_latency_p95)}ms</strong>
          </div>
        </div>
      )}
      <div className={styles.cardFooter}>
        <span>{new Date(experiment.started_at).toLocaleString()}</span>
        {experiment.duration_seconds && <span>{experiment.duration_seconds.toFixed(1)}s</span>}
      </div>
    </div>
  );
};
