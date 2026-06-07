from collections.abc import Mapping
from pathlib import Path
from typing import Any

import anyio
from llama_index.core import SimpleDirectoryReader

from ragmax.application.indexing.dtos import SourceInput
from ragmax.core.exceptions import InvalidRequestError
from ragmax.domain.indexing.blocks import ContentBlock
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.infrastructure.indexing.parsers.block_parsing import blocks_from_text

SIMPLE_DIRECTORY_READER_EXTENSIONS = (
    ".csv",
    ".docx",
    ".epub",
    ".gif",
    ".hwp",
    ".ipynb",
    ".jpeg",
    ".jpg",
    ".mbox",
    ".md",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".ppt",
    ".pptm",
    ".pptx",
    ".txt",
    ".webp",
    ".xls",
    ".xlsx",
)


class SimpleDirectoryReaderSourceParser:
    parser_name = "simple_directory_reader"
    parser_version = "llama_index_simple_directory_reader:v1"

    async def parse(
        self,
        source: SourceInput,
        options: Mapping[str, Any] | None = None,
    ) -> SourceDocument:
        file_path = _require_file_path(source)
        documents = await anyio.to_thread.run_sync(self._load_documents, file_path)
        blocks = self._documents_to_blocks(source, documents)
        if not blocks:
            raise InvalidRequestError(f"Parser '{self.parser_name}' returned no text blocks.")

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

    def _load_documents(self, file_path: Path):
        reader = SimpleDirectoryReader(
            input_files=[str(file_path)],
            raise_on_error=True,
        )
        return reader.load_data()

    def _documents_to_blocks(self, source: SourceInput, documents) -> list[ContentBlock]:
        blocks: list[ContentBlock] = []
        block_index = 1
        for document_index, document in enumerate(documents, start=1):
            text = _document_text(document)
            if not text.strip():
                continue

            metadata = dict(getattr(document, "metadata", {}) or {})
            metadata.update(
                {
                    "document_index": document_index,
                    "parser": self.parser_name,
                }
            )
            page_no = _page_no_from_metadata(metadata) or document_index
            parsed_blocks = blocks_from_text(
                source_id=source.source_id,
                text=text,
                start_index=block_index,
                page_no=page_no,
                metadata=metadata,
            )
            blocks.extend(parsed_blocks)
            block_index += len(parsed_blocks)
        return blocks


def _require_file_path(source: SourceInput) -> Path:
    if not source.file_path:
        raise InvalidRequestError("SimpleDirectoryReader parser requires source.file_path.")
    file_path = Path(source.file_path)
    if not file_path.exists() or not file_path.is_file():
        raise InvalidRequestError(f"Source file does not exist: {source.filename}")
    return file_path


def _document_text(document) -> str:
    if hasattr(document, "get_content"):
        return document.get_content() or ""
    return getattr(document, "text", "") or ""


def _page_no_from_metadata(metadata: Mapping[str, Any]) -> int | None:
    for key in ("page_label", "page_number", "page", "page_no"):
        value = metadata.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None
