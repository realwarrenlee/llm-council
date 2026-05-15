"""Configuration management for LLM Council."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CouncilConfig:
    """Configuration for Council deliberation.

    This dataclass consolidates all configuration parameters for cleaner
    API design and better type safety.

    Attributes:
        output_mode: Output mode - "synthesis", "perspectives", or "both"
        aggregation_method: Method for aggregating peer reviews - "borda", "bradley_terry", or "elo"
        enable_peer_review: Whether to enable peer review of responses
        anonymize: Whether to anonymize responses during peer review
        chairman_model: Model to use for synthesis. If None, uses default from presets
        include_weights: Whether to include role weights in synthesis
        include_confidence: Whether to include confidence indicators in synthesis
    """

    output_mode: str = "perspectives"
    aggregation_method: str = "borda"
    enable_peer_review: bool = True
    anonymize: bool = False
    chairman_model: str | None = None
    include_weights: bool = True
    include_confidence: bool = True

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        valid_modes = {"synthesis", "perspectives", "both"}
        if self.output_mode not in valid_modes:
            raise ValueError(
                f"Invalid output_mode '{self.output_mode}'. "
                f"Must be one of: {', '.join(valid_modes)}"
            )

        valid_methods = {"borda", "bradley_terry", "elo"}
        if self.aggregation_method not in valid_methods:
            raise ValueError(
                f"Invalid aggregation_method '{self.aggregation_method}'. "
                f"Must be one of: {', '.join(valid_methods)}"
            )
