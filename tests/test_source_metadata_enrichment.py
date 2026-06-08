from types import SimpleNamespace

from ragmax.api.v1.sources import _media_type_for_upload
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.profiles import IndexingProfile, IndexingProfileName, NodeGraphMode
from ragmax.infrastructure.indexing.enrichers.basic_node_enricher import BasicNodeEnricher


def test_upload_media_type_falls_back_to_filename_for_multipart_file_part() -> None:
    upload = SimpleNamespace(content_type="multipart/form-data")

    assert _media_type_for_upload(upload, "tourism.pdf") == "application/pdf"


def test_node_enricher_backfills_page_numbers_from_node_range() -> None:
    document = SourceDocument(
        source_id="source-1",
        notebook_id="notebook-1",
        filename="tourism.pdf",
        media_type="application/pdf",
        parser_name="llamaparse",
        parser_version="llama_cloud_parse:v1:agentic:latest",
        blocks=(),
    )
    profile = IndexingProfile(
        name=IndexingProfileName.SECTION_PDF,
        description="Section profile",
        chunker="section_aware",
        chunk_size=700,
        chunk_overlap=100,
        node_graph_mode=NodeGraphMode.PARENT_CHILD,
    )
    node = IndexNode(
        node_id="node-1",
        source_id="source-1",
        notebook_id="notebook-1",
        text="hello",
        modality="text",
        content_type="section",
        page_start=1,
        page_end=2,
        metadata={"page_numbers": []},
    )

    enriched = BasicNodeEnricher().enrich([node], document, profile)

    assert enriched[0].metadata["page_numbers"] == [1, 2]
    assert enriched[0].metadata["media_type"] == "application/pdf"
