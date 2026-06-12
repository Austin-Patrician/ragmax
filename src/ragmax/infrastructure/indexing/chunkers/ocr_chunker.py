from ragmax.domain.indexing.blocks import BlockType, ContentBlock
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.entities import IndexNode
from typing import Any
from ragmax.domain.indexing.tokenization import Tokenizer
from ragmax.infrastructure.indexing.chunkers.base import BaseChunker


class OcrPageChunker(BaseChunker):
    def chunk(
        self, document: SourceDocument, config: dict[str, Any], tokenizer: Tokenizer
    ) -> list[IndexNode]:
        nodes: list[IndexNode] = []
        page_groups: dict[int, list[ContentBlock]] = {}

        for block in document.blocks:
            if block.block_type not in {BlockType.OCR, BlockType.TEXT} or block.is_empty:
                continue
            page_no = block.page_no or 1
            page_groups.setdefault(page_no, []).append(block)

        for page_no, blocks in sorted(page_groups.items()):
            page_text = self._non_empty_text(blocks)
            for chunk in self._split_text(page_text, config, tokenizer):
                nodes.append(
                    self._make_node(
                        document=document,
                        chunker_name="ocr_page", config=config,
                        text=chunk,
                        blocks=blocks,
                        section_path=(),
                        content_type="ocr",
                        metadata={
                            **self._build_chunk_metadata(chunk, blocks, tokenizer),
                            "page_no": page_no,
                        },
                    )
                )

        return nodes

