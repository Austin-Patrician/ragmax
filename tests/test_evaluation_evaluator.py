"""Tests for RAGEvaluator."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from ragmax.application.retrieval.dtos import (
    AnswerCitation,
    AnswerResult,
    RetrievalCitation,
    RetrievalContextItem,
)
from ragmax.evaluation.evaluator import RAGEvaluator
from ragmax.evaluation.metrics.e2e import LatencyMetric
from ragmax.evaluation.metrics.retrieval import (
    ContextPrecisionMetric,
    ContextRecallMetric,
)
from ragmax.evaluation.models import (
    EvalTestCase,
    ExperimentConfig,
    TestDataset,
)


@pytest.fixture
def mock_retrieval_service():
    """Mock RetrievalService."""
    service = Mock()
    service.answer = AsyncMock()
    return service


@pytest.fixture
def sample_dataset():
    """Sample test dataset."""
    return TestDataset(
        id="dataset_001",
        name="Test Dataset",
        description="A test dataset",
        test_cases=[
            EvalTestCase(
                id="tc_001",
                question="What is Python?",
                expected_answer="Python is a programming language.",
                ground_truth_docs=["doc_001", "doc_002"],
            ),
            EvalTestCase(
                id="tc_002",
                question="What is FastAPI?",
                expected_answer="FastAPI is a web framework.",
                ground_truth_docs=["doc_003"],
            ),
        ],
        version="1.0.0",
    )


@pytest.fixture
def sample_config():
    """Sample experiment configuration."""
    return ExperimentConfig(
        embedding_model="bge-large-zh-v1.5",
        top_k=10,
        enable_bm25=True,
        enable_rerank=True,
        query_strategy="original",
        answer_llm="gpt-4o-mini",
    )


@pytest.fixture
def basic_metrics():
    """Basic metrics for testing."""
    return [
        ContextPrecisionMetric(),
        ContextRecallMetric(),
        LatencyMetric(target_latency_ms=500.0),
    ]


class TestRAGEvaluator:
    """Tests for RAGEvaluator."""

    @pytest.mark.asyncio
    async def test_run_experiment_success(
        self,
        mock_retrieval_service,
        sample_dataset,
        sample_config,
        basic_metrics,
    ):
        """Test successful experiment run."""

        # Setup mock response
        mock_retrieval_service.answer.return_value = AnswerResult(
            query="test query",
            notebook_id="notebook_001",
            answer="Python is a programming language.",
            contexts=(
                RetrievalContextItem(
                    context_id="ctx_001",
                    citation_id="cite_001",
                    node_id="doc_001",
                    source_id="source_001",
                    notebook_id="notebook_001",
                    text="Python is a programming language.",
                    score=0.95,
                    vector_score=0.95,
                    rerank_score=0.95,
                    collection_name="test_collection",
                    content_type="text",
                    page_start=None,
                    page_end=None,
                    section_path=(),
                    citation=RetrievalCitation(
                        source_id="source_001",
                        node_id="doc_001",
                        filename=None,
                        page_label=None,
                        section_path=(),
                    ),
                ),
                RetrievalContextItem(
                    context_id="ctx_002",
                    citation_id="cite_002",
                    node_id="doc_002",
                    source_id="source_001",
                    notebook_id="notebook_001",
                    text="More about Python.",
                    score=0.88,
                    vector_score=0.88,
                    rerank_score=0.88,
                    collection_name="test_collection",
                    content_type="text",
                    page_start=None,
                    page_end=None,
                    section_path=(),
                    citation=RetrievalCitation(
                        source_id="source_001",
                        node_id="doc_002",
                        filename=None,
                        page_label=None,
                        section_path=(),
                    ),
                ),
            ),
            citations=(
                AnswerCitation(
                    citation_id="cite_001",
                    context_id="ctx_001",
                    citation=RetrievalCitation(
                        source_id="source_001",
                        node_id="doc_001",
                        filename=None,
                        page_label=None,
                        section_path=(),
                    ),
                ),
            ),
            retrieval_count=2,
            rerank_count=2,
            reranker_name="test_reranker",
            answer_generator_name="test_generator",
        )

        evaluator = RAGEvaluator(
            retrieval_service=mock_retrieval_service,
            metrics=basic_metrics,
        )

        experiment = await evaluator.run_experiment(
            dataset=sample_dataset,
            config=sample_config,
            name="Test Experiment",
        )

        # Assertions
        assert experiment.name == "Test Experiment"
        assert experiment.status == "completed"
        assert experiment.dataset_id == sample_dataset.id
        assert len(experiment.results) == 2
        assert experiment.metrics_summary is not None
        assert experiment.duration_seconds is not None
        assert experiment.duration_seconds > 0

        # Check that metrics were computed
        assert experiment.metrics_summary.context_precision >= 0.0
        assert experiment.metrics_summary.context_recall >= 0.0
        assert experiment.metrics_summary.overall_score >= 0.0

    @pytest.mark.asyncio
    async def test_run_experiment_with_failures(
        self,
        mock_retrieval_service,
        sample_dataset,
        sample_config,
        basic_metrics,
    ):
        """Test experiment with some test case failures."""

        # First call succeeds, second call fails
        mock_retrieval_service.answer.side_effect = [
            AnswerResult(
                query="test",
                notebook_id="notebook_001",
                answer="Answer",
                contexts=(
                    RetrievalContextItem(
                        context_id="ctx_001",
                        citation_id="cite_001",
                        node_id="doc_001",
                        source_id="source_001",
                        notebook_id="notebook_001",
                        text="Answer",
                        score=0.95,
                        vector_score=0.95,
                        rerank_score=0.95,
                        collection_name="test",
                        content_type="text",
                        page_start=None,
                        page_end=None,
                        section_path=(),
                        citation=RetrievalCitation(
                            source_id="source_001",
                            node_id="doc_001",
                            filename=None,
                            page_label=None,
                            section_path=(),
                        ),
                    ),
                ),
                citations=(),
                retrieval_count=1,
                rerank_count=1,
                reranker_name="test",
                answer_generator_name="test",
            ),
            Exception("Retrieval failed"),
        ]

        evaluator = RAGEvaluator(
            retrieval_service=mock_retrieval_service,
            metrics=basic_metrics,
        )

        experiment = await evaluator.run_experiment(
            dataset=sample_dataset,
            config=sample_config,
        )

        # Should have 2 results, but one with error
        assert len(experiment.results) == 2
        assert experiment.status == "completed"

        # One result should have error
        errors = [r for r in experiment.results if r.error is not None]
        assert len(errors) == 1
        assert "Retrieval failed" in errors[0].error

    @pytest.mark.asyncio
    async def test_metrics_computation(
        self,
        mock_retrieval_service,
        basic_metrics,
    ):
        """Test that metrics are computed correctly."""

        mock_retrieval_service.answer.return_value = AnswerResult(
            query="test query",
            notebook_id="notebook_001",
            answer="Answer text",
            contexts=(
                RetrievalContextItem(
                    context_id="ctx_001",
                    citation_id="cite_001",
                    node_id="doc_001",
                    source_id="source_001",
                    notebook_id="notebook_001",
                    text="Answer text",
                    score=0.95,
                    vector_score=0.95,
                    rerank_score=0.95,
                    collection_name="test",
                    content_type="text",
                    page_start=None,
                    page_end=None,
                    section_path=(),
                    citation=RetrievalCitation(
                        source_id="source_001",
                        node_id="doc_001",
                        filename=None,
                        page_label=None,
                        section_path=(),
                    ),
                ),
            ),
            citations=(),
            retrieval_count=1,
            rerank_count=1,
            reranker_name="test",
            answer_generator_name="test",
        )

        evaluator = RAGEvaluator(
            retrieval_service=mock_retrieval_service,
            metrics=basic_metrics,
        )

        dataset = TestDataset(
            id="dataset_001",
            name="Test",
            description="Test",
            test_cases=[
                EvalTestCase(
                    id="tc_001",
                    question="Question?",
                    ground_truth_docs=["doc_001"],
                ),
            ],
        )

        config = ExperimentConfig(embedding_model="test")

        experiment = await evaluator.run_experiment(dataset, config)

        # Check that all metrics were computed
        result = experiment.results[0]
        assert "context_precision" in result.metrics
        assert "context_recall" in result.metrics
        assert "e2e_latency" in result.metrics

        # Perfect precision and recall since doc_001 is in ground truth
        assert result.metrics["context_precision"] == 1.0
        assert result.metrics["context_recall"] == 1.0

    @pytest.mark.asyncio
    async def test_summary_statistics(
        self,
        mock_retrieval_service,
        sample_dataset,
        sample_config,
        basic_metrics,
    ):
        """Test summary statistics computation."""

        mock_retrieval_service.answer.return_value = AnswerResult(
            query="test query",
            notebook_id="notebook_001",
            answer="Answer",
            contexts=(
                RetrievalContextItem(
                    context_id="ctx_001",
                    citation_id="cite_001",
                    node_id="doc_001",
                    source_id="source_001",
                    notebook_id="notebook_001",
                    text="Answer",
                    score=0.95,
                    vector_score=0.95,
                    rerank_score=0.95,
                    collection_name="test",
                    content_type="text",
                    page_start=None,
                    page_end=None,
                    section_path=(),
                    citation=RetrievalCitation(
                        source_id="source_001",
                        node_id="doc_001",
                        filename=None,
                        page_label=None,
                        section_path=(),
                    ),
                ),
            ),
            citations=(),
            retrieval_count=1,
            rerank_count=1,
            reranker_name="test",
            answer_generator_name="test",
        )

        evaluator = RAGEvaluator(
            retrieval_service=mock_retrieval_service,
            metrics=basic_metrics,
        )

        experiment = await evaluator.run_experiment(
            dataset=sample_dataset,
            config=sample_config,
        )

        summary = experiment.metrics_summary

        # Check summary fields
        assert summary.overall_score >= 0.0
        assert summary.overall_score <= 1.0
        assert summary.pass_rate >= 0.0
        assert summary.pass_rate <= 1.0
        assert summary.e2e_latency_p95 >= 0.0
        assert summary.retrieval_latency_p95 >= 0.0
