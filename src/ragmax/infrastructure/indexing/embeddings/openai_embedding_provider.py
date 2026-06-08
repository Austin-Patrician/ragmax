import asyncio
from collections.abc import Sequence

from openai import AsyncOpenAI

from ragmax.core.exceptions import ConfigurationError, ExternalServiceError


class OpenAIEmbeddingProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        model_name: str,
        base_url: str | None = None,
        dimension: int | None = None,
        batch_size: int = 16,
    ) -> None:
        if not api_key:
            raise ConfigurationError("OPENAI_API_KEY is required when embedding_provider=openai.")
        self._base_url = _normalize_base_url(base_url)
        self._client = AsyncOpenAI(api_key=api_key, base_url=self._base_url)
        self._requested_dimension = dimension
        self._batch_size = max(1, batch_size)
        self._force_single_input = False
        self.model_name = model_name
        self.dimension = dimension or 1536

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            embeddings: list[list[float]] = []
            text_list = list(texts)
            for index in range(0, len(text_list), self._batch_size):
                embeddings.extend(await self._embed_batch(text_list[index : index + self._batch_size]))
            return embeddings
        except Exception as exc:
            if isinstance(exc, ExternalServiceError):
                raise
            raise self._embedding_error(exc) from exc

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._force_single_input or len(texts) == 1:
            return await self._embed_single_inputs(texts)

        try:
            return await self._request_embeddings(texts)
        except Exception as exc:
            if _looks_like_empty_embedding_data(exc):
                self._force_single_input = True
                return await self._embed_single_inputs(texts)
            raise

    async def _embed_single_inputs(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.gather(*(self._request_single_embedding(text) for text in texts))

    async def _request_single_embedding(self, text: str) -> list[float]:
        embeddings = await self._request_embeddings(text)
        if len(embeddings) != 1:
            raise ExternalServiceError(
                f"OpenAI embedding request returned {len(embeddings)} vectors for one input."
            )
        return embeddings[0]

    async def _request_embeddings(self, input_value: str | list[str]) -> list[list[float]]:
        kwargs: dict[str, object] = {
            "model": self.model_name,
            "input": input_value,
        }
        if self._requested_dimension is not None:
            kwargs["dimensions"] = self._requested_dimension

        response = await self._client.embeddings.create(**kwargs)
        data = response.data or []
        if not data:
            raise ValueError("No embedding data received")

        embeddings = [item.embedding for item in data]
        expected_count = 1 if isinstance(input_value, str) else len(input_value)
        if len(embeddings) != expected_count:
            raise ExternalServiceError(
                "OpenAI embedding request returned an unexpected number of vectors: "
                f"expected {expected_count}, got {len(embeddings)}."
            )
        return embeddings

    def _embedding_error(self, exc: Exception) -> ExternalServiceError:
        message = str(exc) or exc.__class__.__name__
        endpoint = self._base_url or "default OpenAI endpoint"
        return ExternalServiceError(
            f"OpenAI embedding request failed for model '{self.model_name}' "
            f"at '{endpoint}': {message}"
        )


def _normalize_base_url(base_url: str | None) -> str | None:
    if base_url is None:
        return None
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        return None
    if normalized.lower().endswith("/embeddings"):
        normalized = normalized[: -len("/embeddings")].rstrip("/")
    return normalized or None


def _looks_like_empty_embedding_data(exc: Exception) -> bool:
    return "No embedding data received" in str(exc)
