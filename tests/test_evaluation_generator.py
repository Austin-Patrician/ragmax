"""Tests for synthetic data generator."""

import json
from unittest.mock import AsyncMock, Mock

import pytest

from ragmax.evaluation.generator import SyntheticDataGenerator
from ragmax.infrastructure.llm.client import LLMResponse


class TestSyntheticDataGenerator:
    """Tests for SyntheticDataGenerator."""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client."""
        client = Mock()
        client.generate = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_generate_from_single_document_chinese(self, mock_llm_client):
        """Test generating test cases from a single document in Chinese."""

        # Mock LLM response
        qa_pairs = [
            {
                "question": "什么是 Python？",
                "answer": "Python 是一种编程语言。",
                "difficulty": "easy",
                "category": "定义",
            },
            {
                "question": "Python 有哪些特点？",
                "answer": "Python 具有简洁、易读、功能强大的特点。",
                "difficulty": "medium",
                "category": "特征",
            },
        ]

        mock_llm_client.generate.return_value = LLMResponse(
            content=json.dumps(qa_pairs, ensure_ascii=False),
            model="test-model",
            usage={"total_tokens": 100},
        )

        generator = SyntheticDataGenerator(mock_llm_client)

        documents = [("doc_001", "Python 是一种编程语言，具有简洁、易读、功能强大的特点。")]

        test_cases = await generator.generate_from_documents(
            documents=documents, num_cases_per_doc=2, difficulty="mixed", language="zh"
        )

        assert len(test_cases) == 2

        # Check first test case
        tc1 = test_cases[0]
        assert tc1.question == "什么是 Python？"
        assert tc1.expected_answer == "Python 是一种编程语言。"
        assert tc1.ground_truth_docs == ["doc_001"]
        assert tc1.metadata["difficulty"] == "easy"
        assert tc1.metadata["category"] == "定义"
        assert tc1.metadata["synthetic"] is True
        assert tc1.metadata["language"] == "zh"

        # Check second test case
        tc2 = test_cases[1]
        assert tc2.question == "Python 有哪些特点？"
        assert tc2.metadata["difficulty"] == "medium"

    @pytest.mark.asyncio
    async def test_generate_from_single_document_english(self, mock_llm_client):
        """Test generating test cases from a single document in English."""

        qa_pairs = [
            {
                "question": "What is Python?",
                "answer": "Python is a programming language.",
                "difficulty": "easy",
                "category": "definition",
            }
        ]

        mock_llm_client.generate.return_value = LLMResponse(
            content=json.dumps(qa_pairs), model="test-model", usage={"total_tokens": 50}
        )

        generator = SyntheticDataGenerator(mock_llm_client)

        documents = [("doc_001", "Python is a programming language.")]

        test_cases = await generator.generate_from_documents(
            documents=documents, num_cases_per_doc=1, difficulty="easy", language="en"
        )

        assert len(test_cases) == 1
        assert test_cases[0].question == "What is Python?"
        assert test_cases[0].metadata["language"] == "en"

    @pytest.mark.asyncio
    async def test_generate_from_multiple_documents(self, mock_llm_client):
        """Test generating from multiple documents."""

        # Mock different responses for different documents
        responses = [
            LLMResponse(
                content=json.dumps(
                    [{"question": "Q1 from doc1?", "answer": "A1", "difficulty": "easy", "category": "test"}]
                ),
                model="test",
                usage={"total_tokens": 50},
            ),
            LLMResponse(
                content=json.dumps(
                    [{"question": "Q1 from doc2?", "answer": "A2", "difficulty": "medium", "category": "test"}]
                ),
                model="test",
                usage={"total_tokens": 50},
            ),
        ]

        mock_llm_client.generate.side_effect = responses

        generator = SyntheticDataGenerator(mock_llm_client)

        documents = [("doc_001", "Content 1"), ("doc_002", "Content 2")]

        test_cases = await generator.generate_from_documents(documents=documents, num_cases_per_doc=1)

        assert len(test_cases) == 2
        assert test_cases[0].ground_truth_docs == ["doc_001"]
        assert test_cases[1].ground_truth_docs == ["doc_002"]

    @pytest.mark.asyncio
    async def test_generate_with_llm_failure(self, mock_llm_client):
        """Test handling LLM generation failure."""

        # First document succeeds, second fails
        mock_llm_client.generate.side_effect = [
            LLMResponse(
                content=json.dumps([{"question": "Q?", "answer": "A", "difficulty": "easy", "category": "test"}]),
                model="test",
                usage={"total_tokens": 50},
            ),
            Exception("LLM error"),
        ]

        generator = SyntheticDataGenerator(mock_llm_client)

        documents = [("doc_001", "Content 1"), ("doc_002", "Content 2")]

        test_cases = await generator.generate_from_documents(documents=documents, num_cases_per_doc=1)

        # Should still get result from successful document
        assert len(test_cases) == 1
        assert test_cases[0].ground_truth_docs == ["doc_001"]

    @pytest.mark.asyncio
    async def test_generate_with_invalid_json_response(self, mock_llm_client):
        """Test handling invalid JSON response from LLM."""

        mock_llm_client.generate.return_value = LLMResponse(
            content="Invalid JSON", model="test", usage={"total_tokens": 10}
        )

        generator = SyntheticDataGenerator(mock_llm_client)

        documents = [("doc_001", "Content")]

        test_cases = await generator.generate_from_documents(documents=documents, num_cases_per_doc=1)

        # Should return empty list on parse failure
        assert len(test_cases) == 0

    @pytest.mark.asyncio
    async def test_generate_truncates_long_content(self, mock_llm_client):
        """Test that very long content is truncated."""

        mock_llm_client.generate.return_value = LLMResponse(
            content=json.dumps([{"question": "Q?", "answer": "A", "difficulty": "easy", "category": "test"}]),
            model="test",
            usage={"total_tokens": 50},
        )

        generator = SyntheticDataGenerator(mock_llm_client)

        # Create very long content (> 4000 chars)
        long_content = "A" * 5000

        documents = [("doc_001", long_content)]

        await generator.generate_from_documents(documents=documents, num_cases_per_doc=1)

        # Verify LLM was called
        assert mock_llm_client.generate.called

        # Check that the content passed to LLM was truncated
        call_args = mock_llm_client.generate.call_args
        messages = call_args[0][0]
        prompt_content = messages[0]["content"]

        # Prompt should contain truncation marker
        assert "截断" in prompt_content or "truncated" in prompt_content

    @pytest.mark.asyncio
    async def test_generate_respects_num_cases_limit(self, mock_llm_client):
        """Test that only requested number of cases are returned."""

        # LLM returns more cases than requested
        qa_pairs = [
            {"question": f"Q{i}?", "answer": f"A{i}", "difficulty": "easy", "category": "test"} for i in range(10)
        ]

        mock_llm_client.generate.return_value = LLMResponse(
            content=json.dumps(qa_pairs), model="test", usage={"total_tokens": 200}
        )

        generator = SyntheticDataGenerator(mock_llm_client)

        documents = [("doc_001", "Content")]

        test_cases = await generator.generate_from_documents(documents=documents, num_cases_per_doc=3)

        # Should only return 3 cases even though LLM returned 10
        assert len(test_cases) == 3
