"""Tests for dataset loader."""

import json
import tempfile
from pathlib import Path

import pytest

from ragmax.evaluation.loader import DatasetLoader
from ragmax.evaluation.models import TestDataset


class TestDatasetLoader:
    """Tests for DatasetLoader."""

    def test_load_from_json_success(self):
        """Test successful loading of a dataset from JSON."""

        json_data = {
            "name": "Test Dataset",
            "description": "A test dataset",
            "version": "1.0.0",
            "test_cases": [
                {
                    "id": "tc_001",
                    "question": "What is Python?",
                    "expected_answer": "Python is a programming language",
                    "ground_truth_docs": ["doc_001", "doc_002"],
                    "metadata": {"difficulty": "easy"},
                },
                {
                    "id": "tc_002",
                    "question": "What is FastAPI?",
                    "ground_truth_docs": ["doc_003"],
                },
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_data, f)
            temp_path = f.name

        try:
            dataset = DatasetLoader.load_from_json(temp_path)

            assert dataset.name == "Test Dataset"
            assert dataset.description == "A test dataset"
            assert dataset.version == "1.0.0"
            assert len(dataset.test_cases) == 2

            # Check first test case
            tc1 = dataset.test_cases[0]
            assert tc1.id == "tc_001"
            assert tc1.question == "What is Python?"
            assert tc1.expected_answer == "Python is a programming language"
            assert tc1.ground_truth_docs == ["doc_001", "doc_002"]
            assert tc1.metadata["difficulty"] == "easy"

            # Check second test case
            tc2 = dataset.test_cases[1]
            assert tc2.id == "tc_002"
            assert tc2.question == "What is FastAPI?"
            assert tc2.expected_answer is None
            assert tc2.ground_truth_docs == ["doc_003"]

        finally:
            Path(temp_path).unlink()

    def test_load_from_json_file_not_found(self):
        """Test loading from non-existent file."""

        with pytest.raises(FileNotFoundError):
            DatasetLoader.load_from_json("/nonexistent/file.json")

    def test_load_from_json_invalid_json(self):
        """Test loading invalid JSON."""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid JSON"):
                DatasetLoader.load_from_json(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_from_json_missing_name(self):
        """Test loading JSON without required 'name' field."""

        json_data = {"test_cases": []}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_data, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="must contain 'name' field"):
                DatasetLoader.load_from_json(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_from_json_missing_test_cases(self):
        """Test loading JSON without 'test_cases' field."""

        json_data = {"name": "Test"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_data, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="must contain 'test_cases' array"):
                DatasetLoader.load_from_json(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_from_json_invalid_test_case(self):
        """Test loading JSON with invalid test case (missing question)."""

        json_data = {
            "name": "Test",
            "test_cases": [
                {"id": "tc_001"}  # Missing 'question'
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_data, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid test case"):
                DatasetLoader.load_from_json(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_save_to_json(self):
        """Test saving a dataset to JSON."""

        from ragmax.evaluation.models import EvalTestCase

        dataset = TestDataset(
            id="dataset_001",
            name="Test Dataset",
            description="Test",
            test_cases=[
                EvalTestCase(
                    id="tc_001",
                    question="Question 1?",
                    expected_answer="Answer 1",
                    ground_truth_docs=["doc_001"],
                    metadata={"difficulty": "easy"},
                )
            ],
            version="1.0.0",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "output.json"
            DatasetLoader.save_to_json(dataset, output_path)

            assert output_path.exists()

            # Load and verify
            with open(output_path) as f:
                data = json.load(f)

            assert data["name"] == "Test Dataset"
            assert data["version"] == "1.0.0"
            assert len(data["test_cases"]) == 1
            assert data["test_cases"][0]["question"] == "Question 1?"

    def test_load_with_auto_generated_ids(self):
        """Test loading dataset where IDs are auto-generated."""

        json_data = {
            "name": "Test",
            "test_cases": [
                {"question": "Q1?"},  # No ID provided
                {"question": "Q2?"},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_data, f)
            temp_path = f.name

        try:
            dataset = DatasetLoader.load_from_json(temp_path)

            assert len(dataset.test_cases) == 2
            # IDs should be auto-generated
            assert dataset.test_cases[0].id.startswith("tc_")
            assert dataset.test_cases[1].id.startswith("tc_")
            # IDs should be unique
            assert dataset.test_cases[0].id != dataset.test_cases[1].id

        finally:
            Path(temp_path).unlink()
