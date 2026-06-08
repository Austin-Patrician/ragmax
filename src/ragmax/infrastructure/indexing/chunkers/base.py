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

        # Apply bbox aggregation strategy from profile options
        bbox_strategy = profile.options.get("bbox_aggregation_strategy", "union")
        bbox = self._aggregate_bboxes(blocks, strategy=bbox_strategy)

        block_ids = tuple(block.block_id for block in blocks)

        # Prioritize section_hint from blocks if available (parser-provided structure)
        effective_section_path = section_path
        if blocks:
            first_block = blocks[0] if isinstance(blocks, (list, tuple)) else blocks
            if hasattr(first_block, "section_hint") and first_block.section_hint:
                effective_section_path = first_block.section_hint

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
            section_path=effective_section_path,
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

    def _aggregate_bboxes(
        self,
        blocks: list[ContentBlock] | tuple[ContentBlock, ...],
        strategy: str = "union",
    ) -> tuple[float, float, float, float] | None:
        """
        Aggregate bboxes from multiple blocks using the specified strategy.

        Args:
            blocks: List of ContentBlocks
            strategy: "union" (compute bounding box) or "first" (take first bbox)

        Returns:
            Aggregated bbox as (x0, y0, x1, y1) or None if no bboxes available
        """
        if strategy == "first":
            return self._aggregate_bboxes_first(blocks)
        elif strategy == "union":
            return self._aggregate_bboxes_union(blocks)
        else:
            # Default to union for unknown strategies
            return self._aggregate_bboxes_union(blocks)

    def _aggregate_bboxes_first(
        self,
        blocks: list[ContentBlock] | tuple[ContentBlock, ...],
    ) -> tuple[float, float, float, float] | None:
        """
        Take the first available bbox (backward compatible behavior).

        This is useful for:
        - Backward compatibility
        - Simple cases where first block represents the whole node
        """
        return next((block.bbox for block in blocks if block.bbox is not None), None)

    def _aggregate_bboxes_union(
        self,
        blocks: list[ContentBlock] | tuple[ContentBlock, ...],
    ) -> tuple[float, float, float, float] | None:
        """
        Compute the minimum bounding box (union) that encompasses all block bboxes.

        Example:
            Block 1: (100, 200, 300, 250)  # Top block
            Block 2: (100, 260, 300, 310)  # Middle block
            Block 3: (100, 320, 300, 370)  # Bottom block
            Union:   (100, 200, 300, 370)  # Encompasses all

        This is useful for:
        - Multi-block sections spanning multiple regions
        - Accurate PDF highlighting of entire sections
        - Spatial queries ("find content in page bottom half")
        """
        valid_bboxes = [block.bbox for block in blocks if block.bbox is not None]

        if not valid_bboxes:
            return None

        # Single bbox - return as is
        if len(valid_bboxes) == 1:
            return valid_bboxes[0]

        # Multiple bboxes - compute union
        x0 = min(bbox[0] for bbox in valid_bboxes)
        y0 = min(bbox[1] for bbox in valid_bboxes)
        x1 = max(bbox[2] for bbox in valid_bboxes)
        y1 = max(bbox[3] for bbox in valid_bboxes)

        return (x0, y0, x1, y1)

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
