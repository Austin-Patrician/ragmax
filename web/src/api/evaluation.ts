/**
 * Evaluation API client
 */

import { apiBaseUrl, authenticatedFetch, parseJsonResponse } from './client';

export interface TestCase {
  id: string;
  question: string;
  expected_answer?: string;
  ground_truth_docs: string[];
  metadata: Record<string, unknown>;
}

export interface Dataset {
  id: string;
  name: string;
  description: string;
  version: string;
  test_case_count?: number;
  test_cases?: TestCase[];
  created_at: string;
}

export interface MetricsSummary {
  context_precision: number;
  context_recall: number;
  faithfulness: number;
  answer_relevancy: number;
  overall_score: number;
  e2e_latency_p95: number;
  pass_rate: number;
  retrieval_latency_p95: number;
  avg_token_cost: number;
}

export interface Experiment {
  id: string;
  name: string;
  dataset_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  duration_seconds?: number;
  metrics_summary?: MetricsSummary;
  config: Record<string, unknown>;
}

export interface DatasetVersion {
  id: string;
  version: string;
  created_at: string;
}

export interface VersionComparison {
  added: number;
  removed: number;
  modified: number;
  unchanged: number;
  total_a: number;
  total_b: number;
}

export const evaluationApi = {
  // Dataset operations
  async listDatasets(limit = 100): Promise<Dataset[]> {
    const response = await requestJson<{ datasets: Dataset[] }>(
      `/api/v1/evaluation/datasets?limit=${limit}`
    );
    return response.datasets;
  },

  async getDataset(datasetId: string): Promise<Dataset> {
    return requestJson(`/api/v1/evaluation/datasets/${encodeURIComponent(datasetId)}`);
  },

  async createDataset(dataset: {
    name: string;
    description?: string;
    version?: string;
    test_cases: Partial<TestCase>[];
  }): Promise<{ id: string; message: string }> {
    return requestJson('/api/v1/evaluation/datasets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dataset),
    });
  },

  async deleteDataset(datasetId: string): Promise<{ message: string }> {
    return requestJson(`/api/v1/evaluation/datasets/${encodeURIComponent(datasetId)}`, {
      method: 'DELETE',
    });
  },

  // Experiment operations
  async listExperiments(datasetId?: string, limit = 50): Promise<Experiment[]> {
    const params = new URLSearchParams();
    if (datasetId) params.append('dataset_id', datasetId);
    params.append('limit', limit.toString());

    const response = await requestJson<{ experiments: Experiment[] }>(
      `/api/v1/evaluation/experiments?${params}`
    );
    return response.experiments;
  },

  async getExperiment(experimentId: string): Promise<Experiment | null> {
    const response = await requestJson<{ experiment: Experiment | null }>(
      `/api/v1/evaluation/experiments/${encodeURIComponent(experimentId)}`
    );
    return response.experiment;
  },

  async runExperiment(request: {
    dataset_id: string;
    name: string;
    config: Record<string, unknown>;
  }): Promise<{ message: string; status: string }> {
    return requestJson('/api/v1/evaluation/experiments/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
  },

  // Version management
  async listDatasetVersions(datasetName: string): Promise<DatasetVersion[]> {
    const response = await requestJson<{ versions: DatasetVersion[] }>(
      `/api/v1/evaluation/datasets/${encodeURIComponent(datasetName)}/versions`
    );
    return response.versions;
  },

  async compareDatasetVersions(
    datasetName: string,
    versionA: string,
    versionB: string
  ): Promise<VersionComparison> {
    const params = new URLSearchParams({
      version_a: versionA,
      version_b: versionB,
    });
    return requestJson(
      `/api/v1/evaluation/datasets/${encodeURIComponent(datasetName)}/compare?${params}`
    );
  },
};

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await authenticatedFetch(`${apiBaseUrl}${path}`, init);
  return parseJsonResponse<T>(response);
}
