"""Evaluation platform for RAG system quality assessment."""

from ragmax.evaluation.evaluator import RAGEvaluator
from ragmax.evaluation.generator import SyntheticDataGenerator
from ragmax.evaluation.loader import DatasetLoader
from ragmax.evaluation.metrics import Metric
from ragmax.evaluation.metrics.e2e import LatencyMetric
from ragmax.evaluation.metrics.generation import AnswerRelevancyMetric, FaithfulnessMetric
from ragmax.evaluation.metrics.retrieval import ContextPrecisionMetric, ContextRecallMetric
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
from ragmax.evaluation.repository import EvaluationRepository

__all__ = [
    # Core evaluator
    "RAGEvaluator",
    # Data models
    "EvalTestCase",
    "ExperimentConfig",
    "ExperimentRun",
    "EvalResult",
    "GenerationResult",
    "MetricsSummary",
    "RetrievalResult",
    "TestDataset",
    # Repository
    "EvaluationRepository",
    # Loader and generator
    "DatasetLoader",
    "SyntheticDataGenerator",
    # Metrics
    "Metric",
    "ContextPrecisionMetric",
    "ContextRecallMetric",
    "FaithfulnessMetric",
    "AnswerRelevancyMetric",
    "LatencyMetric",
]
