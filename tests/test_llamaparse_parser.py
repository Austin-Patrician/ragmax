from pathlib import Path

import pytest

from ragmax.application.indexing.dtos import SourceInput
from ragmax.infrastructure.indexing.parsers.llamaparse_parser import LlamaParseSourceParser


class FakeParsingClient:
    def __init__(self) -> None:
        self.kwargs = {}

    async def parse(self, **kwargs):
        self.kwargs = kwargs
        return {
            "job": {"id": "lp_job_1"},
            "markdown": [
                {
                    "page_no": 1,
                    "markdown": (
                        "# Metrics\n\n"
                        "| Metric | Value |\n"
                        "| --- | --- |\n"
                        "| Recall | 0.92 |"
                    ),
                    "metadata": {"page_label": "1"},
                }
            ],
        }


class FakeLlamaCloudClient:
    def __init__(self) -> None:
        self.parsing = FakeParsingClient()


@pytest.mark.asyncio
async def test_llamaparse_parser_converts_markdown_pages(tmp_path: Path) -> None:
    source_file = tmp_path / "report.pdf"
    source_file.write_bytes(b"%PDF-1.4 fake")
    fake_client = FakeLlamaCloudClient()
    parser = LlamaParseSourceParser(
        api_key=None,
        default_tier="agentic",
        default_version="latest",
        client=fake_client,
    )

    document = await parser.parse(
        SourceInput(
            source_id="source-1",
            notebook_id="notebook-1",
            filename="report.pdf",
            media_type="application/pdf",
            file_path=str(source_file),
            file_size=source_file.stat().st_size,
        ),
        {"tier": "cost_effective", "version": "2026-05-21"},
    )

    assert document.parser_name == "llamaparse"
    assert document.metadata["llamaparse_job_id"] == "lp_job_1"
    assert document.metadata["llamaparse_tier"] == "cost_effective"
    assert fake_client.parsing.kwargs["tier"] == "cost_effective"
    assert fake_client.parsing.kwargs["version"] == "2026-05-21"
    assert fake_client.parsing.kwargs["upload_file"] == source_file
    assert [block.block_type.value for block in document.blocks] == ["heading", "table"]
    assert all(block.metadata["llamaparse_job_id"] == "lp_job_1" for block in document.blocks)
