import hashlib
import math
import re
from dataclasses import replace

from llama_index.core.node_parser import SentenceSplitter

from ragmax.domain.indexing.blocks import BlockType, ContentBlock
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.profiles import IndexingProfile


class BaseChunker:
    chunker_version = "v1"

    def _split_text(self, text: str, profile: IndexingProfile) -> list[str]:
        normalized_text = text.strip()
        if not normalized_text:
            return []

        splitter = SentenceSplitter(
            chunk_size=profile.chunk_size,
            chunk_overlap=profile.chunk_overlap,
        )
        return [chunk.strip() for chunk in splitter.split_text(normalized_text) if chunk.strip()]

    def _make_node(
        self,
        *,
        document: SourceDocument,
        profile: IndexingProfile,
        text: str,
        content_type: str,
        modality: str = "text",
        blocks: list[ContentBlock] | tuple[ContentBlock, ...],
        section_path: tuple[str, ...] = (),
        parent_node_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> IndexNode:
        page_numbers = [block.page_no for block in blocks if block.page_no is not None]
        page_start = min(page_numbers) if page_numbers else None
        page_end = max(page_numbers) if page_numbers else None
        bbox = next((block.bbox for block in blocks if block.bbox is not None), None)
        block_ids = tuple(block.block_id for block in blocks)
        node_id = self._build_node_id(
            document.source_id,
            profile.name.value,
            content_type,
            text,
            block_ids,
        )

        return IndexNode(
            node_id=node_id,
            source_id=document.source_id,
            notebook_id=document.notebook_id,
            text=text.strip(),
            modality=modality,
            content_type=content_type,
            page_start=page_start,
            page_end=page_end,
            section_path=section_path,
            block_ids=block_ids,
            parent_node_id=parent_node_id,
            bbox=bbox,
            indexing_profile=profile.name.value,
            parser_version=document.parser_version,
            chunker_version=self.chunker_version,
            metadata=metadata or {},
        )

    def _estimate_tokens(self, text: str) -> int:
        return max(1, math.ceil(len(text) / 4))

    def _build_chunk_metadata(self, text: str, blocks: list[ContentBlock]) -> dict[str, object]:
        page_numbers = [block.page_no for block in blocks if block.page_no is not None]
        return {
            "char_count": len(text),
            "estimated_tokens": self._estimate_tokens(text),
            "block_count": len(blocks),
            "page_numbers": page_numbers,
        }

    def _build_node_id(
        self,
        source_id: str,
        profile_name: str,
        content_type: str,
        text: str,
        block_ids: tuple[str, ...],
    ) -> str:
        digest_source = "|".join(
            (source_id, profile_name, content_type, ",".join(block_ids), text[:160])
        )
        digest = hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:12]
        return f"{source_id}:{profile_name}:{digest}"

    def _heading_level(self, text: str) -> int:
        heading = text.strip()
        if not heading:
            return 1
        if heading.startswith("#"):
            return min(6, len(heading) - len(heading.lstrip("#")))

        numeric_match = re.match(r"^(\d+(?:\.\d+)*)\s+", heading)
        if numeric_match:
            return numeric_match.group(1).count(".") + 1

        if re.match(r"^第[一二三四五六七八九十百零\d]+[章节部分篇]\s*", heading):
            return 1

        return 2

    def _clean_heading(self, text: str) -> str:
        cleaned = text.strip().lstrip("#").strip()
        return re.sub(r"\s+", " ", cleaned)

    def _push_heading(
        self,
        section_path: list[str],
        heading_text: str,
    ) -> tuple[str, ...]:
        level = self._heading_level(heading_text)
        clean_heading = self._clean_heading(heading_text)
        next_path = section_path[: max(level - 1, 0)]
        next_path.append(clean_heading)
        return tuple(next_path)

    def _text_blocks(self, blocks: tuple[ContentBlock, ...]) -> list[ContentBlock]:
        return [
            block
            for block in blocks
            if block.block_type in {BlockType.TEXT, BlockType.OCR, BlockType.HEADING}
            and block.normalized_text
        ]

    def _non_empty_text(self, blocks: list[ContentBlock]) -> str:
        return "\n\n".join(block.normalized_text for block in blocks if block.normalized_text)

    def _clone_with_metadata(self, node: IndexNode, metadata: dict[str, object]) -> IndexNode:
        merged_metadata = dict(node.metadata)
        merged_metadata.update(metadata)
        return replace(node, metadata=merged_metadata)
