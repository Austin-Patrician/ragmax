import re
from collections.abc import Sequence

from ragmax.application.retrieval.dtos import RerankedNode, RetrievedNode

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


class ScoreKeywordReranker:
    name = "score_keyword_reranker:v1"

    def __init__(self, *, vector_weight: float = 0.75, keyword_weight: float = 0.25) -> None:
        total_weight = vector_weight + keyword_weight
        if total_weight <= 0:
            raise ValueError("Reranker weights must have a positive sum.")
        self._vector_weight = vector_weight / total_weight
        self._keyword_weight = keyword_weight / total_weight

    async def rerank(
        self,
        *,
        query: str,
        nodes: Sequence[RetrievedNode],
        top_k: int,
    ) -> tuple[RerankedNode, ...]:
        if top_k < 1:
            return ()

        query_terms = _tokenize(query)
        scored_nodes: list[tuple[float, int, RerankedNode]] = []
        for index, node in enumerate(nodes):
            keyword_score, matched_terms = _keyword_score(query_terms, node.node.text)
            rerank_score = (self._vector_weight * node.score) + (
                self._keyword_weight * keyword_score
            )
            scored_nodes.append(
                (
                    rerank_score,
                    index,
                    RerankedNode(
                        retrieved_node=node,
                        rank=0,
                        rerank_score=rerank_score,
                        vector_score=node.score,
                        reason="vector_score_plus_keyword_overlap",
                        metadata={
                            "keyword_score": keyword_score,
                            "matched_terms": sorted(matched_terms),
                            "vector_weight": self._vector_weight,
                            "keyword_weight": self._keyword_weight,
                        },
                    ),
                )
            )

        ranked: list[RerankedNode] = []
        for rank, (_, _, item) in enumerate(
            sorted(scored_nodes, key=lambda value: (-value[0], value[1]))[:top_k],
            start=1,
        ):
            ranked.append(
                RerankedNode(
                    retrieved_node=item.retrieved_node,
                    rank=rank,
                    rerank_score=item.rerank_score,
                    vector_score=item.vector_score,
                    reason=item.reason,
                    metadata=item.metadata,
                )
            )
        return tuple(ranked)


def _tokenize(text: str) -> frozenset[str]:
    return frozenset(match.group(0).lower() for match in _TOKEN_RE.finditer(text))


def _keyword_score(query_terms: frozenset[str], text: str) -> tuple[float, frozenset[str]]:
    if not query_terms:
        return 0.0, frozenset()
    text_terms = _tokenize(text)
    matched_terms = query_terms.intersection(text_terms)
    return len(matched_terms) / len(query_terms), frozenset(matched_terms)
