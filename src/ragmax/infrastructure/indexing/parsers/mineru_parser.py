import asyncio
import hashlib
import io
import json
import shutil
import time
import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import anyio
import httpx

from ragmax.application.indexing.dtos import SourceInput
from ragmax.core.exceptions import ConfigurationError, ExternalServiceError, InvalidRequestError
from ragmax.domain.indexing.blocks import BlockType, ContentBlock
from ragmax.domain.indexing.documents import SourceDocument


class MineruParser:
    """MinerU API parser with multimodal support."""

    parser_name = "mineru"
    parser_version = "mineru_api:v1"

    def __init__(
        self,
        *,
        api_token: str | None,
        api_base_url: str = "https://mineru.net",
        model_version: str = "vlm",
        enable_table: bool = True,
        enable_formula: bool = True,
        polling_interval: float = 2.0,
        timeout: int = 300,
        source_storage_dir: Path,
    ) -> None:
        if not api_token:
            raise ConfigurationError("MINERU_API_TOKEN is required for MinerU parser.")

        self._api_token = api_token
        self._api_base_url = api_base_url.rstrip("/")
        self._model_version = model_version
        self._enable_table = enable_table
        self._enable_formula = enable_formula
        self._polling_interval = polling_interval
        self._timeout = timeout
        self._source_storage_dir = Path(source_storage_dir)

    async def parse(
        self,
        source: SourceInput,
        options: Mapping[str, Any] | None = None,
    ) -> SourceDocument:
        """Parse document using MinerU API."""
        file_path = self._require_file_path(source)

        task_id = await self._submit_task(file_path)
        result = await self._poll_task(task_id)
        content_list = await self._download_and_extract(result, source.source_id)

        blocks = self._content_list_to_blocks(
            source_id=source.source_id,
            content_list=content_list,
        )

        if not blocks:
            raise InvalidRequestError(f"Parser '{self.parser_name}' returned no blocks.")

        return SourceDocument(
            source_id=source.source_id,
            notebook_id=source.notebook_id,
            filename=source.filename,
            media_type=source.media_type,
            parser_name=self.parser_name,
            parser_version=self.parser_version,
            blocks=tuple(blocks),
            metadata={
                **source.metadata,
                "file_size": source.file_size,
                "parser": self.parser_name,
            },
        )

    async def _submit_task(self, file_path: Path) -> str:
        """Submit parsing task to MinerU API."""
        url = f"{self._api_base_url}/api/v4/extract/task"

        async with httpx.AsyncClient() as client:
            with file_path.open("rb") as f:
                files = {"file": (file_path.name, f, "application/octet-stream")}
                data = {
                    "model_version": self._model_version,
                    "enable_table": str(self._enable_table).lower(),
                    "enable_formula": str(self._enable_formula).lower(),
                }

                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {self._api_token}"},
                    files=files,
                    data=data,
                    timeout=60.0,
                )

            self._check_response(response)
            result = response.json()

            if result.get("code") != 0:
                raise ExternalServiceError(
                    f"MinerU API error: {result.get('msg', 'Unknown error')}"
                )

            task_id = result.get("data", {}).get("task_id")
            if not task_id:
                raise ExternalServiceError("MinerU API did not return task_id")

            return task_id

    async def _poll_task(self, task_id: str) -> dict:
        """Poll task status until completion."""
        url = f"{self._api_base_url}/api/v4/extract/task/{task_id}"
        start_time = time.time()

        async with httpx.AsyncClient() as client:
            while time.time() - start_time < self._timeout:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {self._api_token}"},
                    timeout=30.0,
                )

                self._check_response(response)
                result = response.json()

                if result.get("code") != 0:
                    raise ExternalServiceError(f"MinerU polling error: {result.get('msg')}")

                data = result.get("data", {})
                state = data.get("state")

                if state == "done":
                    return data
                elif state == "failed":
                    raise ExternalServiceError(
                        f"MinerU task failed: {data.get('err_msg', 'Unknown error')}"
                    )
                elif state in ("pending", "running", "uploading", "converting"):
                    await asyncio.sleep(self._polling_interval)
                else:
                    raise ExternalServiceError(f"Unknown MinerU task state: {state}")

        raise ExternalServiceError(f"MinerU task timeout after {self._timeout}s")

    async def _download_and_extract(self, result: dict, source_id: str) -> list[dict]:
        """Download ZIP and extract content_list JSON."""
        zip_url = result.get("full_zip_url")
        if not zip_url:
            raise ExternalServiceError("MinerU result missing full_zip_url")

        async with httpx.AsyncClient() as client:
            response = await client.get(zip_url, timeout=60.0)
            self._check_response(response)
            zip_data = response.content

        return await anyio.to_thread.run_sync(
            self._extract_zip_content, zip_data, source_id
        )

    def _extract_zip_content(self, zip_data: bytes, source_id: str) -> list[dict]:
        """Extract and parse content from ZIP file."""
        images_dir = self._source_storage_dir / source_id / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            json_file = None
            for name in zf.namelist():
                if name.endswith(".json") and "content" in name.lower():
                    json_file = name
                    break

            if not json_file:
                raise InvalidRequestError("No content JSON found in MinerU ZIP")

            with zf.open(json_file) as f:
                content_list = json.load(f)

            for name in zf.namelist():
                if name.startswith("images/") and not name.endswith("/"):
                    image_name = Path(name).name
                    target = images_dir / image_name
                    with zf.open(name) as src, target.open("wb") as dst:
                        shutil.copyfileobj(src, dst)

        return content_list if isinstance(content_list, list) else []

    def _content_list_to_blocks(
        self,
        *,
        source_id: str,
        content_list: list[dict],
    ) -> list[ContentBlock]:
        """Convert MinerU content_list to ContentBlocks."""
        blocks = []
        section_path = []
        block_index = 1

        for idx, item in enumerate(content_list):
            item_type = item.get("type", "text")
            page_no = item.get("page_idx")

            if item_type == "text":
                text = item.get("text", "").strip()
                if not text:
                    continue

                text_level = item.get("text_level", 0)
                block_type = BlockType.HEADING if text_level > 0 else BlockType.TEXT

                if block_type == BlockType.HEADING:
                    section_path = self._update_section_path(section_path, text, text_level)

                blocks.append(ContentBlock(
                    block_id=f"{source_id}:block:{block_index}",
                    source_id=source_id,
                    block_type=block_type,
                    text=text,
                    page_no=page_no,
                    section_hint=tuple(section_path),
                    metadata={
                        "parser": self.parser_name,
                        "content_list_index": idx,
                        "text_level": text_level,
                    },
                ))
                block_index += 1

            elif item_type == "image":
                img_path = item.get("image_path") or item.get("img_path")
                if img_path:
                    abs_path = self._source_storage_dir / source_id / "images" / Path(img_path).name
                    blocks.append(ContentBlock(
                        block_id=f"{source_id}:block:{block_index}",
                        source_id=source_id,
                        block_type=BlockType.IMAGE,
                        text=f"[Image: {abs_path.name}]",
                        page_no=page_no,
                        section_hint=tuple(section_path),
                        metadata={
                            "parser": self.parser_name,
                            "content_list_index": idx,
                            "image_path": str(abs_path),
                            "image_caption": item.get("image_caption") or item.get("img_caption", []),
                            "image_footnote": item.get("image_footnote") or item.get("img_footnote", []),
                        },
                    ))
                    block_index += 1

            elif item_type == "table":
                table_body = item.get("table_body", "")
                blocks.append(ContentBlock(
                    block_id=f"{source_id}:block:{block_index}",
                    source_id=source_id,
                    block_type=BlockType.TABLE,
                    text=table_body,
                    page_no=page_no,
                    section_hint=tuple(section_path),
                    metadata={
                        "parser": self.parser_name,
                        "content_list_index": idx,
                        "table_body": table_body,
                        "table_caption": item.get("table_caption", []),
                        "table_footnote": item.get("table_footnote", []),
                    },
                ))
                block_index += 1

            elif item_type == "equation":
                latex = item.get("latex") or item.get("text", "")
                blocks.append(ContentBlock(
                    block_id=f"{source_id}:block:{block_index}",
                    source_id=source_id,
                    block_type=BlockType.EQUATION,
                    text=latex,
                    page_no=page_no,
                    section_hint=tuple(section_path),
                    metadata={
                        "parser": self.parser_name,
                        "content_list_index": idx,
                        "equation_latex": latex,
                        "equation_format": item.get("text_format", "latex"),
                    },
                ))
                block_index += 1

        return blocks

    def _update_section_path(self, path: list[str], heading: str, level: int) -> list[str]:
        """Update section path based on heading level."""
        new_path = path[: max(0, level - 1)]
        new_path.append(heading)
        return new_path

    def _require_file_path(self, source: SourceInput) -> Path:
        """Validate and return file path."""
        if not source.file_path:
            raise InvalidRequestError("MinerU parser requires source.file_path.")
        file_path = Path(source.file_path)
        if not file_path.exists() or not file_path.is_file():
            raise InvalidRequestError(f"Source file does not exist: {source.filename}")
        return file_path

    def _check_response(self, response: httpx.Response) -> None:
        """Check HTTP response for errors."""
        if response.status_code >= 400:
            raise ExternalServiceError(
                f"MinerU API HTTP {response.status_code}: {response.text[:200]}"
            )