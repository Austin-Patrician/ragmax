from dataclasses import replace
from typing import cast

from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.profiles import IndexingProfile


class BasicNodeEnricher:
    def enrich(
        self,
        nodes: list[IndexNode] | tuple[IndexNode, ...],
        document: SourceDocument,
        profile: IndexingProfile,
    ) -> list[IndexNode]:
        enriched_nodes: list[IndexNode] = []
        for node in nodes:
            metadata = dict(node.metadata)
            if not metadata.get("page_numbers") and node.page_start is not None:
                page_end = node.page_end or node.page_start
                metadata["page_numbers"] = list(range(node.page_start, page_end + 1))
            metadata.update(
                {
                    "source_filename": document.filename,
                    "media_type": document.media_type,
                    "profile_chunker": profile.chunker,
                }
            )
            enriched_nodes.append(replace(node, metadata=cast(dict[str, object], metadata)))
        return enriched_nodes

