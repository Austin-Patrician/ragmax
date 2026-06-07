from collections.abc import Sequence

from llama_index.embeddings.openai import OpenAIEmbedding

from ragmax.core.exceptions import ConfigurationError


class OpenAIEmbeddingProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        model_name: str,
        dimension: int | None = None,
    ) -> None:
        if not api_key:
            raise ConfigurationError("OPENAI_API_KEY is required when embedding_provider=openai.")
        self.model_name = model_name
        self._embed_model = OpenAIEmbedding(
            api_key=api_key,
            model=model_name,
            dimensions=dimension,
        )
        self.dimension = dimension or 1536

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return await self._embed_model.aget_text_embedding_batch(list(texts))
