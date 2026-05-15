"""Pydantic schemas for LLM Council API.

These schemas mirror the TypeScript interfaces in the frontend API client.
"""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


# =============================================================================
# Role Configuration Schemas
# =============================================================================


class RoleConfig(BaseModel):
    """Configuration for a role's generation behavior.

    Mirrors TypeScript RoleConfig interface.
    """

    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    presence_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    frequency_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    extra: dict[str, Any] = Field(default_factory=dict)


class Role(BaseModel):
    """A role in the LLM Council.

    Mirrors TypeScript Role interface.
    """

    name: str
    prompt: str = ""  # Optional - will be looked up from presets if empty
    model: str = "anthropic/claude-sonnet-4"
    description: str = ""
    config: RoleConfig = Field(default_factory=RoleConfig)
    weight: float = Field(default=1.0, gt=0)
    depends_on: list[str] = Field(default_factory=list)


# =============================================================================
# Council Result Schemas
# =============================================================================


class CouncilResult(BaseModel):
    """Result from a single role's execution.

    Mirrors TypeScript CouncilResult interface.
    """

    role_name: str
    content: str
    model: str
    tokens_used: int | None = None
    latency_ms: float | None = None
    error: str | None = None
    success: bool = True


class AggregationScores(BaseModel):
    """Scores from a single aggregation method."""
    
    scores: dict[str, float] = Field(default_factory=dict)
    confidence_intervals: dict[str, tuple[float, float]] | None = None  # For ELO: (lower, upper)


class CouncilOutput(BaseModel):
    """Complete output from a council deliberation.

    Mirrors TypeScript CouncilOutput interface.
    """

    task: str
    results: list[CouncilResult] = Field(default_factory=list)
    output_mode: str = "perspectives"
    synthesis: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    confidence_scores: dict[str, float] = Field(default_factory=dict)
    aggregate_rankings: dict[str, float] = Field(default_factory=dict)  # Legacy: primary method scores
    aggregation_scores: dict[str, AggregationScores] = Field(default_factory=dict)  # New: all methods


# =============================================================================
# Template Schemas
# =============================================================================


class TemplateRole(BaseModel):
    """Role configuration within a template."""

    name: str
    prompt: str
    model: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None
    weight: float | None = None
    depends_on: list[str] | None = None


class StageConfig(BaseModel):
    """Configuration for a deliberation stage.

    Mirrors TypeScript StageConfig interface.
    """

    name: str
    description: str
    output_mode: str
    anonymize: bool = False
    reviewers: list[str] | None = None
    min_reviewers: int = 2
    aggregation_method: str = "borda"
    pass_through: bool = False
    extra: dict[str, Any] | None = None


class TemplateMetadata(BaseModel):
    """Metadata for a template."""

    author: str | None = None
    version: str | None = None
    tags: list[str] | None = None


class Template(BaseModel):
    """A template defining a council configuration.

    Mirrors TypeScript Template interface.
    """

    name: str
    description: str
    roles: list[TemplateRole]
    output_mode: str = "perspectives"
    stages: list[StageConfig] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Deliberation Request/Response Schemas
# =============================================================================


class DeliberationOptions(BaseModel):
    """Options for starting a deliberation.

    Mirrors TypeScript DeliberationOptions interface.
    """

    output_mode: Literal["synthesis", "perspectives", "both"] | None = None
    anonymize: bool = False
    review: bool = False
    reviewers: list[str] | None = None
    stages: list[StageConfig] | None = None
    aggregation: str | None = None
    bootstrap_rounds: int | None = None
    reference_role: str | None = None
    chairman_model: str | None = None  # Model to use for synthesis
    metadata: dict[str, Any] | None = None


class DeliberationRequest(BaseModel):
    """Request body for starting a deliberation.

    Mirrors TypeScript DeliberationRequest interface.
    """

    task: str
    roles: list[Role]
    options: DeliberationOptions | None = None


# =============================================================================
# WebSocket Stream Schemas
# =============================================================================


class StreamMessage(BaseModel):
    """Message received from streaming deliberation.

    Mirrors TypeScript StreamMessage interface.
    """

    type: Literal[
        "role_start",
        "role_chunk",
        "role_complete",
        "role_error",
        "synthesis_start",
        "synthesis_chunk",
        "synthesis_complete",
        "complete",
        "error",
    ]
    role_name: str | None = None
    content: str | None = None
    result: CouncilResult | None = None
    error: str | None = None
    timestamp: str
    metadata: dict[str, Any] | None = None


# =============================================================================
# Error Response Schemas
# =============================================================================


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    code: str | None = None
    details: dict[str, Any] | None = None


class ValidationErrorResponse(BaseModel):
    """Validation error response with field details."""

    error: str
    code: str = "VALIDATION_ERROR"
    field: str | None = None
    details: dict[str, Any] | None = None
