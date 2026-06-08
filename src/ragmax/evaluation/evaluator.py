"""Core RAG evaluation engine."""

import asyncio
import time
import uuid
from collections import defaultdict
from datetime import datetime

import numpy as np

from ragmax.application.retrieval.service import RetrievalCommand, RetrievalService
from ragmax.evaluation.metrics import Metric
from ragmax.evaluation.models import (
    EvalResult,
    EvalTestCase,
    ExperimentConfig,
    ExperimentRun,
    GenerationResult,
    MetricsSummary,
    RetrievalResult,
    TestDataset,
)
from ragmax.infrastructure.llm.client import LLMClient


class RAGEvaluator:
    """
    RAG system evaluator.

    Runs experiments by executing test cases against a RetrievalService
    with a specific configuration, computes metrics, and generates summaries.
    """

    def __init__(
        self,
        retrieval_service: RetrievalService,
        metrics: list[Metric],
        llm_client: LLMClient | None = None,
    ):
        """
        Args:
            retrieval_service: RetrievalService to evaluate
            metrics: List of metrics to compute
            llm_client: LLM client for answer generation (optional)
        """
        self.retrieval_service = retrieval_service
        self.metrics = metrics
        self.llm = llm_client

    async def run_experiment(
        self,
        dataset: TestDataset,
        config: ExperimentConfig,
        name: str | None = None,
    ) -> ExperimentRun:
        """
        Run a complete evaluation experiment.

        Args:
            dataset: Test dataset containing test cases
            config: Experiment configuration
            name: Optional experiment name

        Returns:
            ExperimentRun with results and metrics summary
        """

        # 1. Create experiment record
        experiment = ExperimentRun(
            id=str(uuid.uuid4()),
            name=name or f"experiment_{datetime.now().isoformat()}",
            dataset_id=dataset.id,
            config=config,
            results=[],
            metrics_summary=None,
            status="running",
            started_at=datetime.now(),
        )

        # 2. Apply configuration (TODO: actual config application)
        # self._apply_config(config)

        # 3. Execute all test cases concurrently
        tasks = [self._evaluate_test_case(test_case) for test_case in dataset.test_cases]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 4. Filter out exceptions and collect successful results
        experiment.results = [r for r in results if isinstance(r, EvalResult)]

        # 5. Compute summary metrics
        experiment.metrics_summary = self._compute_summary(experiment.results)

        # 6. Update status
        experiment.status = "completed"
        experiment.completed_at = datetime.now()
        experiment.duration_seconds = (experiment.completed_at - experiment.started_at).total_seconds()

        return experiment

    async def _evaluate_test_case(self, test_case: EvalTestCase) -> EvalResult:
        """
        Evaluate a single test case.

        Args:
            test_case: Test case to evaluate

        Returns:
            EvalResult with metrics scores
        """

        try:
            # 1. Execute retrieval + generation pipeline
            retrieval_result, generation_result = await self._run_rag_pipeline(test_case.question)

            # 2. Compute all metrics
            metrics_scores = {}
            for metric in self.metrics:
                score = await metric.compute(test_case, retrieval_result, generation_result)
                metrics_scores[metric.name] = score

            # 3. Determine pass/fail
            passed = all(score >= metric.threshold for metric, score in zip(self.metrics, metrics_scores.values()))

            return EvalResult(
                test_case_id=test_case.id,
                retrieval=retrieval_result,
                generation=generation_result,
                metrics=metrics_scores,
                passed=passed,
                error=None,
            )

        except Exception as e:
            return EvalResult(
                test_case_id=test_case.id,
                retrieval=None,
                generation=None,
                metrics={},
                passed=False,
                error=str(e),
            )

    async def _run_rag_pipeline(self, question: str) -> tuple[RetrievalResult, GenerationResult]:
        """
        Execute the RAG pipeline for a question.

        Args:
            question: User question

        Returns:
            Tuple of (RetrievalResult, GenerationResult)
        """

        # Measure retrieval time
        retrieval_start = time.time()

        from ragmax.application.retrieval.dtos import AnswerCommand

        command = AnswerCommand(query=question, notebook_id="eval", retrieval_top_k=10)

        response = await self.retrieval_service.answer(command)

        retrieval_latency = (time.time() - retrieval_start) * 1000  # Convert to ms

        # Extract document IDs (node IDs) and scores from contexts
        doc_ids = [ctx.node_id for ctx in response.contexts]
        scores = [ctx.score for ctx in response.contexts]

        retrieval_result = RetrievalResult(retrieved_doc_ids=doc_ids, scores=scores, latency_ms=retrieval_latency)

        # Generation is included in the same call, so generation latency is minimal
        generation_latency = 0.0  # Already included in retrieval_latency

        # Extract citations as list of citation IDs
        citations = [int(cite.citation_id.split("_")[-1]) if "_" in cite.citation_id else 0 for cite in response.citations]

        generation_result = GenerationResult(
            answer=response.answer, citations=citations, latency_ms=generation_latency, token_count=len(response.answer.split())
        )

        return retrieval_result, generation_result

    def _compute_summary(self, results: list[EvalResult]) -> MetricsSummary:
        """
        Compute aggregated metrics summary from individual results.

        Args:
            results: List of evaluation results

        Returns:
            MetricsSummary with averaged metrics
        """

        if not results:
            # Return zero summary if no results
            return MetricsSummary(
                context_precision=0.0,
                context_recall=0.0,
                faithfulness=0.0,
                answer_relevancy=0.0,
                overall_score=0.0,
                e2e_latency_p95=0.0,
                avg_token_cost=0.0,
                pass_rate=0.0,
            )

        # Aggregate metrics by name
        metric_values = defaultdict(list)
        for result in results:
            if result.error:
                continue
            for name, score in result.metrics.items():
                metric_values[name].append(score)

        # Compute averages
        avg_metrics = {name: sum(scores) / len(scores) if scores else 0.0 for name, scores in metric_values.items()}

        # Compute latency percentiles
        retrieval_latencies = [r.retrieval.latency_ms for r in results if r.retrieval]
        e2e_latencies = [
            r.retrieval.latency_ms + r.generation.latency_ms for r in results if r.retrieval and r.generation
        ]

        retrieval_p95 = float(np.percentile(retrieval_latencies, 95)) if retrieval_latencies else 0.0
        e2e_p95 = float(np.percentile(e2e_latencies, 95)) if e2e_latencies else 0.0

        # Compute token cost (simplified)
        total_tokens = sum(r.generation.token_count for r in results if r.generation)
        avg_tokens = total_tokens / len(results) if results else 0
        avg_cost = avg_tokens * 0.00001  # Rough estimate: $0.01 per 1000 tokens

        # Compute pass rate
        pass_rate = sum(r.passed for r in results) / len(results) if results else 0.0

        # Overall score: weighted average of all metrics
        overall_score = sum(avg_metrics.values()) / len(avg_metrics) if avg_metrics else 0.0

        return MetricsSummary(
            context_precision=avg_metrics.get("context_precision", 0.0),
            context_recall=avg_metrics.get("context_recall", 0.0),
            mrr=avg_metrics.get("mrr", 0.0),
            ndcg_at_k=avg_metrics.get("ndcg_at_k", 0.0),
            retrieval_latency_p95=retrieval_p95,
            faithfulness=avg_metrics.get("faithfulness", 0.0),
            answer_relevancy=avg_metrics.get("answer_relevancy", 0.0),
            correctness=avg_metrics.get("correctness", 0.0),
            citation_accuracy=avg_metrics.get("citation_accuracy", 0.0),
            hallucination_rate=avg_metrics.get("hallucination_rate", 0.0),
            overall_score=overall_score,
            e2e_latency_p95=e2e_p95,
            avg_token_cost=avg_cost,
            pass_rate=pass_rate,
        )
