import hashlib
import math
from collections.abc import Sequence


class HashEmbeddingProvider:
    def __init__(self, *, model_name: str = "hash-embedding-v1", dimension: int = 384) -> None:
        self.model_name = model_name
        self.dimension = dimension

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in texts]

    def _embed_text(self, text: str) -> list[float]:
        values: list[float] = []
        counter = 0
        while len(values) < self.dimension:
            digest = hashlib.sha256(f"{text}|{counter}".encode()).digest()
            values.extend((byte / 127.5) - 1.0 for byte in digest)
            counter += 1

        vector = values[: self.dimension]
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
