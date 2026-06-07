from ragmax.domain.indexing.blocks import BlockType, ContentBlock
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.profiles import IndexingProfile
from ragmax.infrastructure.indexing.chunkers.base import BaseChunker


class TableAwareChunker(BaseChunker):
    def chunk(self, document: SourceDocument, profile: IndexingProfile) -> list[IndexNode]:
        nodes: list[IndexNode] = []
        text_group: list[ContentBlock] = []
        section_path: tuple[str, ...] = ()

        def flush_text_group() -> None:
            if not text_group:
                return
            group_text = self._non_empty_text(text_group)
            for chunk in self._split_text(group_text, profile):
                nodes.append(
                    self._make_node(
                        document=document,
                        profile=profile,
                        text=chunk,
                        blocks=text_group,
                        section_path=section_path,
                        content_type="paragraph",
                        metadata=self._build_chunk_metadata(chunk, text_group),
                    )
                )
            text_group.clear()

        for block in document.blocks:
            if block.block_type == BlockType.HEADING:
                flush_text_group()
                section_path = self._push_heading(list(section_path), block.normalized_text)
                continue

            if block.block_type == BlockType.TABLE:
                flush_text_group()
                nodes.extend(self._table_nodes(document, profile, block, section_path))
                continue

            if block.is_empty:
                continue

            text_group.append(block)

        flush_text_group()
        return nodes

    def _table_nodes(
        self,
        document: SourceDocument,
        profile: IndexingProfile,
        table_block: ContentBlock,
        section_path: tuple[str, ...],
    ) -> list[IndexNode]:
        chunks = self._split_table(
            table_block.normalized_text,
            profile.options.get("repeat_table_header", True),
        )
        nodes: list[IndexNode] = []
        for chunk in chunks:
            nodes.append(
                self._make_node(
                    document=document,
                    profile=profile,
                    text=chunk,
                    blocks=[table_block],
                    section_path=section_path,
                    content_type="table",
                    metadata=self._build_chunk_metadata(chunk, [table_block]),
                )
            )
        return nodes

    def _split_table(self, text: str, repeat_header: bool) -> list[str]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) <= 8:
            return [text.strip()]

        header = lines[:2] if repeat_header and len(lines) >= 2 else []
        body = lines[2:] if header else lines
        row_groups = [body[index : index + 6] for index in range(0, len(body), 6)]

        chunks: list[str] = []
        for rows in row_groups:
            parts = header + rows
            chunks.append("\n".join(parts))
        return chunks
