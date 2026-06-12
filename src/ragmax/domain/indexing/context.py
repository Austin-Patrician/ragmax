from dataclasses import dataclass

from ragmax.domain.indexing.blocks import BlockType, ContentBlock


@dataclass
class ContextConfig:
    """Configuration for context extraction."""

    context_window: int = 1
    """Number of pages/chunks to include before and after current item."""

    context_mode: str = "page"
    """Context extraction mode: 'page' for page-based, 'chunk' for chunk-based."""

    max_context_tokens: int = 2000
    """Maximum number of tokens in extracted context."""

    include_headers: bool = True
    """Whether to include document headers and titles in context."""

    include_captions: bool = True
    """Whether to include image/table captions in context."""


class ContextExtractor:
    """Extract context for multimodal content blocks.

    Provides context-aware text extraction for images, tables, and equations
    by collecting surrounding text, headings, and captions.
    """

    def extract_context(
        self,
        *,
        blocks: tuple[ContentBlock, ...],
        current_index: int,
        config: ContextConfig,
    ) -> str:
        """Extract context for the block at current_index.

        Args:
            blocks: All content blocks from the document
            current_index: Index of the current block to extract context for
            config: Configuration for context extraction

        Returns:
            Formatted context string with surrounding content
        """
        if config.context_mode == "page":
            return self._extract_page_context(blocks, current_index, config)
        else:  # chunk mode
            return self._extract_chunk_context(blocks, current_index, config)

    def extract_neighbor_text(
        self,
        *,
        blocks: tuple[ContentBlock, ...],
        current_index: int,
        window: int = 3,
    ) -> str:
        """Extract neighboring text around the current block.

        Args:
            blocks: All content blocks from the document
            current_index: Index of the current block
            window: Number of blocks to include before and after (default: 3)

        Returns:
            Concatenated text from neighboring blocks
        """
        start_idx = max(0, current_index - window)
        end_idx = min(len(blocks), current_index + window + 1)

        neighbor_texts = []
        for idx in range(start_idx, end_idx):
            if idx == current_index:
                continue  # Skip current block itself

            block = blocks[idx]
            if block.block_type in {BlockType.TEXT, BlockType.HEADING} and block.normalized_text:
                neighbor_texts.append(block.normalized_text)

        return "\n\n".join(neighbor_texts)

    def _extract_page_context(
        self,
        blocks: tuple[ContentBlock, ...],
        current_index: int,
        config: ContextConfig,
    ) -> str:
        """Extract context based on page numbers."""
        current_block = blocks[current_index]
        current_page = current_block.page_no

        if current_page is None:
            return self._extract_chunk_context(blocks, current_index, config)

        start_page = current_page - config.context_window
        end_page = current_page + config.context_window

        context_parts = []
        last_page = None

        for block in blocks:
            if block.page_no is None or not (start_page <= block.page_no <= end_page):
                continue

            if not self._should_include_in_context(block, current_index, blocks, config):
                continue

            if last_page is not None and block.page_no != last_page:
                context_parts.append(f"\n--- Page {block.page_no} ---\n")

            formatted_text = self._format_block_for_context(block, config)
            if formatted_text:
                context_parts.append(formatted_text)
                last_page = block.page_no

        context_text = "\n\n".join(context_parts)
        return self._truncate_context(context_text, config.max_context_tokens)

    def _extract_chunk_context(
        self,
        blocks: tuple[ContentBlock, ...],
        current_index: int,
        config: ContextConfig,
    ) -> str:
        """Extract context based on chunk indices."""
        start_idx = max(0, current_index - config.context_window)
        end_idx = min(len(blocks), current_index + config.context_window + 1)

        context_parts = []
        for idx in range(start_idx, end_idx):
            if idx == current_index:
                continue

            block = blocks[idx]
            if not self._should_include_in_context(block, current_index, blocks, config):
                continue

            formatted_text = self._format_block_for_context(block, config)
            if formatted_text:
                context_parts.append(formatted_text)

        context_text = "\n\n".join(context_parts)
        return self._truncate_context(context_text, config.max_context_tokens)

    def _should_include_in_context(
        self,
        block: ContentBlock,
        current_index: int,
        blocks: tuple[ContentBlock, ...],
        config: ContextConfig,
    ) -> bool:
        """Determine if a block should be included in context."""
        # Always include TEXT and HEADING types
        if block.block_type in {BlockType.TEXT, BlockType.HEADING}:
            return config.include_headers or block.block_type != BlockType.HEADING

        # Include captions from IMAGE/TABLE blocks if configured
        if config.include_captions and block.block_type in {BlockType.IMAGE, BlockType.TABLE}:
            has_caption = (
                block.metadata.get("image_caption")
                or block.metadata.get("table_caption")
            )
            return bool(has_caption)

        return False

    def _format_block_for_context(self, block: ContentBlock, config: ContextConfig) -> str:
        """Format a block for inclusion in context."""
        # For HEADING blocks, add markdown prefix
        if block.block_type == BlockType.HEADING:
            level = block.metadata.get("heading_level", 2)
            prefix = "#" * min(level, 6) + " "
            return prefix + block.normalized_text

        # For TEXT blocks, return as-is
        if block.block_type == BlockType.TEXT:
            return block.normalized_text

        # For IMAGE/TABLE blocks with captions
        if config.include_captions:
            captions = (
                block.metadata.get("image_caption")
                or block.metadata.get("table_caption")
                or []
            )
            if captions:
                caption_text = " ".join(captions) if isinstance(captions, list) else str(captions)
                block_label = "Image" if block.block_type == BlockType.IMAGE else "Table"
                return f"[{block_label} Caption: {caption_text}]"

        return ""

    def _truncate_context(self, text: str, max_tokens: int) -> str:
        """Truncate context to max token count using simple estimation."""
        estimated_tokens = len(text) // 4  # Simple heuristic: 1 token ≈ 4 chars
        if estimated_tokens <= max_tokens:
            return text

        # Truncate to approximately max_tokens
        max_chars = max_tokens * 4
        return text[:max_chars] + "..."
