"""Evaluation API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ragmax.api.auth_dependencies import ROUTE_EVALUATION, require_route_permission
from ragmax.evaluation.models import TestDataset
from ragmax.evaluation.repository import EvaluationRepository
from ragmax.infrastructure.db.session import get_db_session

router = APIRouter(
    prefix="/evaluation",
    tags=["evaluation"],
    dependencies=[Depends(require_route_permission(ROUTE_EVALUATION))],
)


# ==================== Dataset Endpoints ====================


@router.get("/datasets")
async def list_datasets(
    limit: int = 100,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    """List all test datasets."""
    repo = EvaluationRepository(db)
    datasets = await repo.list_datasets(limit=limit)

    return {
        "datasets": [
            {
                "id": ds.id,
                "name": ds.name,
                "description": ds.description,
                "version": ds.version,
                "test_case_count": len(ds.test_cases),
                "created_at": ds.created_at.isoformat(),
            }
            for ds in datasets
        ]
    }


@router.get("/datasets/{dataset_id}")
async def get_dataset(
    dataset_id: str,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    """Get a specific dataset with all test cases."""
    repo = EvaluationRepository(db)
    dataset = await repo.get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "version": dataset.version,
        "created_at": dataset.created_at.isoformat(),
        "test_cases": [
            {
                "id": tc.id,
                "question": tc.question,
                "expected_answer": tc.expected_answer,
                "ground_truth_docs": tc.ground_truth_docs,
                "metadata": tc.metadata,
            }
            for tc in dataset.test_cases
        ],
    }


@router.post("/datasets")
async def create_dataset(
    dataset: dict,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    """Create a new test dataset."""
    from datetime import datetime
    from uuid import uuid4

    from ragmax.evaluation.models import EvalTestCase

    # Parse dataset
    test_cases = [
        EvalTestCase(
            id=tc.get("id", f"tc_{uuid4().hex[:8]}"),
            question=tc["question"],
            expected_answer=tc.get("expected_answer"),
            ground_truth_docs=tc.get("ground_truth_docs", []),
            metadata=tc.get("metadata", {}),
            created_at=datetime.now(),
        )
        for tc in dataset.get("test_cases", [])
    ]

    new_dataset = TestDataset(
        id=str(uuid4()),
        name=dataset["name"],
        description=dataset.get("description", ""),
        test_cases=test_cases,
        version=dataset.get("version", "1.0.0"),
        created_at=datetime.now(),
    )

    repo = EvaluationRepository(db)
    await repo.create_dataset(new_dataset)

    return {"id": new_dataset.id, "message": "Dataset created successfully"}


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    """Delete a dataset."""
    repo = EvaluationRepository(db)
    await repo.delete_dataset(dataset_id)
    return {"message": "Dataset deleted successfully"}


# ==================== Experiment Endpoints ====================


@router.get("/experiments")
async def list_experiments(
    dataset_id: str | None = None,
    limit: int = 50,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    """List evaluation experiments."""
    repo = EvaluationRepository(db)
    await repo.list_experiments(dataset_id=dataset_id, limit=limit)

    # For now return empty since we need to implement full reconstruction
    # TODO: Implement full experiment loading in repository
    return {"experiments": []}


@router.get("/experiments/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    """Get experiment details with results."""
    repo = EvaluationRepository(db)
    experiment = await repo.get_experiment(experiment_id)

    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    # TODO: Implement full serialization
    return {"experiment": None}


@router.post("/experiments/run")
async def run_experiment(
    request: dict,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    """Run a new evaluation experiment."""
    # TODO: Implement experiment execution
    # This will require initializing RAGEvaluator with proper dependencies

    return {
        "message": "Experiment execution not yet implemented",
        "status": "pending",
    }


# ==================== Version Management ====================


@router.get("/datasets/{dataset_name}/versions")
async def list_dataset_versions(
    dataset_name: str,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    """List all versions of a dataset."""
    repo = EvaluationRepository(db)
    versions = await repo.list_dataset_versions(dataset_name)

    return {
        "versions": [
            {
                "id": ds.id,
                "version": ds.version,
                "created_at": ds.created_at.isoformat(),
            }
            for ds in versions
        ]
    }


@router.get("/datasets/{dataset_name}/compare")
async def compare_dataset_versions(
    dataset_name: str,
    version_a: str,
    version_b: str,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
):
    """Compare two versions of a dataset."""
    repo = EvaluationRepository(db)
    comparison = await repo.compare_dataset_versions(dataset_name, version_a, version_b)

    return comparison
