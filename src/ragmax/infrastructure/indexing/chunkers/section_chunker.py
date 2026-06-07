from ragmax.domain.indexing.blocks import BlockType, ContentBlock
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.profiles import IndexingProfile
from ragmax.infrastructure.indexing.chunkers.base import BaseChunker


class SectionAwareChunker(BaseChunker):
    def chunk(self, document: SourceDocument, profile: IndexingProfile) -> list[IndexNode]:
        nodes: list[IndexNode] = []
        section_path: tuple[str, ...] = ()
        section_blocks: list[ContentBlock] = []

        def flush_section(active_path: tuple[str, ...], blocks: list[ContentBlock]) -> None:
            if not blocks:
                return

            text_blocks = [
                block
                for block in blocks
                if block.block_type in {BlockType.TEXT, BlockType.OCR}
                and block.normalized_text
            ]
            table_blocks = [block for block in blocks if block.block_type == BlockType.TABLE]
            heading_prefix = " > ".join(active_path)

            parent_node_id: str | None = None
            if text_blocks and profile.options.get("parent_child", False):
                parent_text = self._non_empty_text(text_blocks)
                if heading_prefix:
                    parent_text = f"{heading_prefix}\n\n{parent_text}"
                parent_node = self._make_node(
                    document=document,
                    profile=profile,
                    text=parent_text,
                    blocks=blocks,
                    section_path=active_path,
                    content_type="section",
                    metadata=self._build_chunk_metadata(parent_text, blocks),
                )
                nodes.append(parent_node)
                parent_node_id = parent_node.node_id

            if text_blocks:
                section_text = self._non_empty_text(text_blocks)
                for chunk in self._split_text(section_text, profile):
                    text = f"{heading_prefix}\n\n{chunk}" if heading_prefix else chunk
                    nodes.append(
                        self._make_node(
                            document=document,
                            profile=profile,
                            text=text,
                            blocks=text_blocks,
                            section_path=active_path,
                            parent_node_id=parent_node_id,
                            content_type="paragraph",
                            metadata=self._build_chunk_metadata(text, text_blocks),
                        )
                    )

            for table_block in table_blocks:
                table_text = table_block.normalized_text
                if heading_prefix:
                    table_text = f"{heading_prefix}\n\n{table_text}"
                nodes.append(
                    self._make_node(
                        document=document,
                        profile=profile,
                        text=table_text,
                        blocks=[table_block],
                        section_path=active_path,
                        parent_node_id=parent_node_id,
                        content_type="table",
                        metadata=self._build_chunk_metadata(table_text, [table_block]),
                    )
                )

        for block in document.blocks:
            if block.block_type == BlockType.HEADING:
                flush_section(section_path, section_blocks)
                section_blocks = []
                section_path = self._push_heading(list(section_path), block.normalized_text)
                continue

            if block.is_empty:
                continue

            section_blocks.append(block)

        flush_section(section_path, section_blocks)
        return nodes

