"""Retrieval-layer evaluation metrics."""

from ragmax.evaluation.metrics import Metric
from ragmax.evaluation.models import EvalTestCase, GenerationResult, RetrievalResult


class ContextPrecisionMetric(Metric):
    """
    Context Precision: Proportion of retrieved documents that are relevant.

    Formula: |relevant ∩ retrieved| / |retrieved|

    Measures retrieval precision - how many of the retrieved documents
    are actually relevant to answering the question.
    """

    @property
    def name(self) -> str:
        return "context_precision"

    @property
    def requires_llm(self) -> bool:
        return False

    @property
    def threshold(self) -> float:
        return 0.8

    async def compute(
        self,
        test_case: EvalTestCase,
        retrieval_result: RetrievalResult,
        generation_result: GenerationResult,
    ) -> float:
        if not retrieval_result or not retrieval_result.retrieved_doc_ids:
            return 0.0

        ground_truth_set = set(test_case.ground_truth_docs)
        retrieved_set = set(retrieval_result.retrieved_doc_ids)

        if not retrieved_set:
            return 0.0

        relevant_retrieved = ground_truth_set & retrieved_set
        return len(relevant_retrieved) / len(retrieved_set)


class ContextRecallMetric(Metric):
    """
    Context Recall: Proportion of relevant documents that were retrieved.

    Formula: |relevant ∩ retrieved| / |relevant|

    Measures retrieval recall - how many of the relevant documents
    were successfully retrieved from the knowledge base.
    """

    @property
    def name(self) -> str:
        return "context_recall"

    @property
    def requires_llm(self) -> bool:
        return False

    @property
    def threshold(self) -> float:
        return 0.9

    async def compute(
        self,
        test_case: EvalTestCase,
        retrieval_result: RetrievalResult,
        generation_result: GenerationResult,
    ) -> float:
        if not retrieval_result:
            return 0.0

        ground_truth_set = set(test_case.ground_truth_docs)
        retrieved_set = set(retrieval_result.retrieved_doc_ids)

        if not ground_truth_set:
            # No ground truth provided, cannot evaluate recall
            return 1.0

        relevant_retrieved = ground_truth_set & retrieved_set
        return len(relevant_retrieved) / len(ground_truth_set)
