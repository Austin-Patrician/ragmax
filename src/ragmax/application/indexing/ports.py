from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, Self

from ragmax.application.indexing.dtos import SourceInput
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.records import (
    IndexArtifactManifestRecord,
    IndexBlockRecord,
    IndexingStage,
    IndexJobRecord,
    IndexPipelineRunRecord,
    IndexStageRunRecord,
    SourceRecord,
)


@dataclass(frozen=True)
class VectorIndexRecord:
    node_id: str
    point_id: str
    collection_name: str


class SourceParser(Protocol):
    async def parse(
        self,
        source: SourceInput,
        options: Mapping[str, Any] | None = None,
    ) -> SourceDocument:
        ...


class EmbeddingProvider(Protocol):
    model_name: str
    dimension: int

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        ...


class VectorIndexWriter(Protocol):
    async def upsert_nodes(
        self,
        *,
        collection_name: str,
        nodes: Sequence[IndexNode],
        embeddings: Sequence[Sequence[float]],
        embedding_model: str,
    ) -> tuple[VectorIndexRecord, ...]:
        ...

    async def delete_source(
        self,
        *,
        collection_name: str,
        source_id: str,
    ) -> int:
        ...


class SourceRepository(Protocol):
    async def create(self, source: SourceRecord) -> SourceRecord:
        ...

    async def get(self, source_id: str) -> SourceRecord | None:
        ...


class IndexJobRepository(Protocol):
    async def create(self, job: IndexJobRecord) -> IndexJobRecord:
        ...

    async def get(self, job_id: str) -> IndexJobRecord | None:
        ...

    async def update(self, job: IndexJobRecord) -> IndexJobRecord:
        ...


class IndexPipelineRunRepository(Protocol):
    async def create(self, run: IndexPipelineRunRecord) -> IndexPipelineRunRecord:
        ...

    async def get(self, run_id: str) -> IndexPipelineRunRecord | None:
        ...

    async def list_by_source(
        self,
        source_id: str,
        *,
        limit: int,
    ) -> tuple[IndexPipelineRunRecord, ...]:
        ...

    async def list_latest(self, *, limit: int) -> tuple[IndexPipelineRunRecord, ...]:
        ...

    async def update(self, run: IndexPipelineRunRecord) -> IndexPipelineRunRecord:
        ...


class IndexStageRunRepository(Protocol):
    async def create(self, stage_run: IndexStageRunRecord) -> IndexStageRunRecord:
        ...

    async def get(self, stage_run_id: str) -> IndexStageRunRecord | None:
        ...

    async def list_by_run(self, run_id: str) -> tuple[IndexStageRunRecord, ...]:
        ...

    async def latest_for_stage(
        self,
        *,
        run_id: str,
        stage_name: IndexingStage,
    ) -> IndexStageRunRecord | None:
        ...

    async def update(self, stage_run: IndexStageRunRecord) -> IndexStageRunRecord:
        ...

    async def mark_stale_after(
        self,
        *,
        run_id: str,
        stage_name: IndexingStage,
    ) -> int:
        ...


class IndexArtifactManifestRepository(Protocol):
    async def create_many(
        self,
        manifests: Sequence[IndexArtifactManifestRecord],
    ) -> tuple[IndexArtifactManifestRecord, ...]:
        ...

    async def get(self, artifact_id: str) -> IndexArtifactManifestRecord | None:
        ...

    async def list_by_stage_run(
        self,
        stage_run_id: str,
    ) -> tuple[IndexArtifactManifestRecord, ...]:
        ...

    async def list_latest_by_run_stage(
        self,
        *,
        run_id: str,
        stage_name: IndexingStage,
    ) -> tuple[IndexArtifactManifestRecord, ...]:
        ...


class IndexNodeRepository(Protocol):
    async def replace_for_source(
        self,
        *,
        source_id: str,
        job_id: str,
        nodes: Sequence[IndexNode],
    ) -> tuple[IndexNode, ...]:
        ...

    async def list_by_source(self, source_id: str) -> tuple[IndexNode, ...]:
        ...

    async def list_by_job(self, job_id: str) -> tuple[IndexNode, ...]:
        ...

    async def get_many(self, node_ids: Sequence[str]) -> tuple[IndexNode, ...]:
        ...

    async def delete_by_source(self, source_id: str) -> int:
        ...


class IndexBlockRepository(Protocol):
    async def replace_for_source(
        self,
        *,
        source_id: str,
        job_id: str,
        blocks: Sequence[IndexBlockRecord],
    ) -> tuple[IndexBlockRecord, ...]:
        ...

    async def list_by_job(self, job_id: str) -> tuple[IndexBlockRecord, ...]:
        ...

    async def delete_by_source(self, source_id: str) -> int:
        ...


class IndexingUnitOfWork(Protocol):
    sources: SourceRepository
    jobs: IndexJobRepository
    pipeline_runs: IndexPipelineRunRepository
    stage_runs: IndexStageRunRepository
    artifact_manifests: IndexArtifactManifestRepository
    blocks: IndexBlockRepository
    nodes: IndexNodeRepository

    async def __aenter__(self) -> Self:
        ...

    async def __aexit__(self, exc_type, exc, tb) -> None:
        ...

    async def commit(self) -> None:
        ...

    async def rollback(self) -> None:
        ...
