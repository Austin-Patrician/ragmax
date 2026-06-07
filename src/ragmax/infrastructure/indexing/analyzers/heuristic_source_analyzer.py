import re
from collections.abc import Sequence

from ragmax.domain.indexing.analysis import SourceAnalysis
from ragmax.domain.indexing.blocks import BlockType
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.profiles import IndexingProfile, IndexingProfileName


class HeuristicSourceAnalyzer:
    def analyze(
        self,
        document: SourceDocument,
        profiles: Sequence[IndexingProfile],
    ) -> SourceAnalysis:
        del profiles

        heading_blocks = sum(
            1 for block in document.blocks if block.block_type == BlockType.HEADING
        )
        table_blocks = sum(1 for block in document.blocks if block.block_type == BlockType.TABLE)
        ocr_blocks = sum(1 for block in document.blocks if block.block_type == BlockType.OCR)
        text_length = len(document.text_content)
        filename = document.filename.lower()

        traits = {
            "block_count": len(document.blocks),
            "heading_blocks": heading_blocks,
            "table_blocks": table_blocks,
            "ocr_blocks": ocr_blocks,
            "page_count": document.page_count,
            "text_length": text_length,
        }

        if ocr_blocks > 0 or (
            document.media_type == "application/pdf"
            and text_length < 80
            and len(document.blocks) > 0
        ):
            return SourceAnalysis(
                recommended_profile=IndexingProfileName.SCANNED_PDF,
                reasons=("Detected OCR-heavy or low-text PDF content.",),
                traits=traits,
            )

        if table_blocks > 0:
            return SourceAnalysis(
                recommended_profile=IndexingProfileName.TABLE_REPORT,
                reasons=("Detected table blocks that should be indexed separately.",),
                traits=traits,
            )

        if heading_blocks >= 2 or re.search(r"(?m)^(#|\d+(\.\d+)*\s+)", document.text_content):
            return SourceAnalysis(
                recommended_profile=IndexingProfileName.SECTION_PDF,
                reasons=("Detected heading-rich content suitable for section-aware chunking.",),
                traits=traits,
            )

        if any(keyword in filename for keyword in ("paper", "report", "manual", "guide")):
            return SourceAnalysis(
                recommended_profile=IndexingProfileName.SECTION_PDF,
                reasons=("Filename suggests a structured document with sections.",),
                traits=traits,
            )

        return SourceAnalysis(
            recommended_profile=IndexingProfileName.DEFAULT_PDF,
            reasons=("Falling back to general sentence-aware chunking.",),
            traits=traits,
        )
