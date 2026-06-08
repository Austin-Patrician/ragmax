from types import SimpleNamespace

import pytest

from ragmax.core.exceptions import ConfigurationError, ExternalServiceError
from ragmax.infrastructure.indexing.embeddings import openai_embedding_provider
from ragmax.infrastructure.indexing.embeddings.openai_embedding_provider import (
    OpenAIEmbeddingProvider,
)


class FakeEmbeddingsResource:
    calls: list[dict[str, object]] = []
    fail_batch_with_empty_data: bool = False
    fail_single: bool = False

    async def create(self, **kwargs: object):
        self.calls.append(kwargs)
        input_value = kwargs["input"]
        if isinstance(input_value, list):
            if self.fail_batch_with_empty_data:
                raise ValueError("No embedding data received")
            return SimpleNamespace(
                data=[SimpleNamespace(embedding=[1.0, 0.0, 0.0]) for _ in input_value]
            )
        if self.fail_single:
            raise RuntimeError("status 404: not found")
        return SimpleNamespace(data=[SimpleNamespace(embedding=[1.0, 0.0, 0.0])])


class FakeAsyncOpenAI:
    calls: list[dict[str, object]] = []
    embeddings_resource = FakeEmbeddingsResource()

    def __init__(self, **kwargs: object) -> None:
        self.calls.append(kwargs)
        self.embeddings = self.embeddings_resource


@pytest.fixture(autouse=True)
def reset_fake_client(monkeypatch: pytest.MonkeyPatch):
    FakeAsyncOpenAI.calls.clear()
    FakeAsyncOpenAI.embeddings_resource.calls.clear()
    FakeAsyncOpenAI.embeddings_resource.fail_batch_with_empty_data = False
    FakeAsyncOpenAI.embeddings_resource.fail_single = False
    monkeypatch.setattr(openai_embedding_provider, "AsyncOpenAI", FakeAsyncOpenAI)


def test_openai_embedding_provider_passes_base_url() -> None:
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        model_name="text-embedding-3-small",
        base_url="https://embeddings.example.com/v1",
        dimension=3,
    )

    assert provider.dimension == 3
    assert provider.model_name == "text-embedding-3-small"
    assert FakeAsyncOpenAI.calls == [
        {
            "api_key": "test-key",
            "base_url": "https://embeddings.example.com/v1",
        }
    ]


def test_openai_embedding_provider_normalizes_embeddings_base_url() -> None:
    OpenAIEmbeddingProvider(
        api_key="test-key",
        model_name="text-embedding-3-small",
        base_url="https://embeddings.example.com/v1/embeddings/",
        dimension=3,
    )

    assert FakeAsyncOpenAI.calls[0]["base_url"] == "https://embeddings.example.com/v1"


@pytest.mark.asyncio
async def test_openai_embedding_provider_uses_batch_input_when_supported() -> None:
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        model_name="text-embedding-3-small",
        base_url="https://embeddings.example.com/v1",
        dimension=3,
        batch_size=8,
    )

    embeddings = await provider.embed_texts(["one", "two", "three"])

    assert len(embeddings) == 3
    assert FakeAsyncOpenAI.embeddings_resource.calls == [
        {
            "model": "text-embedding-3-small",
            "input": ["one", "two", "three"],
            "dimensions": 3,
        }
    ]


@pytest.mark.asyncio
async def test_openai_embedding_provider_falls_back_to_single_inputs_when_batch_is_empty() -> None:
    FakeAsyncOpenAI.embeddings_resource.fail_batch_with_empty_data = True
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        model_name="text-embedding-3-small",
        base_url="https://embeddings.example.com/v1",
        dimension=3,
        batch_size=8,
    )

    embeddings = await provider.embed_texts(["one", "two"])

    assert len(embeddings) == 2
    assert FakeAsyncOpenAI.embeddings_resource.calls == [
        {
            "model": "text-embedding-3-small",
            "input": ["one", "two"],
            "dimensions": 3,
        },
        {
            "model": "text-embedding-3-small",
            "input": "one",
            "dimensions": 3,
        },
        {
            "model": "text-embedding-3-small",
            "input": "two",
            "dimensions": 3,
        },
    ]


@pytest.mark.asyncio
async def test_openai_embedding_provider_wraps_single_input_failures() -> None:
    FakeAsyncOpenAI.embeddings_resource.fail_single = True
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        model_name="text-embedding-3-small",
        base_url="https://embeddings.example.com/v1",
    )

    with pytest.raises(ExternalServiceError) as exc_info:
        await provider.embed_texts(["hello"])

    message = str(exc_info.value)
    assert "OpenAI embedding request failed" in message
    assert "text-embedding-3-small" in message
    assert "https://embeddings.example.com/v1" in message
    assert "status 404: not found" in message


def test_openai_embedding_provider_requires_api_key() -> None:
    with pytest.raises(ConfigurationError):
        OpenAIEmbeddingProvider(
            api_key=None,
            model_name="text-embedding-3-small",
        )
