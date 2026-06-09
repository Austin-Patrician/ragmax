from abc import ABC, abstractmethod

from ragmax.domain.datasets.records import DatasetFileRecord, DatasetRecord


class DatasetRepository(ABC):
    @abstractmethod
    async def create(self, dataset: DatasetRecord) -> DatasetRecord:
        pass

    @abstractmethod
    async def get(self, dataset_id: str) -> DatasetRecord | None:
        pass

    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0) -> tuple[DatasetRecord, ...]:
        pass

    @abstractmethod
    async def update(self, dataset: DatasetRecord) -> DatasetRecord:
        pass

    @abstractmethod
    async def delete(self, dataset_id: str) -> bool:
        pass


class DatasetFileRepository(ABC):
    @abstractmethod
    async def add_files(
        self, dataset_id: str, source_ids: tuple[str, ...]
    ) -> tuple[DatasetFileRecord, ...]:
        pass

    @abstractmethod
    async def remove_file(self, dataset_id: str, source_id: str) -> bool:
        pass

    @abstractmethod
    async def list_by_dataset(self, dataset_id: str) -> tuple[DatasetFileRecord, ...]:
        pass

    @abstractmethod
    async def list_by_source(self, source_id: str) -> tuple[DatasetFileRecord, ...]:
        pass

    @abstractmethod
    async def exists(self, dataset_id: str, source_id: str) -> bool:
        pass
