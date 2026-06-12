import asyncio
import json
import re
from dataclasses import replace

from ragmax.domain.indexing.blocks import BlockType, ContentBlock
from ragmax.infrastructure.indexing.processors import prompts
from ragmax.infrastructure.indexing.vlm.openai_vlm_provider import OpenAIVLMProvider


class ModalProcessor:
    """Process multimodal content blocks with VLM enhancement."""

    def __init__(self, *, vlm_provider: OpenAIVLMProvider) -> None:
        self._vlm_provider = vlm_provider

    async def process_block(
        self,
        *,
        block: ContentBlock,
        context: str,
        section_path: tuple[str, ...],
    ) -> ContentBlock:
        """Process a single multimodal block with VLM enhancement."""
        if block.block_type == BlockType.IMAGE:
            return await self._process_image_block(block, context, section_path)
        elif block.block_type == BlockType.TABLE:
            return await self._process_table_block(block, context, section_path)
        else:
            return block

    async def process_blocks_batch(
        self,
        *,
        blocks: list[tuple[ContentBlock, str, tuple[str, ...]]],
        max_concurrent: int = 5,
    ) -> list[ContentBlock]:
        """Process multiple blocks concurrently with rate limiting."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_limit(block: ContentBlock, context: str, section: tuple[str, ...]):
            async with semaphore:
                return await self.process_block(block=block, context=context, section_path=section)

        tasks = [process_with_limit(b, c, s) for b, c, s in blocks]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_image_block(
        self,
        block: ContentBlock,
        context: str,
        section_path: tuple[str, ...],
    ) -> ContentBlock:
        """Process IMAGE block with VLM analysis."""
        image_path = block.metadata.get("image_path")
        if not image_path:
            return block

        entity_name = self._generate_entity_name(section_path, "Image")
        captions = block.metadata.get("image_caption", [])
        footnotes = block.metadata.get("image_footnote", [])

        prompt = prompts.VISION_PROMPT_WITH_CONTEXT.format(
            context=context,
            section_path=" > ".join(section_path) if section_path else "Document",
            image_path=image_path,
            captions=self._format_list(captions),
            footnotes=self._format_list(footnotes),
            entity_name=entity_name,
        )

        try:
            response = await self._vlm_provider.analyze_image(
                image_path=image_path,
                prompt=prompt,
                system_prompt=prompts.IMAGE_ANALYSIS_SYSTEM,
            )

            result = self._parse_json_response(response)

            return replace(block, metadata={
                **block.metadata,
                "vlm_description": result.get("detailed_description", ""),
                "entity_info": result.get("entity_info", {}),
            })
        except Exception:
            return block

    async def _process_table_block(
        self,
        block: ContentBlock,
        context: str,
        section_path: tuple[str, ...],
    ) -> ContentBlock:
        """Process TABLE block with LLM analysis."""
        table_body = block.metadata.get("table_body") or block.text
        captions = block.metadata.get("table_caption", [])
        entity_name = self._generate_entity_name(section_path, "Table")

        prompt = prompts.TABLE_PROMPT_WITH_CONTEXT.format(
            context=context,
            section_path=" > ".join(section_path) if section_path else "Document",
            table_body=table_body,
            captions=self._format_list(captions),
            entity_name=entity_name,
        )

        # Note: Table uses text analysis, not image
        # Could be extended to use vision model on table screenshots if available
        return block

    def _generate_entity_name(self, section_path: tuple[str, ...], prefix: str) -> str:
        """Generate semantic entity name from section path."""
        if section_path:
            return f"{prefix} from {section_path[-1]}"
        return prefix

    def _format_list(self, items: list | str | None) -> str:
        """Format list items for prompt."""
        if not items:
            return "None"
        if isinstance(items, str):
            return items
        return ", ".join(str(item) for item in items)

    def _parse_json_response(self, response: str) -> dict:
        """Parse JSON response with fallback."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return {}