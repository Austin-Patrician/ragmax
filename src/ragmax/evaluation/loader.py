"""JSON dataset loader for evaluation test datasets."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ragmax.evaluation.models import EvalTestCase, TestDataset


class DatasetLoader:
    """Load test datasets from JSON files."""

    @staticmethod
    def load_from_json(file_path: str | Path) -> TestDataset:
        """
        Load a test dataset from a JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            TestDataset instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON is invalid or missing required fields

        Expected JSON format:
        {
            "name": "Dataset Name",
            "description": "Description",
            "version": "1.0.0",
            "test_cases": [
                {
                    "id": "tc_001",
                    "question": "Question text",
                    "expected_answer": "Expected answer",
                    "ground_truth_docs": ["doc_id1", "doc_id2"],
                    "metadata": {
                        "difficulty": "easy",
                        "category": "auth"
                    }
                }
            ]
        }
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in dataset file: {e}")

        # Validate required fields
        if "name" not in data:
            raise ValueError("Dataset JSON must contain 'name' field")
        if "test_cases" not in data or not isinstance(data["test_cases"], list):
            raise ValueError("Dataset JSON must contain 'test_cases' array")

        # Parse test cases
        test_cases = []
        for idx, tc_data in enumerate(data["test_cases"]):
            try:
                test_case = DatasetLoader._parse_test_case(tc_data)
                test_cases.append(test_case)
            except Exception as e:
                raise ValueError(f"Invalid test case at index {idx}: {e}")

        # Create dataset
        dataset = TestDataset(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            description=data.get("description", ""),
            test_cases=test_cases,
            version=data.get("version", "1.0.0"),
            created_at=datetime.now(),
        )

        return dataset

    @staticmethod
    def _parse_test_case(data: dict[str, Any]) -> EvalTestCase:
        """Parse a single test case from JSON data."""

        if "question" not in data:
            raise ValueError("Test case must contain 'question' field")

        return EvalTestCase(
            id=data.get("id", f"tc_{uuid.uuid4().hex[:8]}"),
            question=data["question"],
            expected_answer=data.get("expected_answer"),
            ground_truth_docs=data.get("ground_truth_docs", []),
            metadata=data.get("metadata", {}),
            created_at=datetime.now(),
        )

    @staticmethod
    def save_to_json(dataset: TestDataset, file_path: str | Path) -> None:
        """
        Save a test dataset to a JSON file.

        Args:
            dataset: TestDataset to save
            file_path: Output file path
        """

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "id": dataset.id,
            "name": dataset.name,
            "description": dataset.description,
            "version": dataset.version,
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

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
