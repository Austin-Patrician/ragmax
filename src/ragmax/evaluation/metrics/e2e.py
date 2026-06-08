"""End-to-end evaluation metrics."""

from ragmax.evaluation.metrics import Metric
from ragmax.evaluation.models import EvalTestCase, GenerationResult, RetrievalResult


class LatencyMetric(Metric):
    """
    End-to-End Latency: Total time from query to answer.

    Measures the sum of retrieval and generation latency.
    Normalized to 0-1 scale based on target latency.
    """

    def __init__(self, target_latency_ms: float = 2000.0):
        """
        Args:
            target_latency_ms: Target latency in milliseconds.
                Latencies below this get score 1.0, above get penalized.
        """
        self.target_latency_ms = target_latency_ms

    @property
    def name(self) -> str:
        return "e2e_latency"

    @property
    def requires_llm(self) -> bool:
        return False

    @property
    def threshold(self) -> float:
        return 0.7  # Allow 30% over target

    async def compute(
        self,
        test_case: EvalTestCase,
        retrieval_result: RetrievalResult,
        generation_result: GenerationResult,
    ) -> float:
        if not retrieval_result or not generation_result:
            return 0.0

        total_latency = retrieval_result.latency_ms + generation_result.latency_ms

        if total_latency <= self.target_latency_ms:
            return 1.0

        # Exponential decay for latencies over target
        # Score = exp(-ln(2) * (actual - target) / target)
        # At 2x target: score = 0.5
        # At 3x target: score = 0.25
        import math

        ratio = total_latency / self.target_latency_ms
        score = math.exp(-math.log(2) * (ratio - 1))
        return max(0.0, score)
