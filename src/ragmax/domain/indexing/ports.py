from collections.abc import Sequence
from typing import Protocol

from ragmax.domain.indexing.analysis import SourceAnalysis
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.profiles import IndexingProfile


class SourceAnalyzer(Protocol):
    def analyze(
        self,
        document: SourceDocument,
        profiles: Sequence[IndexingProfile],
    ) -> SourceAnalysis:
        ...


class Chunker(Protocol):
    def chunk(
        self,
        document: SourceDocument,
        profile: IndexingProfile,
    ) -> list[IndexNode]:
        ...


class NodeEnricher(Protocol):
    def enrich(
        self,
        nodes: Sequence[IndexNode],
        document: SourceDocument,
        profile: IndexingProfile,
    ) -> list[IndexNode]:
        ...
