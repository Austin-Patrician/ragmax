from ragmax.domain.indexing.profiles import IndexingProfile, IndexingProfileName

DEFAULT_INDEXING_PROFILES: tuple[IndexingProfile, ...] = (
    IndexingProfile(
        name=IndexingProfileName.DEFAULT_PDF,
        description="General PDF chunking with sentence-aware splitting.",
        parser="simple_directory_reader",
        chunker="sentence_splitter",
        chunk_size=700,
        chunk_overlap=100,
        supported_media_types=("application/pdf", "text/plain", "text/markdown"),
        options={"extract_tables": False, "extract_images": False, "parent_child": False},
    ),
    IndexingProfile(
        name=IndexingProfileName.SECTION_PDF,
        description="Section-aware PDF chunking for reports, papers, and manuals.",
        parser="simple_directory_reader",
        chunker="section_aware",
        chunk_size=800,
        chunk_overlap=100,
        supported_media_types=("application/pdf", "text/plain", "text/markdown"),
        options={"keep_headings": True, "extract_tables": True, "parent_child": True},
    ),
    IndexingProfile(
        name=IndexingProfileName.TABLE_REPORT,
        description="Table-aware chunking for financial, analytic, or statistical reports.",
        parser="simple_directory_reader",
        chunker="table_aware",
        chunk_size=600,
        chunk_overlap=80,
        supported_media_types=("application/pdf", "text/plain", "text/markdown"),
        options={"table_to_markdown": True, "repeat_table_header": True},
    ),
    IndexingProfile(
        name=IndexingProfileName.SCANNED_PDF,
        description="OCR-oriented page/block chunking for scanned PDFs.",
        parser="simple_directory_reader",
        chunker="ocr_page",
        chunk_size=500,
        chunk_overlap=80,
        supported_media_types=("application/pdf",),
        options={"preserve_bbox": True, "index_page_images": True},
    ),
)


def list_indexing_profiles() -> tuple[IndexingProfile, ...]:
    return DEFAULT_INDEXING_PROFILES
