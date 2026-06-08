from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class BlockType(StrEnum):
    TEXT = "text"
    HEADING = "heading"
    TABLE = "table"
    IMAGE = "image"
    OCR = "ocr"
    CODE = "code"
    LIST = "list"
    QUOTE = "quote"


@dataclass(frozen=True)
class ContentBlock:
    block_id: str
    source_id: str
    block_type: BlockType
    text: str
    page_no: int | None = None
    bbox: tuple[float, float, float, float] | None = None
    section_hint: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def normalized_text(self) -> str:
        return self.text.strip()

    @property
    def is_empty(self) -> bool:
        return not self.normalized_text

