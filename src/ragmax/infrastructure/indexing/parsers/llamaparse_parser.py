from collections.abc import Mapping
from pathlib import Path
from typing import Any

from llama_cloud import AsyncLlamaCloud
from llama_cloud.types import LlamaParseSupportedFileExtensions

from ragmax.application.indexing.dtos import SourceInput
from ragmax.core.exceptions import ConfigurationError, InvalidRequestError
from ragmax.domain.indexing.blocks import ContentBlock
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.infrastructure.indexing.parsers.block_parsing import blocks_from_text

LLAMAPARSE_EXTENSIONS = tuple(LlamaParseSupportedFileExtensions.__args__)
LLAMAPARSE_TIERS = ("fast", "cost_effective", "agentic", "agentic_plus")


class LlamaParseSourceParser:
    parser_name = "llamaparse"
    parser_version = "llama_cloud_parse:v1"

    def __init__(
        self,
        *,
        api_key: str | None,
        default_tier: str,
        default_version: str,
        client: AsyncLlamaCloud | None = None,
    ) -> None:
        self._api_key = api_key
        self._default_tier = default_tier
        self._default_version = default_version
        self._client = client

    async def parse(
        self,
        source: SourceInput,
        options: Mapping[str, Any] | None = None,
    ) -> SourceDocument:
        file_path = _require_file_path(source)
        parse_options = dict(options or {})
        tier = str(parse_options.get("tier") or self._default_tier)
        version = str(parse_options.get("version") or self._default_version)
        timeout = float(parse_options.get("timeout") or 7200.0)
        polling_interval = float(parse_options.get("polling_interval") or 1.0)

        if tier not in LLAMAPARSE_TIERS:
            raise InvalidRequestError(
                f"Unsupported LlamaParse tier '{tier}'. "
                f"Supported tiers: {', '.join(LLAMAPARSE_TIERS)}."
            )

        client = self._get_client()
        result = await client.parsing.parse(
            tier=tier,
            version=version,
            upload_file=file_path,
            expand=["markdown", "text", "metadata"],
            timeout=timeout,
            polling_interval=polling_interval,
        )

        payload = _model_to_dict(result)
        job_payload = payload.get("job") or {}
        job_id = job_payload.get("id")
        pages = _extract_pages(payload)
        blocks = self._pages_to_blocks(
            source=source,
            pages=pages,
            job_id=job_id,
            tier=tier,
            version=version,
        )
        if not blocks:
            raise InvalidRequestError(f"Parser '{self.parser_name}' returned no text blocks.")

        return SourceDocument(
            source_id=source.source_id,
            notebook_id=source.notebook_id,
            filename=source.filename,
            media_type=source.media_type,
            parser_name=self.parser_name,
            parser_version=f"{self.parser_version}:{tier}:{version}",
            blocks=tuple(blocks),
            metadata={
                **source.metadata,
                "file_size": source.file_size,
                "parser": self.parser_name,
                "llamaparse_job_id": job_id,
                "llamaparse_tier": tier,
                "llamaparse_version": version,
            },
        )

    def _get_client(self) -> AsyncLlamaCloud:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise ConfigurationError("LLAMA_CLOUD_API_KEY is required for LlamaParse indexing.")
        self._client = AsyncLlamaCloud(api_key=self._api_key)
        return self._client

    def _pages_to_blocks(
        self,
        *,
        source: SourceInput,
        pages: list[dict[str, Any]],
        job_id: str | None,
        tier: str,
        version: str,
    ) -> list[ContentBlock]:
        blocks: list[ContentBlock] = []
        block_index = 1
        for page_index, page in enumerate(pages, start=1):
            text = str(page.get("text") or "").strip()
            if not text:
                continue

            page_no = _int_or_none(page.get("page_no")) or page_index
            page_metadata = dict(page.get("metadata") or {})
            page_metadata.update(
                {
                    "parser": self.parser_name,
                    "llamaparse_job_id": job_id,
                    "llamaparse_tier": tier,
                    "llamaparse_version": version,
                    "page_index": page_index,
                }
            )
            parsed_blocks = blocks_from_text(
                source_id=source.source_id,
                text=text,
                start_index=block_index,
                page_no=page_no,
                metadata=page_metadata,
            )
            blocks.extend(parsed_blocks)
            block_index += len(parsed_blocks)
        return blocks


def _require_file_path(source: SourceInput) -> Path:
    if not source.file_path:
        raise InvalidRequestError("LlamaParse parser requires source.file_path.")
    file_path = Path(source.file_path)
    if not file_path.exists() or not file_path.is_file():
        raise InvalidRequestError(f"Source file does not exist: {source.filename}")
    return file_path


def _model_to_dict(model: Any) -> dict[str, Any]:
    if hasattr(model, "to_dict"):
        return dict(model.to_dict())
    if hasattr(model, "model_dump"):
        return dict(model.model_dump())
    if isinstance(model, dict):
        return dict(model)
    return {}


def _extract_pages(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    markdown = payload.get("markdown")
    markdown_pages = _pages_from_value(markdown, preferred_key="markdown")
    if markdown_pages:
        return markdown_pages

    text = payload.get("text")
    text_pages = _pages_from_value(text, preferred_key="text")
    if text_pages:
        return text_pages

    markdown_full = payload.get("markdown_full")
    if isinstance(markdown_full, str) and markdown_full.strip():
        return [{"page_no": 1, "text": markdown_full, "metadata": {}}]

    text_full = payload.get("text_full")
    if isinstance(text_full, str) and text_full.strip():
        return [{"page_no": 1, "text": text_full, "metadata": {}}]

    return []


def _pages_from_value(value: Any, *, preferred_key: str) -> list[dict[str, Any]]:
    if isinstance(value, str):
        return [{"page_no": 1, "text": value, "metadata": {}}] if value.strip() else []

    if isinstance(value, list):
        pages: list[dict[str, Any]] = []
        for index, item in enumerate(value, start=1):
            page = _page_from_item(item, preferred_key=preferred_key, fallback_page_no=index)
            if page is not None:
                pages.append(page)
        return pages

    if isinstance(value, dict):
        if isinstance(value.get("pages"), list):
            return _pages_from_value(value["pages"], preferred_key=preferred_key)

        pages = []
        for index, (key, item) in enumerate(value.items(), start=1):
            page = _page_from_item(item, preferred_key=preferred_key, fallback_page_no=index)
            if page is None:
                continue
            page["page_no"] = _int_or_none(key) or page.get("page_no") or index
            pages.append(page)
        return pages

    return []


def _page_from_item(
    item: Any,
    *,
    preferred_key: str,
    fallback_page_no: int,
) -> dict[str, Any] | None:
    if isinstance(item, str):
        text = item
        metadata: dict[str, Any] = {}
        page_no = fallback_page_no
    elif isinstance(item, dict):
        text = (
            item.get(preferred_key)
            or item.get("markdown")
            or item.get("text")
            or item.get("content")
            or ""
        )
        metadata = dict(item.get("metadata") or {})
        page_no = (
            _int_or_none(item.get("page_no"))
            or _int_or_none(item.get("page"))
            or _int_or_none(item.get("page_number"))
            or fallback_page_no
        )
    else:
        return None

    if not str(text).strip():
        return None
    return {"page_no": page_no, "text": str(text), "metadata": metadata}


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
