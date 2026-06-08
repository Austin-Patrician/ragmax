from dataclasses import dataclass, field
from typing import Any

from ragmax.domain.indexing.analysis import IndexingSummary, SourceAnalysis
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.profiles import IndexingProfile
from ragmax.domain.indexing.records import IndexBlockRecord, IndexJobRecord, SourceRecord


@dataclass(frozen=True)
class SourceInputBlock:
    block_id: str | None = None
    block_type: str = "text"
    text: str = ""
    page_no: int | None = None
    bbox: tuple[float, float, float, float] | None = None
    section_hint: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceInput:
    source_id: str
    notebook_id: str
    filename: str
    media_type: str
    text: str | None = None
    input_blocks: tuple[SourceInputBlock, ...] = field(default_factory=tuple)
    file_path: str | None = None
    file_size: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProfileOverrides:
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PreviewIndexingCommand:
    source: SourceInput
    profile_name: str | None = None
    parser_name: str | None = None
    parser_options: dict[str, Any] = field(default_factory=dict)
    overrides: ProfileOverrides = field(default_factory=ProfileOverrides)


@dataclass(frozen=True)
class CreateSourceCommand:
    notebook_id: str
    filename: str
    media_type: str
    source_id: str | None = None
    source_hash: str | None = None
    text: str | None = None
    input_blocks: tuple[SourceInputBlock, ...] = field(default_factory=tuple)
    file_path: str | None = None
    file_size: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunIndexJobCommand:
    source_id: str
    profile_name: str | None = None
    parser_name: str | None = None
    parser_options: dict[str, Any] = field(default_factory=dict)
    overrides: ProfileOverrides = field(default_factory=ProfileOverrides)


@dataclass(frozen=True)
class PreviewIndexingResult:
    analysis: SourceAnalysis
    effective_profile: IndexingProfile
    effective_parser: str
    document: SourceDocument
    nodes: tuple[IndexNode, ...]
    summary: IndexingSummary


@dataclass(frozen=True)
class RunIndexJobResult:
    job: IndexJobRecord
    source: SourceRecord
    effective_profile: IndexingProfile
    effective_parser: str
    nodes: tuple[IndexNode, ...]
    summary: IndexingSummary


@dataclass(frozen=True)
class IndexingArtifactsResult:
    job: IndexJobRecord
    blocks: tuple[IndexBlockRecord, ...]
    nodes: tuple[IndexNode, ...]


@dataclass(frozen=True)
class DeleteSourceIndexResult:
    source_id: str
    deleted_count: int
    vector_deleted_count: int = 0
