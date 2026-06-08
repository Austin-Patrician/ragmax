/**
 * Experiment Detail Page
 */

import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Clock, CheckCircle, XCircle } from 'lucide-react';
import { evaluationApi, type Experiment } from '../../../api/evaluation';
import styles from './ExperimentDetail.module.css';

export const ExperimentDetail: React.FC = () => {
  const { experimentId } = useParams<{ experimentId: string }>();
  const { t } = useTranslation();
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadExperiment(id: string) {
    try {
      const data = await evaluationApi.getExperiment(id);
      setExperiment(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load experiment');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (experimentId) {
      void Promise.resolve().then(() => loadExperiment(experimentId));
    }
  }, [experimentId]);

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading experiment...</div>
      </div>
    );
  }

  if (error || !experiment) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>Error: {error || 'Experiment not found'}</div>
        <button className={styles.backButton} onClick={() => (window.location.href = '/evaluation')}>
          <ArrowLeft size={16} />
          {t('common.back', 'Back to Evaluation')}
        </button>
      </div>
    );
  }

  const metrics = experiment.metrics_summary;

  return (
    <div className={styles.container}>
      <button className={styles.backButton} onClick={() => (window.location.href = '/evaluation')}>
        <ArrowLeft size={16} />
        {t('evaluation.experiments.backToOverview', 'Back to Overview')}
      </button>

      <header className={styles.header}>
        <div>
          <h1>{experiment.name}</h1>
          <div className={styles.meta}>
            <span className={getStatusBadgeClass(experiment.status)}>{experiment.status}</span>
            <span className={styles.metaItem}>
              <Clock size={14} />
              {new Date(experiment.started_at).toLocaleString()}
            </span>
            {experiment.duration_seconds && (
              <span className={styles.metaItem}>Duration: {experiment.duration_seconds.toFixed(1)}s</span>
            )}
          </div>
        </div>
      </header>

      {metrics && (
        <>
          {/* Key Metrics Cards */}
          <section className={styles.metricsSection}>
            <h2>{t('evaluation.experiments.keyMetrics', 'Key Metrics')}</h2>
            <div className={styles.metricsGrid}>
              <MetricCard
                title={t('evaluation.experiments.overallScore', 'Overall Score')}
                value={`${(metrics.overall_score * 100).toFixed(1)}%`}
                status={metrics.overall_score >= 0.8 ? 'good' : metrics.overall_score >= 0.6 ? 'warning' : 'bad'}
              />
              <MetricCard
                title={t('evaluation.experiments.passRate', 'Pass Rate')}
                value={`${(metrics.pass_rate * 100).toFixed(1)}%`}
                status={metrics.pass_rate >= 0.9 ? 'good' : metrics.pass_rate >= 0.7 ? 'warning' : 'bad'}
              />
              <MetricCard
                title={t('evaluation.experiments.faithfulness', 'Faithfulness')}
                value={`${(metrics.faithfulness * 100).toFixed(1)}%`}
                status={metrics.faithfulness >= 0.95 ? 'good' : metrics.faithfulness >= 0.85 ? 'warning' : 'bad'}
              />
              <MetricCard
                title={t('evaluation.experiments.contextRecall', 'Context Recall')}
                value={`${(metrics.context_recall * 100).toFixed(1)}%`}
                status={metrics.context_recall >= 0.9 ? 'good' : metrics.context_recall >= 0.75 ? 'warning' : 'bad'}
              />
              <MetricCard
                title={t('evaluation.experiments.contextPrecision', 'Context Precision')}
                value={`${(metrics.context_precision * 100).toFixed(1)}%`}
                status={metrics.context_precision >= 0.8 ? 'good' : metrics.context_precision >= 0.6 ? 'warning' : 'bad'}
              />
              <MetricCard
                title={t('evaluation.experiments.p95Latency', 'P95 Latency')}
                value={`${Math.round(metrics.e2e_latency_p95)}ms`}
                status={metrics.e2e_latency_p95 <= 2000 ? 'good' : metrics.e2e_latency_p95 <= 5000 ? 'warning' : 'bad'}
              />
            </div>
          </section>

          {/* Configuration */}
          <section className={styles.section}>
            <h2>{t('evaluation.experiments.configuration', 'Configuration')}</h2>
            <div className={styles.configCard}>
              <pre>{JSON.stringify(experiment.config, null, 2)}</pre>
            </div>
          </section>
        </>
      )}

      {/* Placeholder for test results */}
      <section className={styles.section}>
        <h2>{t('evaluation.experiments.testResults', 'Test Results')}</h2>
        <div className={styles.placeholder}>
          <p>{t('evaluation.experiments.resultsNotAvailable', 'Detailed test results are not yet available.')}</p>
          <p className={styles.note}>
            {t('evaluation.experiments.implementationNote', 'This feature requires additional backend implementation.')}
          </p>
        </div>
      </section>
    </div>
  );
};

const getStatusBadgeClass = (status: string): string => {
  const baseClass = 'statusBadge';
  switch (status) {
    case 'completed':
      return `${baseClass} ${baseClass}Completed`;
    case 'running':
      return `${baseClass} ${baseClass}Running`;
    case 'failed':
      return `${baseClass} ${baseClass}Failed`;
    default:
      return `${baseClass} ${baseClass}Pending`;
  }
};

// Metric Card Component
const MetricCard: React.FC<{
  title: string;
  value: string;
  status: 'good' | 'warning' | 'bad';
}> = ({ title, value, status }) => {
  const getIcon = () => {
    if (status === 'good') return <CheckCircle size={20} className={styles.iconGood} />;
    if (status === 'bad') return <XCircle size={20} className={styles.iconBad} />;
    return <Clock size={20} className={styles.iconWarning} />;
  };

  return (
    <div className={`${styles.metricCard} ${styles[`metricCard${status.charAt(0).toUpperCase() + status.slice(1)}`]}`}>
      <div className={styles.metricHeader}>
        {getIcon()}
        <span className={styles.metricTitle}>{title}</span>
      </div>
      <div className={styles.metricValue}>{value}</div>
    </div>
  );
};
