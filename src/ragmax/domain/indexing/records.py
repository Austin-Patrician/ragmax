from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from ragmax.domain.indexing.entities import IndexNode


class IndexJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    notebook_id: str
    filename: str
    media_type: str
    source_hash: str
    text: str | None = None
    blocks: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
    requested_profile: str | None = None
    effective_profile: str | None = None
    requested_parser: str | None = None
    effective_parser: str | None = None
    overrides: dict[str, Any] = field(default_factory=dict)
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
