"""OpenRouter provider implementation."""

from __future__ import annotations

import os
import time

import httpx

from llm_council.providers.base import Provider, ProviderError, GenerationResult


class OpenRouterProvider(Provider):
    """OpenRouter API provider.

    OpenRouter provides unified access to 100+ LLMs through a single API.
    Get an API key at https://openrouter.ai

    Environment:
        OPENROUTER_API_KEY: Required. Your OpenRouter API key.

    Example:
        >>> provider = OpenRouterProvider()
        >>> result = await provider.generate(
        ...     "What is Python?",
        ...     system_prompt="You are a helpful assistant.",
        ...     model="anthropic/claude-sonnet-4"
        ... )
    """

    BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "anthropic/claude-sonnet-4"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
    ) -> None:
        """Initialize OpenRouter provider.

        Args:
            api_key: OpenRouter API key. Falls back to OPENROUTER_API_KEY env var.
            base_url: Override the API base URL.
            default_model: Default model if not specified in generate().
        """
        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self._base_url = base_url or self.BASE_URL
        self._default_model = default_model or self.DEFAULT_MODEL
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> GenerationResult:
        """Generate a response using OpenRouter."""
        if not self._api_key:
            return GenerationResult(
                content="",
                model=model or self._default_model,
                error="OPENROUTER_API_KEY not set. Get one at https://openrouter.ai",
            )

        client = await self._get_client()
        start_time = time.time()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        body: dict = {
            "model": model or self._default_model,
            "messages": messages,
            "temperature": temperature,
        }
        
        # Only include max_tokens if explicitly specified
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        
        print(f"DEBUG OpenRouter: Calling {body['model']} with max_tokens={body.get('max_tokens', 'not set')}")

        try:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/llm-council",
                    "X-Title": "LLM Council",
                },
                json=body,
            )
            response.raise_for_status()
            data = response.json()

            latency_ms = (time.time() - start_time) * 1000
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            usage = data.get("usage", {})

            return GenerationResult(
                content=message.get("content", ""),
                model=data.get("model", model or self._default_model),
                tokens_used=usage.get("total_tokens"),
                latency_ms=latency_ms,
            )

        except httpx.HTTPStatusError as e:
            return GenerationResult(
                content="",
                model=model or self._default_model,
                error=f"API error {e.response.status_code}: {e.response.text}",
            )
        except Exception as e:
            return GenerationResult(
                content="",
                model=model or self._default_model,
                error=f"Request failed: {str(e)}",
            )

    async def health_check(self) -> bool:
        """Check if OpenRouter API is accessible."""
        if not self._api_key:
            return False

        try:
            client = await self._get_client()
            response = await client.get(
                f"{self._base_url}/models",
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
