"""Anonymization module for LLM Council.

This module provides functionality for anonymizing responses during peer review,
allowing unbiased evaluation of responses without knowing which role produced them.
"""

from llm_council.anonymization.core import (
    AnonymizedCollection,
    AnonymizedResult,
    anonymize_responses,
    de_anonymize,
    parse_ranking_from_text,
    calculate_aggregate_rankings,
)

__all__ = [
    "AnonymizedResult",
    "AnonymizedCollection",
    "anonymize_responses",
    "de_anonymize",
    "parse_ranking_from_text",
    "calculate_aggregate_rankings",
]
