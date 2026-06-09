from dataclasses import dataclass, field
from typing import Any

from ragmax.domain.datasets.records import DatasetFileRecord, DatasetRecord


@dataclass(frozen=True)
class CreateDatasetCommand:
    name: str
    dataset_id: str | None = None
    description: str | None = None
    config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UpdateDatasetCommand:
    dataset_id: str
    name: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class AddFilesToDatasetCommand:
    dataset_id: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class RemoveFileFromDatasetCommand:
    dataset_id: str
    source_id: str


@dataclass(frozen=True)
class DatasetWithFiles:
    dataset: DatasetRecord
    files: tuple[DatasetFileRecord, ...]
    file_count: int
