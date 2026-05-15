"""Analysis module for LLM Council.

This module provides tools for analyzing council deliberations, including
pairwise comparison analysis using the Bradley-Terry model, ELO scoring,
and judge agreement analysis for peer review.
"""

from llm_council.analysis.bradley_terry import (
    PairwiseResult,
    BradleyTerryAnalyzer,
    pairwise_from_rankings,
    pairwise_from_reviews,
)
from llm_council.analysis.elo import (
    EloRating,
    EloCalculator,
    compute_mle_elo,
    bootstrap_elo,
    calculate_separability,
    calculate_polarization,
    predict_win_rate,
)
from llm_council.analysis.agreement import (
    AgreementMetrics,
    ComparisonRating,
    JudgeAgreementAnalyzer,
    convert_reviews_to_matrix,
    extract_ranking_from_review,
    AGREEMENT_METHODS,
)

__all__ = [
    # Bradley-Terry analysis
    "PairwiseResult",
    "BradleyTerryAnalyzer",
    "pairwise_from_rankings",
    "pairwise_from_reviews",
    # ELO scoring
    "EloRating",
    "EloCalculator",
    "compute_mle_elo",
    "bootstrap_elo",
    "calculate_separability",
    "calculate_polarization",
    "predict_win_rate",
    # Agreement analysis
    "AgreementMetrics",
    "ComparisonRating",
    "JudgeAgreementAnalyzer",
    "convert_reviews_to_matrix",
    "extract_ranking_from_review",
    "AGREEMENT_METHODS",
]
