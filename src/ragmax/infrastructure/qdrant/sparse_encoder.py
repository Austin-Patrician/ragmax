"""Shared sparse text encoding for Qdrant lexical retrieval."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter

from qdrant_client import models

SPARSE_VECTOR_NAME = "text-sparse"
SPARSE_HASH_SPACE = 2_000_003

_ALNUM_RE = re.compile(r"[a-z0-9_]+")
_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


class SparseTextEncoder:
    """Encode mixed Chinese/English text into a deterministic sparse vector."""

    def __init__(self, *, hash_space: int = SPARSE_HASH_SPACE, k1: float = 1.2) -> None:
        if hash_space < 1:
            raise ValueError("hash_space must be positive.")
        if k1 <= 0:
            raise ValueError("k1 must be positive.")
        self._hash_space = hash_space
        self._k1 = k1

    def encode(self, text: str) -> tuple[models.SparseVector, tuple[str, ...]]:
        tokens = self.tokenize(text)
        if not tokens:
            return models.SparseVector(indices=[], values=[]), ()

        term_freq = Counter(tokens)
        values_by_index: dict[int, float] = {}
        for token, freq in sorted(term_freq.items()):
            index = self._token_index(token)
            value = freq / (freq + self._k1)
            values_by_index[index] = values_by_index.get(index, 0.0) + value

        indices = sorted(values_by_index)
        return (
            models.SparseVector(
                indices=indices,
                values=[values_by_index[index] for index in indices],
            ),
            tuple(sorted(term_freq)),
        )

    def tokenize(self, text: str) -> tuple[str, ...]:
        import jieba

        normalized = unicodedata.normalize("NFKC", text).lower()
        tokens: list[str] = []
        for segment in jieba.lcut(normalized, cut_all=False):
            cleaned = segment.strip()
            if not cleaned:
                continue

            if _ALNUM_RE.fullmatch(cleaned) or _CJK_RE.search(cleaned):
                tokens.append(cleaned)
                continue

            tokens.extend(_ALNUM_RE.findall(cleaned))

        return tuple(tokens)

    def _token_index(self, token: str) -> int:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "big") % self._hash_space
