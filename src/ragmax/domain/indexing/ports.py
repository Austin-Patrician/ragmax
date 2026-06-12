from collections.abc import Sequence
from typing import Any, Protocol

from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.tokenization import Tokenizer


class Chunker(Protocol):
    def chunk(
        self,
        document: SourceDocument,
        config: dict[str, Any],
        tokenizer: Tokenizer,
    ) -> list[IndexNode]:
        ...


class NodeEnricher(Protocol):
    def enrich(
        self,
        nodes: Sequence[IndexNode],
        document: SourceDocument,
        config: dict[str, Any],
    ) -> list[IndexNode]:
        ...
