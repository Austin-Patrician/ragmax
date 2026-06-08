from collections.abc import Mapping
from typing import Any

from ragmax.application.indexing.dtos import SourceInput, SourceInputBlock
from ragmax.core.exceptions import InvalidRequestError
from ragmax.domain.indexing.blocks import ContentBlock
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.infrastructure.indexing.parsers.block_parsing import (
    blocks_from_text,
    normalize_block_type,
)


class HeuristicSourceParser:
    parser_name = "inline_content_parser"
    parser_version = "v1"

    async def parse(
        self,
        source: SourceInput,
        options: Mapping[str, Any] | None = None,
    ) -> SourceDocument:
        if source.input_blocks:
            blocks = tuple(
                self._parse_block(source.source_id, block, index)
                for index, block in enumerate(source.input_blocks)
            )
        elif source.text and source.text.strip():
            blocks = tuple(self._parse_text(source.source_id, source.text))
        else:
            raise InvalidRequestError("Source content is empty. Provide text or blocks.")

        return SourceDocument(
            source_id=source.source_id,
            notebook_id=source.notebook_id,
            filename=source.filename,
            media_type=source.media_type,
            parser_name=self.parser_name,
            parser_version=self.parser_version,
            blocks=blocks,
            metadata=source.metadata,
        )

    def _parse_text(self, source_id: str, text: str) -> list[ContentBlock]:
        return blocks_from_text(source_id=source_id, text=text, page_no=1)

    def _parse_block(self, source_id: str, block: SourceInputBlock, index: int) -> ContentBlock:
        return ContentBlock(
            block_id=block.block_id or f"{source_id}:block:{index + 1}",
            source_id=source_id,
            block_type=normalize_block_type(block.block_type),
            text=block.text,
            page_no=block.page_no,
            bbox=block.bbox,
            section_hint=block.section_hint,
            metadata=block.metadata,
        )
