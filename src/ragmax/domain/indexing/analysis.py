from collections import Counter
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from ragmax.domain.indexing.blocks import ContentBlock
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.profiles import IndexingProfileName

if TYPE_CHECKING:
    from ragmax.domain.indexing.quality import ChunkQualityMetrics


@dataclass(frozen=True)
class SourceAnalysis:
    recommended_profile: IndexingProfileName
    reasons: tuple[str, ...]
    traits: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IndexingSummary:
    block_count: int
    node_count: int
    page_count: int
    block_types: dict[str, int]
    content_types: dict[str, int]
    modalities: dict[str, int]
    node_roles: dict[str, int]
    vectorized_count: int = 0
    chunk_length_stats: dict[str, int] = field(default_factory=dict)
    quality: dict[str, Any] = field(default_factory=dict)
    performance: dict[str, float] = field(default_factory=dict)
    quality_metrics: "ChunkQualityMetrics | None" = None

    @classmethod
    def from_nodes(
        cls,
        *,
        blocks: tuple[ContentBlock, ...],
        page_count: int,
        nodes: tuple[IndexNode, ...],
        vectorized_count: int = 0,
        performance: dict[str, float] | None = None,
        quality_metrics: "ChunkQualityMetrics | None" = None,
    ) -> "IndexingSummary":
        block_count = len(blocks)
        block_types = Counter(block.block_type.value for block in blocks)
        content_types = Counter(node.content_type for node in nodes)
        modalities = Counter(node.modality for node in nodes)
        node_roles = Counter(_node_role(node) for node in nodes)
        text_lengths = sorted(len(node.text) for node in nodes if node.text)
        page_number_blocks = sum(1 for block in blocks if block.page_no is not None)
        block_ids = {block.block_id for block in blocks}
        unresolved_block_ref_count = sum(
            1 for node in nodes for block_id in node.block_ids if block_id not in block_ids
        )
        return cls(
            block_count=block_count,
            node_count=len(nodes),
            page_count=page_count,
            block_types=dict(block_types),
            content_types=dict(content_types),
            modalities=dict(modalities),
            node_roles=dict(node_roles),
            vectorized_count=vectorized_count,
            chunk_length_stats=_length_stats(text_lengths),
            quality={
                "page_number_coverage": page_number_blocks / block_count
                if block_count
                else 0.0,
                "blocks_without_text": sum(1 for block in blocks if block.is_empty),
                "unresolved_block_ref_count": unresolved_block_ref_count,
            },
            performance=performance or {},
            quality_metrics=quality_metrics,
        )


def _node_role(node: IndexNode) -> str:
    if node.parent_node_id:
        return "child"
    if node.content_type == "section":
        return "parent"
    return "leaf"


def _length_stats(lengths: list[int]) -> dict[str, int]:
    if not lengths:
        return {"min": 0, "p50": 0, "p95": 0, "max": 0}

    return {
        "min": lengths[0],
        "p50": _percentile(lengths, 0.5),
        "p95": _percentile(lengths, 0.95),
        "max": lengths[-1],
    }


def _percentile(values: list[int], percentile: float) -> int:
    index = min(len(values) - 1, int(round((len(values) - 1) * percentile)))
    return values[index]

