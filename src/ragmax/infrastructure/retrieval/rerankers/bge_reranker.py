"""BGE Cross-Encoder Reranker implementation."""

import asyncio
import math
from collections.abc import Callable, Sequence
from typing import Any

import anyio

from ragmax.application.retrieval.dtos import RerankedNode, RetrievedNode
from ragmax.core.exceptions import ConfigurationError, ExternalServiceError

CrossEncoderFactory = Callable[[str, str, int], Any]


class BGECrossEncoderReranker:
    """Cross-encoder reranker using BGE Reranker models.

    This implementation uses sentence-transformers CrossEncoder for precise
    relevance scoring by jointly encoding query-document pairs.
    """

    name = "bge_reranker"

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: str = "cpu",
        batch_size: int = 16,
        max_length: int = 512,
        cross_encoder_factory: CrossEncoderFactory | None = None,
    ) -> None:
        """Initialize BGE reranker.

        Args:
            model_name: HuggingFace model name (default: BAAI/bge-reranker-v2-m3)
            device: Device for inference ("cpu" or "cuda")
            batch_size: Batch size for inference
        """
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.max_length = max_length
        self._cross_encoder_factory = cross_encoder_factory or _default_cross_encoder_factory
        self._model: Any | None = None
        self._model_lock = asyncio.Lock()

    async def rerank(
        self,
        *,
        query: str,
        nodes: Sequence[RetrievedNode],
        top_k: int,
    ) -> tuple[RerankedNode, ...]:
        """Rerank nodes using cross-encoder.

        Args:
            query: Search query
            nodes: Retrieved nodes to rerank
            top_k: Number of top results to return

        Returns:
            Reranked nodes sorted by cross-encoder score
        """
        if top_k < 1 or not nodes:
            return ()

        # Prepare query-document pairs
        pairs = [(query, node.node.text) for node in nodes]

        model = await self._get_model()
        try:
            raw_scores = await anyio.to_thread.run_sync(self._predict, model, pairs)
        except Exception as exc:
            raise ExternalServiceError(f"BGE reranker inference failed: {exc}") from exc

        # Build reranked results
        scored_nodes: list[tuple[float, int, RetrievedNode]] = [
            (float(raw_scores[i]), i, node) for i, node in enumerate(nodes)
        ]

        # Sort by cross-encoder score (descending)
        scored_nodes.sort(key=lambda x: (-x[0], x[1]))

        # Build final results with ranks
        reranked: list[RerankedNode] = []
        for rank, (raw_score, original_idx, node) in enumerate(scored_nodes[:top_k], start=1):
            normalized_score = _sigmoid(raw_score)
            reranked.append(
                RerankedNode(
                    retrieved_node=node,
                    rank=rank,
                    rerank_score=normalized_score,
                    vector_score=node.score,
                    reason="cross_encoder_relevance",
                    metadata={
                        "model": self.model_name,
                        "device": self.device,
                        "original_rank": original_idx + 1,
                        "raw_score": raw_score,
                        "score_delta": normalized_score - node.score,
                    },
                )
            )

        return tuple(reranked)

    async def _get_model(self) -> Any:
        if self._model is not None:
            return self._model

        async with self._model_lock:
            if self._model is not None:
                return self._model
            try:
                self._model = await anyio.to_thread.run_sync(
                    self._cross_encoder_factory,
                    self.model_name,
                    self.device,
                    self.max_length,
                )
            except Exception as exc:
                raise ConfigurationError(f"BGE reranker model failed to load: {exc}") from exc
            return self._model

    def _predict(self, model: Any, pairs: list[tuple[str, str]]) -> list[float]:
        scores = model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
        )
        return [float(score) for score in scores]


def _default_cross_encoder_factory(model_name: str, device: str, max_length: int) -> Any:
    try:
        from sentence_transformers import CrossEncoder
    except ImportError as exc:
        raise ConfigurationError(
            "sentence-transformers is required for BGE reranker. "
            "Install it with: uv sync"
        ) from exc

    return CrossEncoder(model_name, device=device, max_length=max_length)


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)
