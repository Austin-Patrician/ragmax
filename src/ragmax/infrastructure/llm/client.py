"""LLM client implementations."""

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMMessage:
    """Message in LLM conversation."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass(frozen=True)
class LLMResponse:
    """Response from LLM."""

    content: str
    usage: dict[str, int]  # Token usage stats
    model: str


@dataclass(frozen=True)
class LLMStreamChunk:
    content_delta: str = ""
    usage: dict[str, int] | None = None
    model: str | None = None


class LLMClient(Protocol):
    """Interface for LLM clients."""

    async def generate(
        self,
        messages: Sequence[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate completion from messages."""
        ...

    async def stream_generate(
        self,
        messages: Sequence[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Generate completion chunks from messages."""
        ...


class OpenAILLMClient:
    """OpenAI API client for LLM generation."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
    ) -> None:
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-4o-mini)
            base_url: Optional custom base URL
        """
        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            raise ImportError(
                "openai package is required for LLM generation. "
                "Install it with: pip install openai"
            ) from e

        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def generate(
        self,
        messages: Sequence[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate completion using OpenAI API.

        Args:
            messages: Conversation messages
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens to generate

        Returns:
            LLM response with content and usage stats
        """
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": msg.role, "content": msg.content} for msg in messages],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        }

        return LLMResponse(
            content=response.choices[0].message.content or "",
            usage=usage,
            model=response.model,
        )

    async def stream_generate(
        self,
        messages: Sequence[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Generate completion using OpenAI streaming API."""
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": msg.role, "content": msg.content} for msg in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            stream_options={"include_usage": True},
        )

        async for chunk in stream:
            usage = None
            if getattr(chunk, "usage", None) is not None:
                usage = {
                    "prompt_tokens": chunk.usage.prompt_tokens,
                    "completion_tokens": chunk.usage.completion_tokens,
                    "total_tokens": chunk.usage.total_tokens,
                }

            content_delta = ""
            if chunk.choices:
                content_delta = chunk.choices[0].delta.content or ""

            if content_delta or usage is not None:
                yield LLMStreamChunk(
                    content_delta=content_delta,
                    usage=usage,
                    model=chunk.model,
                )
