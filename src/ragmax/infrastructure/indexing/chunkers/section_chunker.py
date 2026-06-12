from typing import Any

from ragmax.domain.indexing.blocks import BlockType, ContentBlock
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.tokenization import Tokenizer
from ragmax.infrastructure.indexing.chunkers.base import BaseChunker


class SectionAwareChunker(BaseChunker):
    def chunk(
        self, document: SourceDocument, config: dict[str, Any], tokenizer: Tokenizer
    ) -> list[IndexNode]:
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
            if text_blocks and config.get("node_graph_mode") == "parent_child":
                parent_text = self._non_empty_text(text_blocks)
                if heading_prefix:
                    parent_text = f"{heading_prefix}\n\n{parent_text}"
                parent_node = self._make_node(
                    document=document,
                    chunker_name="section_aware", config=config,
                    text=parent_text,
                    blocks=blocks,
                    section_path=active_path,
                    content_type="section",
                    metadata=self._build_chunk_metadata(parent_text, blocks, tokenizer),
                )
                nodes.append(parent_node)
                parent_node_id = parent_node.node_id

            if text_blocks:
                section_text = self._non_empty_text(text_blocks)
                for chunk in self._split_text(section_text, config, tokenizer):
                    # Only include heading_prefix in child nodes if there's no parent node
                    # (parent_node already contains the heading context)
                    if parent_node_id is None and heading_prefix:
                        text = f"{heading_prefix}\n\n{chunk}"
                    else:
                        text = chunk
                    nodes.append(
                        self._make_node(
                            document=document,
                            chunker_name="section_aware", config=config,
                            text=text,
                            blocks=text_blocks,
                            section_path=active_path,
                            parent_node_id=parent_node_id,
                            content_type="paragraph",
                            metadata=self._build_chunk_metadata(text, text_blocks, tokenizer),
                        )
                    )

            for table_block in table_blocks:
                table_text = table_block.normalized_text
                # Only include heading_prefix in table nodes if there's no parent node
                if parent_node_id is None and heading_prefix:
                    table_text = f"{heading_prefix}\n\n{table_text}"
                nodes.append(
                    self._make_node(
                        document=document,
                        chunker_name="section_aware", config=config,
                        text=table_text,
                        blocks=[table_block],
                        section_path=active_path,
                        parent_node_id=parent_node_id,
                        content_type="table",
                        metadata=self._build_chunk_metadata(table_text, [table_block], tokenizer),
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
