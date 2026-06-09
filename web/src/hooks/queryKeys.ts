export const queryKeys = {
  indexing: {
    pipelineRuns: (sourceId: string) => ['indexing', 'sources', sourceId, 'runs'] as const,
    pipelineRun: (runId: string) => ['indexing', 'runs', runId] as const,
    stageArtifacts: (runId: string, stageName: string) =>
      ['indexing', 'runs', runId, 'stages', stageName, 'artifacts'] as const,
    artifactData: (artifactId: string, offset: number, limit: number) =>
      ['indexing', 'artifacts', artifactId, offset, limit] as const,
  },
  datasets: {
    list: () => ['datasets'] as const,
    detail: (datasetId: string) => ['datasets', datasetId] as const,
    files: (datasetId: string) => ['datasets', datasetId, 'files'] as const,
  },
  retrieval: {
    search: ['retrieval', 'search'] as const,
    answer: ['retrieval', 'answer'] as const,
  },
  userSettings: {
    profile: ['user-settings', 'profile'] as const,
    configuration: ['user-settings', 'configuration'] as const,
    modelProviders: ['user-settings', 'model-providers'] as const,
  },
}
