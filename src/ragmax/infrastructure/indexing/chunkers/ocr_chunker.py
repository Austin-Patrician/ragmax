from ragmax.domain.indexing.blocks import BlockType, ContentBlock
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.profiles import IndexingProfile
from ragmax.infrastructure.indexing.chunkers.base import BaseChunker


class OcrPageChunker(BaseChunker):
    def chunk(self, document: SourceDocument, profile: IndexingProfile) -> list[IndexNode]:
        nodes: list[IndexNode] = []
        page_groups: dict[int, list[ContentBlock]] = {}

        for block in document.blocks:
            if block.block_type not in {BlockType.OCR, BlockType.TEXT} or block.is_empty:
                continue
            page_no = block.page_no or 1
            page_groups.setdefault(page_no, []).append(block)

        for page_no, blocks in sorted(page_groups.items()):
            page_text = self._non_empty_text(blocks)
            for chunk in self._split_text(page_text, profile):
                nodes.append(
                    self._make_node(
                        document=document,
                        profile=profile,
                        text=chunk,
                        blocks=blocks,
                        section_path=(),
                        content_type="ocr",
                        metadata={
                            **self._build_chunk_metadata(chunk, blocks),
                            "page_no": page_no,
                        },
                    )
                )

        return nodes

