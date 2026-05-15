"""Custom exception types for LLM Council."""


class CouncilError(Exception):
    """Base exception for all Council-related errors."""

    pass


class ProviderError(CouncilError):
    """Error related to LLM provider operations."""

    pass


class AggregationError(CouncilError):
    """Error during peer review aggregation."""

    pass


class ConfigurationError(CouncilError):
    """Error in council configuration."""

    pass


class PeerReviewError(CouncilError):
    """Error during peer review process."""

    pass
