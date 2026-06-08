"""Tests for evaluation metrics."""

import pytest

from ragmax.evaluation.metrics.e2e import LatencyMetric
from ragmax.evaluation.metrics.retrieval import (
    ContextPrecisionMetric,
    ContextRecallMetric,
)
from ragmax.evaluation.models import (
    EvalTestCase,
    GenerationResult,
    RetrievalResult,
)


@pytest.fixture
def sample_test_case():
    """Sample test case for testing."""
    return EvalTestCase(
        id="test_001",
        question="What is the capital of France?",
        expected_answer="Paris",
        ground_truth_docs=["doc_001", "doc_002", "doc_003"],
        metadata={"difficulty": "easy"},
    )


@pytest.fixture
def sample_retrieval_result():
    """Sample retrieval result."""
    return RetrievalResult(
        retrieved_doc_ids=["doc_001", "doc_002", "doc_004", "doc_005"],
        scores=[0.95, 0.88, 0.75, 0.62],
        latency_ms=45.5,
    )


@pytest.fixture
def sample_generation_result():
    """Sample generation result."""
    return GenerationResult(
        answer="Paris is the capital of France.",
        citations=[1, 2],
        latency_ms=120.3,
        token_count=8,
    )


class TestContextPrecisionMetric:
    """Tests for ContextPrecisionMetric."""

    @pytest.mark.asyncio
    async def test_perfect_precision(self, sample_test_case):
        """Test when all retrieved documents are relevant."""
        metric = ContextPrecisionMetric()

        retrieval_result = RetrievalResult(
            retrieved_doc_ids=["doc_001", "doc_002", "doc_003"],
            scores=[0.95, 0.88, 0.75],
            latency_ms=45.5,
        )
        generation_result = GenerationResult("answer", [], 100.0, 10)

        score = await metric.compute(sample_test_case, retrieval_result, generation_result)
        assert score == 1.0

    @pytest.mark.asyncio
    async def test_partial_precision(self, sample_test_case, sample_retrieval_result, sample_generation_result):
        """Test when some retrieved documents are not relevant."""
        metric = ContextPrecisionMetric()

        score = await metric.compute(sample_test_case, sample_retrieval_result, sample_generation_result)
        # 2 out of 4 retrieved docs are in ground truth
        assert score == 0.5

    @pytest.mark.asyncio
    async def test_zero_precision(self, sample_test_case, sample_generation_result):
        """Test when no retrieved documents are relevant."""
        metric = ContextPrecisionMetric()

        retrieval_result = RetrievalResult(
            retrieved_doc_ids=["doc_999", "doc_998"],
            scores=[0.5, 0.4],
            latency_ms=45.5,
        )

        score = await metric.compute(sample_test_case, retrieval_result, sample_generation_result)
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_empty_retrieval(self, sample_test_case, sample_generation_result):
        """Test when no documents are retrieved."""
        metric = ContextPrecisionMetric()

        retrieval_result = RetrievalResult(
            retrieved_doc_ids=[],
            scores=[],
            latency_ms=45.5,
        )

        score = await metric.compute(sample_test_case, retrieval_result, sample_generation_result)
        assert score == 0.0


class TestContextRecallMetric:
    """Tests for ContextRecallMetric."""

    @pytest.mark.asyncio
    async def test_perfect_recall(self, sample_test_case, sample_generation_result):
        """Test when all relevant documents are retrieved."""
        metric = ContextRecallMetric()

        retrieval_result = RetrievalResult(
            retrieved_doc_ids=["doc_001", "doc_002", "doc_003", "doc_999"],
            scores=[0.95, 0.88, 0.75, 0.5],
            latency_ms=45.5,
        )

        score = await metric.compute(sample_test_case, retrieval_result, sample_generation_result)
        assert score == 1.0

    @pytest.mark.asyncio
    async def test_partial_recall(self, sample_test_case, sample_retrieval_result, sample_generation_result):
        """Test when some relevant documents are missing."""
        metric = ContextRecallMetric()

        score = await metric.compute(sample_test_case, sample_retrieval_result, sample_generation_result)
        # 2 out of 3 ground truth docs are retrieved
        assert score == pytest.approx(0.666, rel=0.01)

    @pytest.mark.asyncio
    async def test_zero_recall(self, sample_test_case, sample_generation_result):
        """Test when no relevant documents are retrieved."""
        metric = ContextRecallMetric()

        retrieval_result = RetrievalResult(
            retrieved_doc_ids=["doc_999", "doc_998"],
            scores=[0.5, 0.4],
            latency_ms=45.5,
        )

        score = await metric.compute(sample_test_case, retrieval_result, sample_generation_result)
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_no_ground_truth(self, sample_generation_result):
        """Test when no ground truth is provided."""
        metric = ContextRecallMetric()

        test_case = EvalTestCase(
            id="test_001",
            question="Question without ground truth",
            ground_truth_docs=[],
        )

        retrieval_result = RetrievalResult(
            retrieved_doc_ids=["doc_001"],
            scores=[0.9],
            latency_ms=45.5,
        )

        score = await metric.compute(test_case, retrieval_result, sample_generation_result)
        assert score == 1.0  # Cannot evaluate recall without ground truth


class TestLatencyMetric:
    """Tests for LatencyMetric."""

    @pytest.mark.asyncio
    async def test_under_target(self, sample_test_case):
        """Test when latency is under target."""
        metric = LatencyMetric(target_latency_ms=200.0)

        retrieval_result = RetrievalResult(["doc_001"], [0.9], 50.0)
        generation_result = GenerationResult("answer", [], 100.0, 10)

        score = await metric.compute(sample_test_case, retrieval_result, generation_result)
        assert score == 1.0

    @pytest.mark.asyncio
    async def test_at_target(self, sample_test_case):
        """Test when latency is exactly at target."""
        metric = LatencyMetric(target_latency_ms=200.0)

        retrieval_result = RetrievalResult(["doc_001"], [0.9], 100.0)
        generation_result = GenerationResult("answer", [], 100.0, 10)

        score = await metric.compute(sample_test_case, retrieval_result, generation_result)
        assert score == 1.0

    @pytest.mark.asyncio
    async def test_over_target(self, sample_test_case):
        """Test when latency is over target."""
        metric = LatencyMetric(target_latency_ms=100.0)

        retrieval_result = RetrievalResult(["doc_001"], [0.9], 100.0)
        generation_result = GenerationResult("answer", [], 100.0, 10)

        score = await metric.compute(sample_test_case, retrieval_result, generation_result)
        # Total = 200ms, target = 100ms, ratio = 2.0
        # Score should be around 0.5
        assert 0.4 < score < 0.6

    @pytest.mark.asyncio
    async def test_missing_results(self, sample_test_case):
        """Test when results are missing."""
        metric = LatencyMetric()

        score = await metric.compute(sample_test_case, None, None)
        assert score == 0.0
