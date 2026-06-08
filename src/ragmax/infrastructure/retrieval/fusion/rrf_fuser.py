"""Reciprocal Rank Fusion (RRF) implementation."""

from collections.abc import Sequence

from ragmax.application.retrieval.fusion_dtos import BM25SearchHit, FusedSearchHit
from ragmax.application.retrieval.ports import VectorSearchHit


class RRFFuser:
    """Reciprocal Rank Fusion for combining search results.

    RRF formula: score(d) = Σ 1 / (k + rank(d))

    This approach operates purely on rank positions, avoiding the need to
    normalize incompatible scores (BM25 integers vs. vector similarity floats).
    """

    def __init__(self, k: int = 60) -> None:
        """Initialize RRF fuser.

        Args:
            k: Dampening constant for RRF formula (default: 60)
        """
        self.k = k

    def fuse(
        self,
        *,
        vector_hits: Sequence[VectorSearchHit],
        bm25_hits: Sequence[BM25SearchHit],
        top_k: int,
    ) -> tuple[FusedSearchHit, ...]:
        """Fuse vector and BM25 search results using RRF.

        Args:
            vector_hits: Results from vector search
            bm25_hits: Results from BM25 search
            top_k: Number of top results to return

        Returns:
            Fused results sorted by RRF score (descending)
        """
        # Build rank maps (1-indexed)
        vector_ranks = {hit.node_id: i + 1 for i, hit in enumerate(vector_hits)}
        bm25_ranks = {hit.node_id: i + 1 for i, hit in enumerate(bm25_hits)}

        # Build score maps for metadata
        vector_hits_by_id = {hit.node_id: hit for hit in vector_hits}
        bm25_hits_by_id = {hit.node_id: hit for hit in bm25_hits}
        vector_scores = {node_id: hit.score for node_id, hit in vector_hits_by_id.items()}
        bm25_scores = {node_id: hit.score for node_id, hit in bm25_hits_by_id.items()}

        # Get all unique node_ids
        all_node_ids = set(vector_ranks.keys()) | set(bm25_ranks.keys())

        # Calculate RRF scores
        fused: list[tuple[float, str, FusedSearchHit]] = []
        for node_id in all_node_ids:
            vector_rank = vector_ranks.get(node_id)
            bm25_rank = bm25_ranks.get(node_id)
            vector_hit = vector_hits_by_id.get(node_id)
            bm25_hit = bm25_hits_by_id.get(node_id)

            # RRF score: sum of 1/(k + rank) for each retriever
            rrf_score = 0.0
            if vector_rank is not None:
                rrf_score += 1.0 / (self.k + vector_rank)
            if bm25_rank is not None:
                rrf_score += 1.0 / (self.k + bm25_rank)

            fused.append(
                (
                    rrf_score,
                    node_id,
                    FusedSearchHit(
                        node_id=node_id,
                        fused_score=rrf_score,
                        vector_score=vector_scores.get(node_id),
                        bm25_score=bm25_scores.get(node_id),
                        vector_rank=vector_rank,
                        bm25_rank=bm25_rank,
                        collection_name=(
                            vector_hit.collection_name
                            if vector_hit is not None
                            else bm25_hit.collection_name
                            if bm25_hit is not None
                            else ""
                        ),
                        matched_terms=bm25_hit.matched_terms if bm25_hit is not None else (),
                        payload={
                            "vector_payload": vector_hit.payload if vector_hit is not None else {},
                            "bm25_payload": bm25_hit.payload if bm25_hit is not None else {},
                        },
                    ),
                )
            )

        # Sort by RRF score (descending), then by node_id for stable sorting
        fused.sort(key=lambda x: (-x[0], x[1]))

        # Return top_k results
        return tuple(hit for _, _, hit in fused[:top_k])
