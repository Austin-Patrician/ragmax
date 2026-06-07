import re
from collections.abc import Mapping
from typing import Any

from ragmax.core.exceptions import InvalidRequestError
from ragmax.domain.indexing.blocks import BlockType, ContentBlock


def blocks_from_text(
    *,
    source_id: str,
    text: str,
    start_index: int = 1,
    page_no: int | None = 1,
    metadata: Mapping[str, Any] | None = None,
) -> list[ContentBlock]:
    segments = [segment.strip() for segment in re.split(r"\n\s*\n", text) if segment.strip()]
    blocks: list[ContentBlock] = []
    for offset, segment in enumerate(segments):
        block_index = start_index + offset
        blocks.append(
            ContentBlock(
                block_id=f"{source_id}:block:{block_index}",
                source_id=source_id,
                block_type=infer_block_type(segment),
                text=segment,
                page_no=page_no,
                metadata=dict(metadata or {}),
            )
        )
    return blocks


def normalize_block_type(block_type: str) -> BlockType:
    normalized = block_type.lower()
    try:
        return BlockType(normalized)
    except ValueError as exc:
        raise InvalidRequestError(f"Unsupported block type: {block_type}") from exc


def infer_block_type(text: str) -> BlockType:
    stripped_text = text.strip()
    lines = [line.strip() for line in stripped_text.splitlines() if line.strip()]

    if looks_like_table(lines):
        return BlockType.TABLE
    if looks_like_heading(stripped_text):
        return BlockType.HEADING
    return BlockType.TEXT


def looks_like_heading(text: str) -> bool:
    if text.startswith("#"):
        return True
    if re.match(r"^(\d+(?:\.\d+)*)\s+\S+", text):
        return True
    if re.match(r"^第[一二三四五六七八九十百零\d]+[章节部分篇]\s*\S*", text):
        return True

    if len(text) > 80 or "\n" in text:
        return False

    has_terminal_punctuation = bool(re.search(r"[。.!?;:：；]$", text))
    word_count = len(text.split())
    return not has_terminal_punctuation and word_count <= 10


def looks_like_table(lines: list[str]) -> bool:
    if len(lines) < 2:
        return False
    pipe_lines = sum(1 for line in lines if "|" in line)
    tab_lines = sum(1 for line in lines if "\t" in line)
    html_table_lines = sum(1 for line in lines if "<table" in line.lower() or "<tr" in line.lower())
    return pipe_lines >= 2 or tab_lines >= 2 or html_table_lines >= 1
