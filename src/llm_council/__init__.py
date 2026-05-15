"""LLM Council - Role-based deliberation system."""

__version__ = "0.1.0"

from llm_council.roles import Role, RoleConfig, RoleRegistry
from llm_council.council import Council, OutputMode
from llm_council.peer_review import PeerReview, ReviewRound, PeerReviewResult
from llm_council.config import CouncilConfig
from llm_council.exceptions import (
    CouncilError,
    ProviderError,
    AggregationError,
    ConfigurationError,
    PeerReviewError,
)
from llm_council.peer_review_orchestrator import PeerReviewOrchestrator

__all__ = [
    "Role",
    "RoleConfig",
    "RoleRegistry",
    "Council",
    "CouncilConfig",
    "OutputMode",
    "PeerReview",
    "ReviewRound",
    "PeerReviewResult",
    "PeerReviewOrchestrator",
    "CouncilError",
    "ProviderError",
    "AggregationError",
    "ConfigurationError",
    "PeerReviewError",
]
