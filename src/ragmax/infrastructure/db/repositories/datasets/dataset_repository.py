from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ragmax.domain.datasets.ports import DatasetFileRepository, DatasetRepository
from ragmax.domain.datasets.records import DatasetFileRecord, DatasetRecord
from ragmax.infrastructure.db.models import DatasetFileModel, DatasetModel


class SQLAlchemyDatasetRepository(DatasetRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, dataset: DatasetRecord) -> DatasetRecord:
        model = DatasetModel(
            dataset_id=dataset.dataset_id,
            name=dataset.name,
            description=dataset.description,
            config=dataset.config,
            dataset_metadata=dataset.metadata,
            created_at=dataset.created_at or datetime.now(UTC),
            updated_at=dataset.updated_at or datetime.now(UTC),
        )
        self._session.add(model)
        await self._session.flush()
        return self._model_to_record(model)

    async def get(self, dataset_id: str) -> DatasetRecord | None:
        result = await self._session.execute(
            select(DatasetModel).where(DatasetModel.dataset_id == dataset_id)
        )
        model = result.scalar_one_or_none()
        return self._model_to_record(model) if model else None

    async def list(self, limit: int = 100, offset: int = 0) -> tuple[DatasetRecord, ...]:
        result = await self._session.execute(
            select(DatasetModel, func.count(DatasetFileModel.id).label("file_count"))
            .outerjoin(DatasetFileModel, DatasetModel.dataset_id == DatasetFileModel.dataset_id)
            .group_by(DatasetModel.dataset_id)
            .order_by(DatasetModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = result.all()
        return tuple(self._model_to_record(model, file_count) for model, file_count in rows)

    async def update(self, dataset: DatasetRecord) -> DatasetRecord:
        result = await self._session.execute(
            select(DatasetModel).where(DatasetModel.dataset_id == dataset.dataset_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Dataset not found: {dataset.dataset_id}")

        model.name = dataset.name
        model.description = dataset.description
        model.config = dataset.config
        model.dataset_metadata = dataset.metadata
        model.updated_at = datetime.now(UTC)

        await self._session.flush()
        return self._model_to_record(model)

    async def delete(self, dataset_id: str) -> bool:
        result = await self._session.execute(
            delete(DatasetModel).where(DatasetModel.dataset_id == dataset_id)
        )
        return result.rowcount > 0

    def _model_to_record(self, model: DatasetModel, file_count: int = 0) -> DatasetRecord:
        return DatasetRecord(
            dataset_id=model.dataset_id,
            name=model.name,
            description=model.description,
            config=dict(model.config),
            metadata=dict(model.dataset_metadata),
            created_at=model.created_at,
            updated_at=model.updated_at,
            file_count=file_count,
        )


class SQLAlchemyDatasetFileRepository(DatasetFileRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_files(
        self, dataset_id: str, source_ids: tuple[str, ...]
    ) -> tuple[DatasetFileRecord, ...]:
        added = []
        for source_id in source_ids:
            # Check if already exists
            exists = await self.exists(dataset_id, source_id)
            if exists:
                continue

            model = DatasetFileModel(
                dataset_id=dataset_id,
                source_id=source_id,
                added_at=datetime.now(UTC),
            )
            self._session.add(model)
            await self._session.flush()
            added.append(self._model_to_record(model))

        return tuple(added)

    async def remove_file(self, dataset_id: str, source_id: str) -> bool:
        result = await self._session.execute(
            delete(DatasetFileModel).where(
                DatasetFileModel.dataset_id == dataset_id,
                DatasetFileModel.source_id == source_id,
            )
        )
        return result.rowcount > 0

    async def list_by_dataset(self, dataset_id: str) -> tuple[DatasetFileRecord, ...]:
        result = await self._session.execute(
            select(DatasetFileModel)
            .where(DatasetFileModel.dataset_id == dataset_id)
            .order_by(DatasetFileModel.added_at.desc())
        )
        models = result.scalars().all()
        return tuple(self._model_to_record(model) for model in models)

    async def list_by_source(self, source_id: str) -> tuple[DatasetFileRecord, ...]:
        result = await self._session.execute(
            select(DatasetFileModel)
            .where(DatasetFileModel.source_id == source_id)
            .order_by(DatasetFileModel.added_at.desc())
        )
        models = result.scalars().all()
        return tuple(self._model_to_record(model) for model in models)

    async def exists(self, dataset_id: str, source_id: str) -> bool:
        result = await self._session.execute(
            select(DatasetFileModel).where(
                DatasetFileModel.dataset_id == dataset_id,
                DatasetFileModel.source_id == source_id,
            )
        )
        return result.scalar_one_or_none() is not None

    def _model_to_record(self, model: DatasetFileModel) -> DatasetFileRecord:
        return DatasetFileRecord(
            id=model.id,
            dataset_id=model.dataset_id,
            source_id=model.source_id,
            added_at=model.added_at,
        )
