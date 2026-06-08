export const queryKeys = {
  indexing: {
    profiles: ['indexing', 'profiles'] as const,
    parsers: ['indexing', 'parsers'] as const,
    artifacts: (jobId: string) => ['indexing', 'jobs', jobId, 'artifacts'] as const,
    emptyArtifacts: ['indexing', 'jobs', 'empty'] as const,
  },
  retrieval: {
    search: ['retrieval', 'search'] as const,
    answer: ['retrieval', 'answer'] as const,
  },
}
