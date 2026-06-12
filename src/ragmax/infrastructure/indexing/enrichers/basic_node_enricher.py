from dataclasses import replace
from typing import Any, cast

from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.entities import IndexNode


class BasicNodeEnricher:
    def enrich(
        self,
        nodes: list[IndexNode] | tuple[IndexNode, ...],
        document: SourceDocument,
        config: dict[str, Any],
    ) -> list[IndexNode]:
        enriched_nodes: list[IndexNode] = []
        chunker = str(config.get("chunker") or config.get("chunker_name") or "")
        for node in nodes:
            metadata = dict(node.metadata)
            if not metadata.get("page_numbers") and node.page_start is not None:
                page_end = node.page_end or node.page_start
                metadata["page_numbers"] = list(range(node.page_start, page_end + 1))
            metadata.update(
                {
                    "source_filename": document.filename,
                    "media_type": document.media_type,
                    "chunker": chunker or node.indexing_profile,
                }
            )
            enriched_nodes.append(replace(node, metadata=cast(dict[str, object], metadata)))
        return enriched_nodes
