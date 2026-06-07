from ragmax.domain.indexing.blocks import BlockType, ContentBlock
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.profiles import IndexingProfile
from ragmax.infrastructure.indexing.chunkers.base import BaseChunker


class SentenceChunker(BaseChunker):
    def chunk(self, document: SourceDocument, profile: IndexingProfile) -> list[IndexNode]:
        nodes: list[IndexNode] = []
        current_blocks: list[ContentBlock] = []
        section_path: tuple[str, ...] = ()

        for block in document.blocks:
            if block.block_type == BlockType.HEADING:
                if current_blocks:
                    nodes.extend(self._chunk_group(document, profile, current_blocks, section_path))
                    current_blocks = []
                section_path = self._push_heading(list(section_path), block.normalized_text)
                continue

            if block.block_type == BlockType.TABLE or block.is_empty:
                continue

            current_blocks.append(block)

        if current_blocks:
            nodes.extend(self._chunk_group(document, profile, current_blocks, section_path))

        return nodes

    def _chunk_group(
        self,
        document: SourceDocument,
        profile: IndexingProfile,
        blocks: list[ContentBlock],
        section_path: tuple[str, ...],
    ) -> list[IndexNode]:
        group_text = self._non_empty_text(blocks)
        chunks = self._split_text(group_text, profile)
        return [
            self._make_node(
                document=document,
                profile=profile,
                text=chunk,
                blocks=blocks,
                section_path=section_path,
                content_type="paragraph",
                metadata=self._build_chunk_metadata(chunk, blocks),
            )
            for chunk in chunks
        ]

