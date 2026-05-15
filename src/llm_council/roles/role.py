"""Core Role dataclass and configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RoleConfig:
    """Configuration for a role's behavior.

    Attributes:
        temperature: Sampling temperature (0.0 - 2.0)
        max_tokens: Maximum tokens to generate
        top_p: Nucleus sampling parameter
        presence_penalty: Presence penalty (-2.0 to 2.0)
        frequency_penalty: Frequency penalty (-2.0 to 2.0)
        extra: Additional provider-specific parameters
    """

    temperature: float = 0.7
    max_tokens: int | None = None
    top_p: float | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(f"temperature must be between 0.0 and 2.0, got {self.temperature}")
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive, got {self.max_tokens}")


@dataclass
class Role:
    """A role in the council with a specific perspective or expertise.

    Roles represent different viewpoints or areas of expertise that contribute
    to the council's deliberation. Each role has a unique prompt that defines
    its perspective and behavior.

    Attributes:
        name: Unique identifier for the role
        prompt: System prompt defining the role's perspective
        model: LLM model to use for this role
        description: Human-readable description of the role
        config: Generation configuration for this role
        weight: Voting weight for aggregation (default: 1.0)

    Example:
        ```python
        role = Role(
            name="critic",
            prompt="You are a critical thinker who identifies risks...",
            model="anthropic/claude-sonnet-4",
            description="Identifies potential issues and risks",
            weight=1.5,
        )
        ```
    """

    name: str
    prompt: str
    model: str
    description: str = ""
    config: RoleConfig = field(default_factory=RoleConfig)
    weight: float = 1.0

    def __post_init__(self) -> None:
        """Validate role configuration."""
        if not self.name:
            raise ValueError("Role name cannot be empty")
        # Prompt is now optional for model-based approach
        if not self.model:
            raise ValueError("Role model cannot be empty")
        if self.weight <= 0:
            raise ValueError(f"Role weight must be positive, got {self.weight}")

    def copy(self) -> Role:
        """Create a copy of this role.

        Returns:
            New Role instance with the same configuration
        """
        return Role(
            name=self.name,
            prompt=self.prompt,
            model=self.model,
            description=self.description,
            config=self.config,
            weight=self.weight,
        )

    def with_weight(self, weight: float) -> Role:
        """Create a copy of this role with a different weight.

        Args:
            weight: New weight value

        Returns:
            New Role instance with updated weight
        """
        return Role(
            name=self.name,
            prompt=self.prompt,
            model=self.model,
            description=self.description,
            config=self.config,
            weight=weight,
        )



@dataclass
class Role:
    """A role in the LLM Council.

    A role represents a perspective or persona that contributes to deliberation.
    Each role has a name, prompt defining its behavior, and optional configuration.

    Attributes:
        name: Unique identifier for this role
        prompt: System prompt defining the role's behavior and perspective
        model: Model identifier (e.g., "claude-sonnet-4-5", "gpt-5")
        description: Human-readable description of the role
        config: Generation configuration for this role
        weight: Voting weight for aggregation (default: 1.0)
        depends_on: List of role names this role depends on

    Example:
        ```python
        critic = Role(
            name="critic",
            prompt="You are a skeptical critic who challenges assumptions...",
            model="claude-sonnet-4-5",
            description="Challenges assumptions and identifies risks",
            weight=1.5,  # Critics get more weight
        )
        ```
    """

    name: str
    prompt: str
    model: str = "anthropic/claude-sonnet-4"
    description: str = ""
    config: RoleConfig = field(default_factory=RoleConfig)
    weight: float = 1.0
    depends_on: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate role configuration."""
        if not self.name:
            raise ValueError("Role name cannot be empty")
        # Prompt is now optional for model-based approach
        if self.weight <= 0:
            raise ValueError(f"Role weight must be positive, got {self.weight}")

    def with_model(self, model: str) -> Role:
        """Create a copy of this role with a different model."""
        return Role(
            name=self.name,
            prompt=self.prompt,
            model=model,
            description=self.description,
            config=self.config,
            weight=self.weight,
            depends_on=self.depends_on.copy(),
        )

    def with_weight(self, weight: float) -> Role:
        """Create a copy of this role with a different weight."""
        return Role(
            name=self.name,
            prompt=self.prompt,
            model=self.model,
            description=self.description,
            config=self.config,
            weight=weight,
            depends_on=self.depends_on.copy(),
        )

    def depends_on_role(self, *role_names: str) -> Role:
        """Add dependencies on other roles."""
        new_depends = list(self.depends_on)
        for name in role_names:
            if name not in new_depends:
                new_depends.append(name)
        return Role(
            name=self.name,
            prompt=self.prompt,
            model=self.model,
            description=self.description,
            config=self.config,
            weight=self.weight,
            depends_on=new_depends,
        )
