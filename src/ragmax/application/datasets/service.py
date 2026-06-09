from datetime import UTC, datetime
from uuid import uuid4

from ragmax.application.datasets.dtos import (
    AddFilesToDatasetCommand,
    CreateDatasetCommand,
    DatasetWithFiles,
    RemoveFileFromDatasetCommand,
    UpdateDatasetCommand,
)
from ragmax.core.exceptions import InvalidRequestError, NotFoundError
from ragmax.domain.datasets.ports import DatasetFileRepository, DatasetRepository
from ragmax.domain.datasets.records import DatasetFileRecord, DatasetRecord


class DatasetService:
    def __init__(
        self,
        dataset_repo: DatasetRepository,
        dataset_file_repo: DatasetFileRepository,
    ) -> None:
        self._dataset_repo = dataset_repo
        self._dataset_file_repo = dataset_file_repo

    async def create_dataset(self, command: CreateDatasetCommand) -> DatasetRecord:
        dataset_id = command.dataset_id or f"ds_{uuid4().hex}"
        dataset = DatasetRecord(
            dataset_id=dataset_id,
            name=command.name,
            description=command.description,
            config=command.config,
            metadata=command.metadata,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        return await self._dataset_repo.create(dataset)

    async def get_dataset(self, dataset_id: str) -> DatasetRecord:
        dataset = await self._dataset_repo.get(dataset_id)
        if dataset is None:
            raise NotFoundError(f"Dataset not found: {dataset_id}")
        return dataset

    async def list_datasets(self, limit: int = 100, offset: int = 0) -> tuple[DatasetRecord, ...]:
        return await self._dataset_repo.list(limit=limit, offset=offset)

    async def update_dataset(self, command: UpdateDatasetCommand) -> DatasetRecord:
        dataset = await self.get_dataset(command.dataset_id)

        updated = DatasetRecord(
            dataset_id=dataset.dataset_id,
            name=command.name if command.name is not None else dataset.name,
            description=command.description if command.description is not None else dataset.description,
            config=command.config if command.config is not None else dataset.config,
            metadata=command.metadata if command.metadata is not None else dataset.metadata,
            created_at=dataset.created_at,
            updated_at=datetime.now(UTC),
        )
        return await self._dataset_repo.update(updated)

    async def delete_dataset(self, dataset_id: str) -> bool:
        dataset = await self.get_dataset(dataset_id)
        return await self._dataset_repo.delete(dataset.dataset_id)

    async def add_files_to_dataset(
        self, command: AddFilesToDatasetCommand
    ) -> tuple[DatasetFileRecord, ...]:
        # Verify dataset exists
        await self.get_dataset(command.dataset_id)

        if not command.source_ids:
            raise InvalidRequestError("At least one source_id is required")

        return await self._dataset_file_repo.add_files(command.dataset_id, command.source_ids)

    async def remove_file_from_dataset(self, command: RemoveFileFromDatasetCommand) -> bool:
        # Verify dataset exists
        await self.get_dataset(command.dataset_id)

        success = await self._dataset_file_repo.remove_file(
            command.dataset_id, command.source_id
        )
        if not success:
            raise NotFoundError(
                f"File {command.source_id} not found in dataset {command.dataset_id}"
            )
        return success

    async def list_dataset_files(self, dataset_id: str) -> tuple[DatasetFileRecord, ...]:
        # Verify dataset exists
        await self.get_dataset(dataset_id)
        return await self._dataset_file_repo.list_by_dataset(dataset_id)

    async def get_dataset_with_files(self, dataset_id: str) -> DatasetWithFiles:
        dataset = await self.get_dataset(dataset_id)
        files = await self._dataset_file_repo.list_by_dataset(dataset_id)
        return DatasetWithFiles(
            dataset=dataset,
            files=files,
            file_count=len(files),
        )

    async def list_datasets_by_source(self, source_id: str) -> tuple[DatasetFileRecord, ...]:
        return await self._dataset_file_repo.list_by_source(source_id)
