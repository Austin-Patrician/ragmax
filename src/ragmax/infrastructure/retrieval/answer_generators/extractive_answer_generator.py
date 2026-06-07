import re
from collections.abc import Sequence

from ragmax.application.retrieval.dtos import GeneratedAnswer, RetrievalContextItem

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


class ExtractiveAnswerGenerator:
    name = "extractive_answer_generator:v1"

    def __init__(self, *, max_contexts: int = 4, max_snippet_chars: int = 420) -> None:
        self._max_contexts = max(1, max_contexts)
        self._max_snippet_chars = max(80, max_snippet_chars)

    async def generate(
        self,
        *,
        query: str,
        contexts: Sequence[RetrievalContextItem],
    ) -> GeneratedAnswer:
        selected_contexts = tuple(contexts[: self._max_contexts])
        if not selected_contexts:
            return GeneratedAnswer(
                answer="I could not find relevant context in this notebook.",
                metadata={"strategy": "extractive"},
            )

        query_terms = _tokenize(query)
        snippets = [
            (
                f"[{context.citation_id}] "
                f"{_best_snippet(query_terms, context.text, self._max_snippet_chars)}"
            )
            for context in selected_contexts
        ]
        return GeneratedAnswer(
            answer="Based on the retrieved context, the relevant information is:\n"
            + "\n".join(snippets),
            used_context_ids=tuple(context.context_id for context in selected_contexts),
            metadata={
                "strategy": "extractive",
                "used_context_count": len(selected_contexts),
            },
        )


def _best_snippet(
    query_terms: frozenset[str],
    text: str,
    max_chars: int,
) -> str:
    normalized_text = _normalize_whitespace(text)
    if len(normalized_text) <= max_chars:
        return normalized_text

    candidates = [
        _normalize_whitespace(candidate)
        for candidate in _SENTENCE_SPLIT_RE.split(normalized_text)
        if candidate.strip()
    ]
    if not candidates:
        return _truncate(normalized_text, max_chars)

    best_candidate = max(
        candidates,
        key=lambda candidate: (_overlap_score(query_terms, candidate), len(candidate)),
    )
    return _truncate(best_candidate, max_chars)


def _overlap_score(query_terms: frozenset[str], text: str) -> float:
    if not query_terms:
        return 0.0
    text_terms = _tokenize(text)
    return len(query_terms.intersection(text_terms)) / len(query_terms)


def _tokenize(text: str) -> frozenset[str]:
    return frozenset(match.group(0).lower() for match in _TOKEN_RE.finditer(text))


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."
