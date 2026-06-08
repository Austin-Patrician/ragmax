from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Any


class IndexingProfileName(StrEnum):
    DEFAULT_PDF = "default_pdf"
    SECTION_PDF = "section_pdf"
    TABLE_REPORT = "table_report"
    SCANNED_PDF = "scanned_pdf"


class NodeGraphMode(StrEnum):
    FLAT = "flat"
    PARENT_CHILD = "parent_child"


@dataclass(frozen=True)
class IndexingProfile:
    name: IndexingProfileName
    description: str
    chunker: str
    chunk_size: int
    chunk_overlap: int
    node_graph_mode: NodeGraphMode = NodeGraphMode.FLAT
    supported_media_types: tuple[str, ...] = field(default_factory=tuple)
    text_collection: str = "ragmax_text_nodes"
    visual_collection: str = "ragmax_visual_nodes"
    options: dict[str, Any] = field(default_factory=dict)

    def with_overrides(
        self,
        *,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        option_overrides: dict[str, Any] | None = None,
    ) -> "IndexingProfile":
        options = dict(self.options)
        if option_overrides:
            options.update(option_overrides)
        return replace(
            self,
            chunk_size=chunk_size or self.chunk_size,
            chunk_overlap=chunk_overlap or self.chunk_overlap,
            options=options,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name.value,
            "description": self.description,
            "chunker": self.chunker,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "node_graph_mode": self.node_graph_mode.value,
            "supported_media_types": list(self.supported_media_types),
            "text_collection": self.text_collection,
            "visual_collection": self.visual_collection,
            "options": self.options,
        }

