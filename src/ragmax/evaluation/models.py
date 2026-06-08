"""Data models for RAG evaluation platform."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EvalTestCase:
    """Single evaluation test case."""

    id: str
    question: str
    expected_answer: str | None = None
    ground_truth_docs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TestDataset:
    """Collection of test cases."""

    id: str
    name: str
    description: str
    test_cases: list[EvalTestCase]
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ExperimentConfig:
    """Experiment configuration (serializable to JSON)."""

    # Retrieval configuration
    embedding_model: str
    top_k: int = 10
    enable_bm25: bool = True
    enable_rerank: bool = True
    rerank_model: str | None = "BAAI/bge-reranker-v2-m3"
    rerank_top_n: int | None = 5
    fusion_strategy: str = "rrf"

    # Query Transform configuration
    query_strategy: str = "original"  # "original", "hyde", "multi_query"
    multi_query_llm: str | None = None

    # Generation configuration
    answer_llm: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 1000


@dataclass
class RetrievalResult:
    """Retrieval stage result."""

    retrieved_doc_ids: list[str]
    scores: list[float]
    latency_ms: float


@dataclass
class GenerationResult:
    """Generation stage result."""

    answer: str
    citations: list[int]
    latency_ms: float
    token_count: int


@dataclass
class EvalResult:
    """Evaluation result for a single test case."""

    test_case_id: str
    retrieval: RetrievalResult | None
    generation: GenerationResult | None
    metrics: dict[str, float]
    passed: bool
    error: str | None = None


@dataclass
class MetricsSummary:
    """Aggregated metrics summary."""

    # Retrieval layer
    context_precision: float
    context_recall: float

    # Generation layer
    faithfulness: float
    answer_relevancy: float

    # End-to-end
    overall_score: float
    e2e_latency_p95: float
    avg_token_cost: float
    pass_rate: float

    # Optional metrics
    mrr: float = 0.0
    ndcg_at_k: float = 0.0
    retrieval_latency_p95: float = 0.0
    correctness: float = 0.0
    citation_accuracy: float = 0.0
    hallucination_rate: float = 0.0


@dataclass
class ExperimentRun:
    """Single experiment run."""

    id: str
    name: str
    dataset_id: str
    config: ExperimentConfig
    results: list[EvalResult]
    metrics_summary: MetricsSummary | None
    status: str  # "running", "completed", "failed"
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float | None = None
