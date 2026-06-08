/**
 * Experiment Comparison Page
 */

import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { evaluationApi, type Experiment } from '../../../api/evaluation';
import styles from './ExperimentComparison.module.css';

export const ExperimentComparison: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { t } = useTranslation();
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadExperiments(ids: string[]) {
    try {
      const promises = ids.map((id) => evaluationApi.getExperiment(id).catch(() => null));
      const results = await Promise.all(promises);
      setExperiments(results.filter((exp): exp is Experiment => exp !== null));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load experiments');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const ids = searchParams.get('ids')?.split(',') || [];
    void Promise.resolve().then(() => {
      if (ids.length > 0) {
        return loadExperiments(ids);
      }
      setLoading(false);
    });
  }, [searchParams]);

  const baseline = experiments[0];

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading experiments...</div>
      </div>
    );
  }

  if (error || !baseline) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>
          {error || 'No experiments to compare. Please select at least 2 experiments.'}
        </div>
        <button className={styles.backButton} onClick={() => (window.location.href = '/evaluation')}>
          <ArrowLeft size={16} />
          {t('evaluation.comparison.backToOverview', 'Back to Overview')}
        </button>
      </div>
    );
  }

  const candidates = experiments.slice(1);

  return (
    <div className={styles.container}>
      <button className={styles.backButton} onClick={() => (window.location.href = '/evaluation')}>
        <ArrowLeft size={16} />
        {t('evaluation.comparison.backToOverview', 'Back to Overview')}
      </button>

      <header className={styles.header}>
        <h1>{t('evaluation.comparison.title', 'Experiment Comparison')}</h1>
        <p className={styles.subtitle}>
          {t('evaluation.comparison.subtitle', 'Compare multiple experiments side by side')}
        </p>
      </header>

      {/* Comparison Table */}
      <div className={styles.comparisonTable}>
        <table>
          <thead>
            <tr>
              <th className={styles.metricColumn}>{t('evaluation.comparison.metric', 'Metric')}</th>
              <th className={styles.baselineColumn}>
                {baseline.name}
                <span className={styles.baselineBadge}>{t('evaluation.comparison.baseline', 'Baseline')}</span>
              </th>
              {candidates.map((exp) => (
                <th key={exp.id}>{exp.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <MetricRow
              label={t('evaluation.comparison.overallScore', 'Overall Score')}
              baseline={baseline.metrics_summary?.overall_score}
              candidates={candidates.map((exp) => exp.metrics_summary?.overall_score)}
              formatter={(val) => `${(val * 100).toFixed(1)}%`}
              higherIsBetter
            />
            <MetricRow
              label={t('evaluation.comparison.passRate', 'Pass Rate')}
              baseline={baseline.metrics_summary?.pass_rate}
              candidates={candidates.map((exp) => exp.metrics_summary?.pass_rate)}
              formatter={(val) => `${(val * 100).toFixed(1)}%`}
              higherIsBetter
            />
            <MetricRow
              label={t('evaluation.comparison.faithfulness', 'Faithfulness')}
              baseline={baseline.metrics_summary?.faithfulness}
              candidates={candidates.map((exp) => exp.metrics_summary?.faithfulness)}
              formatter={(val) => `${(val * 100).toFixed(1)}%`}
              higherIsBetter
            />
            <MetricRow
              label={t('evaluation.comparison.contextRecall', 'Context Recall')}
              baseline={baseline.metrics_summary?.context_recall}
              candidates={candidates.map((exp) => exp.metrics_summary?.context_recall)}
              formatter={(val) => `${(val * 100).toFixed(1)}%`}
              higherIsBetter
            />
            <MetricRow
              label={t('evaluation.comparison.contextPrecision', 'Context Precision')}
              baseline={baseline.metrics_summary?.context_precision}
              candidates={candidates.map((exp) => exp.metrics_summary?.context_precision)}
              formatter={(val) => `${(val * 100).toFixed(1)}%`}
              higherIsBetter
            />
            <MetricRow
              label={t('evaluation.comparison.p95Latency', 'P95 Latency')}
              baseline={baseline.metrics_summary?.e2e_latency_p95}
              candidates={candidates.map((exp) => exp.metrics_summary?.e2e_latency_p95)}
              formatter={(val) => `${Math.round(val)}ms`}
              higherIsBetter={false}
            />
          </tbody>
        </table>
      </div>

      {/* Recommendations */}
      <section className={styles.recommendations}>
        <h2>{t('evaluation.comparison.recommendations', 'Recommendations')}</h2>
        <div className={styles.recommendationCard}>
          <p>
            {t(
              'evaluation.comparison.analysisPlaceholder',
              'AI-powered analysis and recommendations will be available here.'
            )}
          </p>
        </div>
      </section>
    </div>
  );
};

// Metric Row Component
const MetricRow: React.FC<{
  label: string;
  baseline: number | undefined;
  candidates: (number | undefined)[];
  formatter: (val: number) => string;
  higherIsBetter: boolean;
}> = ({ label, baseline, candidates, formatter, higherIsBetter }) => {
  const calculateDelta = (value?: number) => {
    if (value === undefined || baseline === undefined || baseline === 0) return null;
    const delta = value - baseline;
    const deltaPercent = (delta / baseline) * 100;
    return { delta, deltaPercent };
  };

  const getDeltaIcon = (delta: number) => {
    if (Math.abs(delta) < 0.01) return <Minus size={16} className={styles.iconNeutral} />;
    const improved = higherIsBetter ? delta > 0 : delta < 0;
    return improved ? (
      <TrendingUp size={16} className={styles.iconImproved} />
    ) : (
      <TrendingDown size={16} className={styles.iconRegressed} />
    );
  };

  return (
    <tr>
      <td className={styles.metricLabel}>{label}</td>
      <td className={styles.baselineValue}>{baseline !== undefined ? formatter(baseline) : 'N/A'}</td>
      {candidates.map((candidate, idx) => {
        const deltaData = calculateDelta(candidate);
        return (
          <td key={idx} className={styles.candidateValue}>
            <div className={styles.valueWithDelta}>
              <span className={styles.value}>{candidate !== undefined ? formatter(candidate) : 'N/A'}</span>
              {deltaData && (
                <span className={styles.delta}>
                  {getDeltaIcon(deltaData.delta)}
                  {Math.abs(deltaData.deltaPercent).toFixed(1)}%
                </span>
              )}
            </div>
          </td>
        );
      })}
    </tr>
  );
};
