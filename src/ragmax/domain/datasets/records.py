from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class DatasetRecord:
    dataset_id: str
    name: str
    description: str | None = None
    config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    file_count: int = 0


@dataclass(frozen=True)
class DatasetFileRecord:
    id: int
    dataset_id: str
    source_id: str
    added_at: datetime | None = None
