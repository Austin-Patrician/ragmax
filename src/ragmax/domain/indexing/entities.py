from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class IndexNode:
    node_id: str
    source_id: str
    notebook_id: str
    text: str
    modality: str
    content_type: str
    page_start: int | None = None
    page_end: int | None = None
    section_path: tuple[str, ...] = field(default_factory=tuple)
    block_ids: tuple[str, ...] = field(default_factory=tuple)
    parent_node_id: str | None = None
    asset_path: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    indexing_profile: str | None = None
    parser_version: str | None = None
    chunker_version: str | None = None
    embedding_model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
