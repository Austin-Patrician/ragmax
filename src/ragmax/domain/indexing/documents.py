from dataclasses import dataclass, field
from typing import Any

from ragmax.domain.indexing.blocks import ContentBlock


@dataclass(frozen=True)
class SourceDocument:
    source_id: str
    notebook_id: str
    filename: str
    media_type: str
    parser_name: str
    parser_version: str
    blocks: tuple[ContentBlock, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def page_count(self) -> int:
        pages = {block.page_no for block in self.blocks if block.page_no is not None}
        return len(pages) or 1

    @property
    def text_content(self) -> str:
        return "\n\n".join(block.normalized_text for block in self.blocks if block.normalized_text)

