from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.profiles import IndexingProfileName


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
    content_types: dict[str, int]
    modalities: dict[str, int]

    @classmethod
    def from_nodes(
        cls,
        *,
        block_count: int,
        page_count: int,
        nodes: tuple[IndexNode, ...],
    ) -> "IndexingSummary":
        content_types = Counter(node.content_type for node in nodes)
        modalities = Counter(node.modality for node in nodes)
        return cls(
            block_count=block_count,
            node_count=len(nodes),
            page_count=page_count,
            content_types=dict(content_types),
            modalities=dict(modalities),
        )

