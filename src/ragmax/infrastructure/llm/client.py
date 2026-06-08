"""LLM client implementations."""

from dataclasses import dataclass
from typing import Protocol

from collections.abc import Sequence


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
