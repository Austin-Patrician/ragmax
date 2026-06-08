import pytest

from ragmax.application.indexing.dtos import SourceInput
from ragmax.application.indexing.parser_registry import ParserSpec, SourceParserRegistry
from ragmax.core.exceptions import InvalidRequestError


class FakeParser:
    async def parse(self, source, options=None):
        raise NotImplementedError


def test_file_parser_resolution_uses_default_file_parser() -> None:
    registry = SourceParserRegistry(
        parsers={
            "simple_directory_reader": FakeParser(),
            "llamaparse": FakeParser(),
            "inline_content_parser": FakeParser(),
        },
        specs=(
            ParserSpec(
                name="simple_directory_reader",
                description="Simple parser",
                supported_extensions=(".pdf",),
            ),
            ParserSpec(
                name="llamaparse",
                description="LlamaParse parser",
                supported_extensions=(".pdf",),
            ),
            ParserSpec(
                name="inline_content_parser",
                description="Inline parser",
                is_internal=True,
            ),
        ),
        default_file_parser="llamaparse",
        inline_parser="inline_content_parser",
    )

    resolved = registry.resolve(
        source=SourceInput(
            source_id="source-1",
            notebook_id="notebook-1",
            filename="report.pdf",
            media_type="application/pdf",
            file_path="storage/report.pdf",
        ),
        requested_parser=None,
    )

    assert resolved.name == "llamaparse"


def test_inline_sources_still_use_inline_parser() -> None:
    registry = SourceParserRegistry(
        parsers={
            "llamaparse": FakeParser(),
            "inline_content_parser": FakeParser(),
        },
        specs=(
            ParserSpec(
                name="llamaparse",
                description="LlamaParse parser",
                supported_extensions=(".pdf",),
            ),
            ParserSpec(
                name="inline_content_parser",
                description="Inline parser",
                is_internal=True,
            ),
        ),
        default_file_parser="llamaparse",
        inline_parser="inline_content_parser",
    )

    resolved = registry.resolve(
        source=SourceInput(
            source_id="source-1",
            notebook_id="notebook-1",
            filename="note.txt",
            media_type="text/plain",
            text="Inline text",
        ),
        requested_parser=None,
    )

    assert resolved.name == "inline_content_parser"


def test_unknown_requested_parser_is_rejected() -> None:
    registry = SourceParserRegistry(
        parsers={"llamaparse": FakeParser()},
        specs=(ParserSpec(name="llamaparse", description="LlamaParse parser"),),
        default_file_parser="llamaparse",
        inline_parser="inline_content_parser",
    )

    with pytest.raises(InvalidRequestError, match="Unknown source parser"):
        registry.resolve(
            source=SourceInput(
                source_id="source-1",
                notebook_id="notebook-1",
                filename="report.pdf",
                media_type="application/pdf",
                file_path="storage/report.pdf",
            ),
            requested_parser="missing",
        )
