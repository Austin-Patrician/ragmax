"""Repository for evaluation data persistence."""

import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ragmax.evaluation.models import (
    EvalResult,
    EvalTestCase,
    ExperimentRun,
    TestDataset,
)
from ragmax.infrastructure.db.models import (
    EvalDatasetModel,
    EvalExperimentModel,
    EvalResultModel,
    EvalTestCaseModel,
)


class EvaluationRepository:
    """Repository for evaluation data persistence."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # ==================== Dataset Operations ====================

    async def create_dataset(self, dataset: TestDataset) -> None:
        """Create a new dataset with test cases."""
        await self.save_dataset(dataset)

    async def save_dataset(self, dataset: TestDataset) -> None:
        """Save a test dataset with its test cases."""

        # Save dataset
        dataset_stmt = insert(EvalDatasetModel).values(
            id=UUID(dataset.id) if isinstance(dataset.id, str) else dataset.id,
            name=dataset.name,
            description=dataset.description,
            version=dataset.version,
            created_at=dataset.created_at,
        )
        await self.db.execute(dataset_stmt)

        # Save test cases
        if dataset.test_cases:
            test_case_values = [
                {
                    "id": tc.id,
                    "dataset_id": UUID(dataset.id) if isinstance(dataset.id, str) else dataset.id,
                    "question": tc.question,
                    "expected_answer": tc.expected_answer,
                    "ground_truth_docs": tc.ground_truth_docs,
                    "metadata": tc.metadata,
                    "created_at": tc.created_at,
                }
                for tc in dataset.test_cases
            ]
            await self.db.execute(insert(EvalTestCaseModel).values(test_case_values))

        await self.db.commit()

    async def get_dataset(self, dataset_id: str) -> TestDataset | None:
        """Load a dataset with its test cases."""

        # Load dataset
        dataset_stmt = select(EvalDatasetModel).where(EvalDatasetModel.id == UUID(dataset_id))
        dataset_result = await self.db.execute(dataset_stmt)
        dataset_row = dataset_result.scalar_one_or_none()

        if not dataset_row:
            return None

        # Load test cases
        test_cases_stmt = select(EvalTestCaseModel).where(EvalTestCaseModel.dataset_id == UUID(dataset_id))
        test_cases_result = await self.db.execute(test_cases_stmt)
        test_case_rows = test_cases_result.scalars().all()

        test_cases = [
            EvalTestCase(
                id=row.id,
                question=row.question,
                expected_answer=row.expected_answer,
                ground_truth_docs=row.ground_truth_docs,
                metadata=row.test_metadata,
                created_at=row.created_at,
            )
            for row in test_case_rows
        ]

        return TestDataset(
            id=str(dataset_row.id),
            name=dataset_row.name,
            description=dataset_row.description or "",
            test_cases=test_cases,
            version=dataset_row.version,
            created_at=dataset_row.created_at,
        )

    async def get_dataset_by_name(self, name: str, version: str = "1.0.0") -> TestDataset | None:
        """Get dataset by name and version."""

        stmt = select(EvalDatasetModel).where(
            EvalDatasetModel.name == name,
            EvalDatasetModel.version == version,
        )
        result = await self.db.execute(stmt)
        dataset_row = result.scalar_one_or_none()

        if not dataset_row:
            return None

        return await self.get_dataset(str(dataset_row.id))

    async def list_datasets(self, limit: int = 100) -> Sequence[TestDataset]:
        """List all datasets (without test cases for efficiency)."""

        stmt = select(EvalDatasetModel).order_by(EvalDatasetModel.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        rows = result.scalars().all()

        return [
            TestDataset(
                id=str(row.id),
                name=row.name,
                description=row.description or "",
                test_cases=[],  # Don't load test cases for list view
                version=row.version,
                created_at=row.created_at,
            )
            for row in rows
        ]

    async def update_dataset(self, dataset_id: str, name: str | None = None, description: str | None = None) -> None:
        """Update dataset metadata."""

        values = {}
        if name is not None:
            values["name"] = name
        if description is not None:
            values["description"] = description

        if values:
            stmt = update(EvalDatasetModel).where(EvalDatasetModel.id == UUID(dataset_id)).values(**values)
            await self.db.execute(stmt)
            await self.db.commit()

    async def delete_dataset(self, dataset_id: str) -> None:
        """Delete a dataset and all its test cases."""

        # Delete test cases first (due to foreign key)
        await self.db.execute(delete(EvalTestCaseModel).where(EvalTestCaseModel.dataset_id == UUID(dataset_id)))

        # Delete dataset
        await self.db.execute(delete(EvalDatasetModel).where(EvalDatasetModel.id == UUID(dataset_id)))

        await self.db.commit()

    # ==================== Test Case Operations ====================

    async def add_test_case(self, dataset_id: str, test_case: EvalTestCase) -> None:
        """Add a test case to an existing dataset."""

        stmt = insert(EvalTestCaseModel).values(
            id=test_case.id,
            dataset_id=UUID(dataset_id),
            question=test_case.question,
            expected_answer=test_case.expected_answer,
            ground_truth_docs=test_case.ground_truth_docs,
            metadata=test_case.metadata,
            created_at=test_case.created_at,
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def update_test_case(
        self,
        test_case_id: str,
        question: str | None = None,
        expected_answer: str | None = None,
        ground_truth_docs: list[str] | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Update a test case."""

        values = {}
        if question is not None:
            values["question"] = question
        if expected_answer is not None:
            values["expected_answer"] = expected_answer
        if ground_truth_docs is not None:
            values["ground_truth_docs"] = ground_truth_docs
        if metadata is not None:
            values["test_metadata"] = metadata

        if values:
            stmt = update(EvalTestCaseModel).where(EvalTestCaseModel.id == test_case_id).values(**values)
            await self.db.execute(stmt)
            await self.db.commit()

    async def delete_test_case(self, test_case_id: str) -> None:
        """Delete a test case."""

        await self.db.execute(delete(EvalTestCaseModel).where(EvalTestCaseModel.id == test_case_id))
        await self.db.commit()

    # ==================== Version Management ====================

    async def list_dataset_versions(self, dataset_name: str) -> Sequence[TestDataset]:
        """List all versions of a dataset by name."""

        stmt = (
            select(EvalDatasetModel)
            .where(EvalDatasetModel.name == dataset_name)
            .order_by(EvalDatasetModel.version.desc())
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()

        return [
            TestDataset(
                id=str(row.id),
                name=row.name,
                description=row.description or "",
                test_cases=[],  # Don't load test cases for list view
                version=row.version,
                created_at=row.created_at,
            )
            for row in rows
        ]

    async def create_new_version(
        self,
        source_dataset_id: str,
        new_version: str,
        description: str | None = None,
    ) -> TestDataset:
        """
        Create a new version of a dataset by copying an existing one.

        Args:
            source_dataset_id: ID of the dataset to copy
            new_version: New version string
            description: Optional new description

        Returns:
            Newly created TestDataset

        Raises:
            ValueError: If source dataset doesn't exist or version already exists
        """

        # Load source dataset
        source = await self.get_dataset(source_dataset_id)
        if not source:
            raise ValueError(f"Source dataset not found: {source_dataset_id}")

        # Check if version already exists
        existing = await self.get_dataset_by_name(source.name, new_version)
        if existing:
            raise ValueError(f"Version {new_version} already exists for dataset {source.name}")

        # Create new dataset with same test cases
        new_dataset = TestDataset(
            id=str(uuid.uuid4()),
            name=source.name,
            description=description or source.description,
            test_cases=[
                EvalTestCase(
                    id=f"{tc.id}_v{new_version}",  # Make IDs unique
                    question=tc.question,
                    expected_answer=tc.expected_answer,
                    ground_truth_docs=tc.ground_truth_docs,
                    metadata={**tc.metadata, "copied_from": tc.id},
                    created_at=datetime.now(),
                )
                for tc in source.test_cases
            ],
            version=new_version,
            created_at=datetime.now(),
        )

        await self.save_dataset(new_dataset)
        return new_dataset

    async def compare_dataset_versions(
        self,
        dataset_name: str,
        version_a: str,
        version_b: str,
    ) -> dict:
        """
        Compare two versions of a dataset.

        Returns:
            Dict with comparison statistics:
            - added: number of test cases added in version_b
            - removed: number of test cases removed from version_a
            - modified: number of test cases with different questions/answers
            - unchanged: number of test cases that are identical
        """

        dataset_a = await self.get_dataset_by_name(dataset_name, version_a)
        dataset_b = await self.get_dataset_by_name(dataset_name, version_b)

        if not dataset_a or not dataset_b:
            raise ValueError(f"Could not find both versions: {version_a}, {version_b}")

        # Create maps by test case ID (without version suffix)
        def get_base_id(tc_id: str) -> str:
            # Remove version suffix if present
            return tc_id.split("_v")[0] if "_v" in tc_id else tc_id

        cases_a = {get_base_id(tc.id): tc for tc in dataset_a.test_cases}
        cases_b = {get_base_id(tc.id): tc for tc in dataset_b.test_cases}

        ids_a = set(cases_a.keys())
        ids_b = set(cases_b.keys())

        added = len(ids_b - ids_a)
        removed = len(ids_a - ids_b)

        # Check for modifications in common test cases
        common = ids_a & ids_b
        modified = 0
        for tc_id in common:
            tc_a = cases_a[tc_id]
            tc_b = cases_b[tc_id]
            if (
                tc_a.question != tc_b.question
                or tc_a.expected_answer != tc_b.expected_answer
                or tc_a.ground_truth_docs != tc_b.ground_truth_docs
            ):
                modified += 1

        unchanged = len(common) - modified

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
            "unchanged": unchanged,
            "total_a": len(cases_a),
            "total_b": len(cases_b),
        }

    # ==================== Experiment Operations ====================

    async def save_experiment(self, experiment: ExperimentRun) -> None:
        """Save an experiment run with its results."""

        # Convert config and metrics_summary to dicts
        config_dict = asdict(experiment.config)
        metrics_dict = asdict(experiment.metrics_summary) if experiment.metrics_summary else None

        # Save experiment
        experiment_stmt = insert(EvalExperimentModel).values(
            id=UUID(experiment.id) if isinstance(experiment.id, str) else experiment.id,
            name=experiment.name,
            dataset_id=UUID(experiment.dataset_id) if isinstance(experiment.dataset_id, str) else experiment.dataset_id,
            config=config_dict,
            metrics_summary=metrics_dict,
            status=experiment.status,
            started_at=experiment.started_at,
            completed_at=experiment.completed_at,
            duration_seconds=experiment.duration_seconds,
        )
        await self.db.execute(experiment_stmt)

        # Save results
        if experiment.results:
            result_values = [
                {
                    "id": uuid.uuid4(),
                    "experiment_id": UUID(experiment.id) if isinstance(experiment.id, str) else experiment.id,
                    "test_case_id": result.test_case_id,
                    "retrieval_result": asdict(result.retrieval) if result.retrieval else None,
                    "generation_result": asdict(result.generation) if result.generation else None,
                    "metrics": result.metrics,
                    "passed": result.passed,
                    "error": result.error,
                }
                for result in experiment.results
            ]
            await self.db.execute(insert(EvalResultModel).values(result_values))

        await self.db.commit()

    async def get_experiment(self, experiment_id: str) -> ExperimentRun | None:
        """Load an experiment with its results."""

        # Load experiment
        experiment_stmt = select(EvalExperimentModel).where(EvalExperimentModel.id == UUID(experiment_id))
        experiment_result = await self.db.execute(experiment_stmt)
        experiment_row = experiment_result.scalar_one_or_none()

        if not experiment_row:
            return None

        # Load results
        results_stmt = select(EvalResultModel).where(EvalResultModel.experiment_id == UUID(experiment_id))
        results_result = await self.db.execute(results_stmt)
        result_rows = results_result.scalars().all()

        # Convert back to domain models (simplified - would need full reconstruction)
        # This is a placeholder - full implementation would reconstruct all nested objects

        return None  # TODO: Implement full reconstruction

    async def list_experiments(
        self,
        dataset_id: str | None = None,
        limit: int = 50,
    ) -> Sequence[ExperimentRun]:
        """List experiments, optionally filtered by dataset."""

        stmt = select(EvalExperimentModel).order_by(EvalExperimentModel.started_at.desc()).limit(limit)

        if dataset_id:
            stmt = stmt.where(EvalExperimentModel.dataset_id == UUID(dataset_id))

        result = await self.db.execute(stmt)
        rows = result.scalars().all()

        # TODO: Convert to ExperimentRun objects
        return []

