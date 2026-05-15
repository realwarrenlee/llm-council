"""Base provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class ProviderError(Exception):
    """Error from a provider."""

    pass


@dataclass
class GenerationResult:
    """Result from a generation request."""

    content: str
    model: str
    tokens_used: int | None = None
    latency_ms: float | None = None
    error: str | None = None

    @property
    def success(self) -> bool:
        """Check if generation was successful."""
        return self.error is None


class Provider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> GenerationResult:
        """Generate a response from the LLM.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            model: Model identifier (provider-specific)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            GenerationResult with content or error
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy/available."""
        ...
