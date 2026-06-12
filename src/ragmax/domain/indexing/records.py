from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from ragmax.domain.indexing.blocks import BlockType
from ragmax.domain.indexing.entities import IndexNode


class IndexJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class IndexPipelineStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class IndexStageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class IndexingStage(StrEnum):
    SOURCE = "source"
    PARSE_BLOCKS = "parse_blocks"
    CHUNK_NODES = "chunk_nodes"
    QUALITY_ENRICH = "quality_enrich"
    VECTORIZE = "vectorize"


INDEXING_STAGE_ORDER: tuple[IndexingStage, ...] = (
    IndexingStage.SOURCE,
    IndexingStage.PARSE_BLOCKS,
    IndexingStage.CHUNK_NODES,
    IndexingStage.QUALITY_ENRICH,
    IndexingStage.VECTORIZE,
)


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    notebook_id: str
    filename: str
    media_type: str
    source_hash: str
    text: str | None = None
    input_blocks: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    file_path: str | None = None
    file_size: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class IndexJobRecord:
    job_id: str
    source_id: str
    status: IndexJobStatus
    requested_chunker: str | None = None
    effective_chunker: str | None = None
    requested_parser: str | None = None
    effective_parser: str | None = None
    config: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    vector_status: str | None = None
    vector_error_message: str | None = None
    node_count: int = 0
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass(frozen=True)
class PersistedIndexNode:
    job_id: str
    node: IndexNode
    created_at: datetime | None = None


@dataclass(frozen=True)
class IndexBlockRecord:
    block_id: str
    job_id: str
    source_id: str
    notebook_id: str
    order_index: int
    block_type: BlockType
    text: str
    page_no: int | None = None
    bbox: tuple[float, float, float, float] | None = None
    section_hint: tuple[str, ...] = field(default_factory=tuple)
    parser_name: str | None = None
    parser_version: str | None = None
    content_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None


@dataclass(frozen=True)
class IndexPipelineRunRecord:
    run_id: str
    source_id: str
    status: IndexPipelineStatus
    config: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass(frozen=True)
class IndexStageRunRecord:
    stage_run_id: str
    run_id: str
    stage_name: IndexingStage
    status: IndexStageStatus
    sequence_no: int
    stale: bool = False
    summary: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: float | None = None
    artifact_count: int = 0
    created_at: datetime | None = None


@dataclass(frozen=True)
class IndexArtifactManifestRecord:
    artifact_id: str
    run_id: str
    stage_run_id: str
    stage_name: IndexingStage
    artifact_type: str
    storage_uri: str
    payload_format: str
    content_hash: str
    size_bytes: int
    record_count: int
    preview: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
