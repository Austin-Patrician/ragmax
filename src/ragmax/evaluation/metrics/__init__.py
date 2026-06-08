"""Base metric interface for evaluation."""

from abc import ABC, abstractmethod

from ragmax.evaluation.models import EvalTestCase, GenerationResult, RetrievalResult


class Metric(ABC):
    """Base class for all evaluation metrics."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Metric name."""
        pass

    @property
    @abstractmethod
    def requires_llm(self) -> bool:
        """Whether this metric requires LLM evaluation."""
        pass

    @property
    def threshold(self) -> float:
        """Pass/fail threshold (0-1 scale)."""
        return 0.7

    @abstractmethod
    async def compute(
        self,
        test_case: EvalTestCase,
        retrieval_result: RetrievalResult,
        generation_result: GenerationResult,
    ) -> float:
        """
        Compute metric score (0-1 scale).

        Args:
            test_case: Test case containing question and ground truth
            retrieval_result: Retrieval stage result
            generation_result: Generation stage result

        Returns:
            Score between 0.0 and 1.0
        """
        pass
