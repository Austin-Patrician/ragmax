import base64
import json
import re
from pathlib import Path

from openai import AsyncOpenAI

from ragmax.core.exceptions import ConfigurationError, ExternalServiceError


class OpenAIVLMProvider:
    """OpenAI-compatible Vision Language Model provider.

    Supports analyzing images with context using vision-capable models.
    Compatible with OpenAI API and any OpenAI-compatible endpoints.
    """

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str | None = None,
        model: str = "qwen/qwen3-vl-32b-instruct",
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> None:
        if not api_key:
            raise ConfigurationError("VLM API key is required when VLM is enabled.")

        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def analyze_image(
        self,
        *,
        image_path: str,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Analyze an image using the vision language model.

        Args:
            image_path: Path to the image file
            prompt: User prompt for image analysis
            system_prompt: Optional system prompt

        Returns:
            JSON string with analysis results

        Raises:
            ExternalServiceError: If the API call fails
        """
        try:
            # Encode image to base64
            image_base64 = self._encode_image_to_base64(image_path)

            # Construct messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            })

            # Call VLM API
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Extract response content
            content = response.choices[0].message.content or ""

            # Clean response (remove thinking tags if present)
            content = self._clean_response(content)

            return content

        except Exception as exc:
            if isinstance(exc, ExternalServiceError):
                raise
            raise self._build_error(exc, image_path) from exc

    def _encode_image_to_base64(self, image_path: str) -> str:
        """Encode image file to base64 string."""
        try:
            path = Path(image_path)
            if not path.exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")

            with path.open("rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as exc:
            raise ExternalServiceError(
                f"Failed to encode image '{image_path}': {exc}"
            ) from exc

    def _clean_response(self, content: str) -> str:
        """Clean VLM response by removing thinking tags and extra whitespace.

        Some models (e.g., DeepSeek-R1, Qwen2.5-think) include <think> tags
        in their reasoning process. This removes them to extract clean output.
        """
        # Remove <think>...</think> blocks
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)

        # Remove standalone <think> or </think> tags
        content = re.sub(r"</?think>", "", content)

        return content.strip()

    def _build_error(self, exc: Exception, image_path: str) -> ExternalServiceError:
        """Build a descriptive error message for VLM failures."""
        message = str(exc) or exc.__class__.__name__
        return ExternalServiceError(
            f"VLM analysis failed for image '{image_path}' using model '{self.model}': {message}"
        )