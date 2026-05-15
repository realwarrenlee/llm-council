"""ELO scoring module for pairwise comparison analysis.

This module provides ELO rating calculations for analyzing pairwise comparison
results, including online ELO updates, MLE ELO computation via logistic regression,
and bootstrap confidence intervals.

Example:
    ```python
    from llm_council.analysis.elo import EloCalculator, EloRating
    from llm_council.analysis.bradley_terry import PairwiseResult

    # Online ELO updates
    calculator = EloCalculator(init_rating=1000, k_factor=32)
    calculator.update_rating("model_a", "model_b", margin="major")
    ratings = calculator.get_all_ratings()

    # MLE ELO computation
    results = [PairwiseResult(...), ...]
    elo_ratings = compute_mle_elo(results, init_rating=1000)

    # Bootstrap confidence intervals
    ratings_with_ci = bootstrap_elo(results, num_rounds=1000)
    ```
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import combinations
from typing import TYPE_CHECKING

# Avoid circular imports
if TYPE_CHECKING:
    from llm_council.analysis.bradley_terry import PairwiseResult

# Optional numpy import - required for MLE ELO computation
try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None  # type: ignore


@dataclass
class EloRating:
    """ELO rating for a single item.

    Attributes:
        item_id: Unique identifier for the rated item
        rating: The ELO rating value
        lower_ci: 95% confidence interval lower bound (optional)
        upper_ci: 95% confidence interval upper bound (optional)
        games_played: Number of games/matches played
    """

    item_id: str
    rating: float
    lower_ci: float | None = None
    upper_ci: float | None = None
    games_played: int = 0


class EloCalculator:
    """Calculator for online ELO rating updates.

    This class implements the standard ELO rating system with support for
    different victory margins (minor/major wins) and configurable parameters.

    Attributes:
        init_rating: Initial rating for new items
        k_factor: Maximum rating change per game
        scale: ELO scale factor (default 400)

    Example:
        ```python
        calculator = EloCalculator(init_rating=1000, k_factor=32)
        calculator.update_rating("model_a", "model_b", margin="major")
        calculator.update_rating("model_c", "model_d", margin="minor")

        # Get rankings
        rankings = calculator.get_rankings()
        for r in rankings:
            print(f"{r.item_id}: {r.rating:.1f}")
        ```
    """

    def __init__(
        self,
        init_rating: float = 1000,
        k_factor: float = 32,
        scale: float = 400,
        base: float = 10.0,
    ) -> None:
        """Initialize the ELO calculator.

        Args:
            init_rating: Initial rating for new items (default: 1000)
            k_factor: Maximum rating change per game (default: 32)
            scale: ELO scale factor (default: 400)
            base: Base for the ELO formula (default: 10)
        """
        self.init_rating = init_rating
        self.k_factor = k_factor
        self.scale = scale
        self.base = base
        self._ratings: dict[str, float] = {}
        self._games_played: dict[str, int] = {}
        self._margin_multipliers = {
            "minor": 1.0,
            "major": 3.0,
            "tie": 0.5,
        }

    def _get_rating(self, item_id: str) -> float:
        """Get current rating or return initial rating if new."""
        return self._ratings.get(item_id, self.init_rating)

    def _expected_score(self, rating_a: float, rating_b: float) -> float:
        """Calculate expected score for player A against player B."""
        return 1.0 / (1.0 + self.base ** ((rating_b - rating_a) / self.scale))

    def update_rating(
        self,
        winner: str,
        loser: str,
        margin: str = "minor",
    ) -> tuple[float, float]:
        """Update ratings after a match.

        Args:
            winner: ID of the winning item
            loser: ID of the losing item
            margin: Victory margin ("minor", "major", or "tie")

        Returns:
            Tuple of (new_winner_rating, new_loser_rating)

        Raises:
            ValueError: If margin is not a valid margin type
        """
        if margin not in self._margin_multipliers:
            valid_margins = list(self._margin_multipliers.keys())
            raise ValueError(f"Invalid margin '{margin}'. Must be one of: {valid_margins}")

        # Get current ratings
        rating_winner = self._get_rating(winner)
        rating_loser = self._get_rating(loser)

        # Calculate expected scores
        expected_winner = self._expected_score(rating_winner, rating_loser)
        expected_loser = 1.0 - expected_winner

        # Determine actual scores based on margin
        margin_mult = self._margin_multipliers[margin]
        if margin == "tie":
            actual_winner = 0.5
            actual_loser = 0.5
        else:
            actual_winner = 1.0
            actual_loser = 0.0

        # Calculate rating changes with margin multiplier
        k_adjusted = self.k_factor * margin_mult
        change_winner = k_adjusted * (actual_winner - expected_winner)
        change_loser = k_adjusted * (actual_loser - expected_loser)

        # Update ratings
        new_winner_rating = rating_winner + change_winner
        new_loser_rating = rating_loser + change_loser

        self._ratings[winner] = new_winner_rating
        self._ratings[loser] = new_loser_rating

        # Update games played
        self._games_played[winner] = self._games_played.get(winner, 0) + 1
        self._games_played[loser] = self._games_played.get(loser, 0) + 1

        return (new_winner_rating, new_loser_rating)

    def get_rating(self, item_id: str) -> float:
        """Get current rating for an item.

        Args:
            item_id: The item identifier

        Returns:
            Current ELO rating (or init_rating if item hasn't played)
        """
        return self._get_rating(item_id)

    def get_all_ratings(self) -> dict[str, EloRating]:
        """Get all ratings as EloRating objects.

        Returns:
            Dictionary mapping item_id to EloRating
        """
        return {
            item_id: EloRating(
                item_id=item_id,
                rating=rating,
                games_played=self._games_played.get(item_id, 0),
            )
            for item_id, rating in self._ratings.items()
        }

    def predict_win_probability(self, a_id: str, b_id: str) -> tuple[float, float]:
        """Predict win probability for a match between two items.

        Args:
            a_id: ID of first item
            b_id: ID of second item

        Returns:
            Tuple of (probability_a_wins, probability_b_wins)
        """
        rating_a = self._get_rating(a_id)
        rating_b = self._get_rating(b_id)

        prob_a = self._expected_score(rating_a, rating_b)
        prob_b = 1.0 - prob_a

        return (prob_a, prob_b)

    def get_rankings(self) -> list[EloRating]:
        """Get all ratings sorted by rating descending.

        Returns:
            List of EloRating objects sorted by rating (highest first)
        """
        ratings = self.get_all_ratings()
        return sorted(ratings.values(), key=lambda r: r.rating, reverse=True)


def _results_to_battles(
    results: list[PairwiseResult],
    major_win_multiplier: int = 3,
) -> list[dict]:
    """Convert PairwiseResult objects to battle records.

    Args:
        results: List of pairwise comparison results
        major_win_multiplier: Weight multiplier for major wins

    Returns:
        List of battle dictionaries with model_a, model_b, winner keys
    """
    battles = []

    for result in results:
        # Determine winner and weight based on PairwiseResult interface
        # winner is "a", "b", or None (for tie)
        if result.winner is None:
            # Tie
            weight = 1
            winner = "tie"
        elif result.winner == "a":
            winner = "model_a"
            weight = major_win_multiplier if result.margin == "major" else 1
        elif result.winner == "b":
            winner = "model_b"
            weight = major_win_multiplier if result.margin == "major" else 1
        else:
            # Invalid result, skip
            continue

        battle = {
            "model_a": result.item_a,
            "model_b": result.item_b,
            "winner": winner,
        }

        # Add multiple entries for weighted wins
        for _ in range(weight):
            battles.append(battle.copy())

    return battles


def compute_mle_elo(
    results: list[PairwiseResult],
    init_rating: float = 1000,
    scale: float = 400,
    base: float = 10,
    reference_item: str | None = None,
) -> dict[str, float]:
    """Compute Maximum Likelihood ELO ratings using logistic regression.

    This function uses sklearn's LogisticRegression to compute ELO ratings
    that maximize the likelihood of the observed pairwise comparison outcomes.
    The implementation is based on the Arena Hard ELO computation method.

    Args:
        results: List of pairwise comparison results
        init_rating: Initial rating value (also used to pin reference)
        scale: ELO scale factor (default: 400)
        base: Base for the ELO formula (default: 10)
        reference_item: Item to pin to init_rating (if None, uses first encountered)

    Returns:
        Dictionary mapping item_id to ELO rating

    Raises:
        ValueError: If results list is empty
        ImportError: If numpy or sklearn is not available

    Example:
        ```python
        results = [
            PairwiseResult(item_a="model1", item_b="model2", winner="model1"),
            PairwiseResult(item_a="model1", item_b="model3", winner="model3"),
        ]
        ratings = compute_mle_elo(results, init_rating=1000)
        ```
    """
    if not NUMPY_AVAILABLE:
        raise ImportError(
            "numpy is required for MLE ELO computation. "
            "Install with: pip install numpy"
        )

    try:
        from sklearn.linear_model import LogisticRegression
    except ImportError as e:
        raise ImportError(
            "sklearn is required for MLE ELO computation. "
            "Install with: pip install scikit-learn"
        ) from e

    if not results:
        return {}

    # Convert results to battles format
    battles = _results_to_battles(results)

    if not battles:
        return {}

    # Get unique models
    models = set()
    for battle in battles:
        models.add(battle["model_a"])
        models.add(battle["model_b"])

    models = sorted(models)
    model_to_idx = {model: i for i, model in enumerate(models)}
    num_models = len(models)

    # Duplicate battles for tie handling (as in reference implementation)
    battles = battles + battles.copy()
    num_battles = len(battles)

    # Build design matrix X
    # X[i, j] = log(base) if model_j is model_a in battle i
    # X[i, j] = -log(base) if model_j is model_b in battle i
    X = np.zeros((num_battles, num_models))
    log_base = math.log(base)

    for i, battle in enumerate(battles):
        idx_a = model_to_idx[battle["model_a"]]
        idx_b = model_to_idx[battle["model_b"]]
        X[i, idx_a] = log_base
        X[i, idx_b] = -log_base

    # Build target vector Y
    # Y[i] = 1 if model_a wins, 0 otherwise
    # For ties: first half counts as model_a win, second half as model_b win
    Y = np.zeros(num_battles)
    for i, battle in enumerate(battles):
        if battle["winner"] == "model_a":
            Y[i] = 1.0
        elif battle["winner"] == "tie":
            # Handle ties: first half of duplicated battles count as model_a win
            if i < num_battles // 2:
                Y[i] = 1.0

    # Check if there's any variation in outcomes
    if len(np.unique(Y)) < 2:
        # All battles have the same outcome - no variation to learn from
        # Return equal ratings for all models
        return {model: init_rating for model in models}

    # Fit logistic regression (no intercept, no regularization)
    lr = LogisticRegression(fit_intercept=False, penalty=None, tol=1e-8)
    lr.fit(X, Y)

    # Convert coefficients to ELO ratings
    elo_scores = scale * lr.coef_[0] + init_rating

    # Pin reference item to init_rating
    if reference_item is None:
        # Use first model as reference if not specified
        reference_item = models[0]

    if reference_item in model_to_idx:
        reference_idx = model_to_idx[reference_item]
        adjustment = init_rating - elo_scores[reference_idx]
        elo_scores = elo_scores + adjustment

    return {model: float(elo_scores[model_to_idx[model]]) for model in models}


def bootstrap_elo(
    results: list[PairwiseResult],
    num_rounds: int = 1000,
    init_rating: float = 1000,
    reference_item: str | None = None,
    random_seed: int | None = None,
) -> dict[str, tuple[float, float, float]]:
    """Compute bootstrap confidence intervals for ELO ratings.

    This function performs bootstrap resampling on the pairwise results
    to estimate the distribution of ELO ratings and compute confidence intervals.

    Args:
        results: List of pairwise comparison results
        num_rounds: Number of bootstrap rounds (default: 1000)
        init_rating: Initial rating for ELO computation
        reference_item: Item to pin to init_rating
        random_seed: Optional random seed for reproducibility

    Returns:
        Dictionary mapping item_id to (median, lower_ci, upper_ci) tuples
        where lower_ci and upper_ci are the 2.5th and 97.5th percentiles (95% CI)

    Raises:
        ImportError: If numpy is not available

    Example:
        ```python
        results = [PairwiseResult(...), ...]
        ratings_with_ci = bootstrap_elo(results, num_rounds=1000)

        for item_id, (median, lower, upper) in ratings_with_ci.items():
            print(f"{item_id}: {median:.1f} [{lower:.1f}, {upper:.1f}]")
        ```
    """
    if not NUMPY_AVAILABLE:
        raise ImportError(
            "numpy is required for bootstrap ELO computation. "
            "Install with: pip install numpy"
        )

    if not results:
        return {}

    if len(results) < 2:
        # Not enough data for bootstrapping
        return {}

    if random_seed is not None:
        np.random.seed(random_seed)

    # Store bootstrap results for each item
    bootstrap_results: dict[str, list[float]] = {}
    failed_iterations = 0

    for _ in range(num_rounds):
        # Sample with replacement
        if len(results) < 100:
            # For small datasets, use all data (no actual bootstrapping)
            sample = results
        else:
            indices = np.random.choice(len(results), size=len(results), replace=True)
            sample = [results[i] for i in indices]

        # Compute ELO on sample
        try:
            elo_ratings = compute_mle_elo(
                sample,
                init_rating=init_rating,
                reference_item=reference_item,
            )

            # Store results
            for item_id, rating in elo_ratings.items():
                if item_id not in bootstrap_results:
                    bootstrap_results[item_id] = []
                bootstrap_results[item_id].append(rating)
        except Exception as e:
            # Skip failed iterations
            failed_iterations += 1
            if failed_iterations == 1:
                # Print first error for debugging
                print(f"ELO bootstrap iteration failed: {e}")
            continue

    if failed_iterations > 0:
        print(f"ELO: {failed_iterations}/{num_rounds} bootstrap iterations failed")

    # Compute statistics
    result = {}
    for item_id, ratings in bootstrap_results.items():
        if not ratings:
            continue

        ratings_array = np.array(ratings)
        median = float(np.median(ratings_array))
        lower_ci = float(np.percentile(ratings_array, 2.5))
        upper_ci = float(np.percentile(ratings_array, 97.5))

        result[item_id] = (median, lower_ci, upper_ci)

    return result


def calculate_separability(ratings: list[EloRating]) -> float:
    """Calculate the percentage of non-overlapping pairs.

    Separability measures how well the ratings distinguish between items.
    Two items are considered separable if their 95% confidence intervals
    do not overlap.

    Args:
        ratings: List of EloRating objects with confidence intervals

    Returns:
        Percentage of pairs that are non-overlapping (0-100)

    Example:
        ```python
        ratings = [
            EloRating("a", 1200, lower_ci=1150, upper_ci=1250),
            EloRating("b", 1100, lower_ci=1050, upper_ci=1150),
        ]
        sep = calculate_separability(ratings)  # 100.0 (non-overlapping)
        ```
    """
    if len(ratings) < 2:
        return 0.0

    total_pairs = 0
    non_overlapping_pairs = 0

    for rating_a, rating_b in combinations(ratings, 2):
        # Skip if either rating lacks confidence intervals
        if rating_a.lower_ci is None or rating_a.upper_ci is None:
            continue
        if rating_b.lower_ci is None or rating_b.upper_ci is None:
            continue

        total_pairs += 1

        # Check if intervals overlap
        # Non-overlapping if: upper_a < lower_b OR upper_b < lower_a
        if (rating_a.upper_ci < rating_b.lower_ci or
            rating_b.upper_ci < rating_a.lower_ci):
            non_overlapping_pairs += 1

    if total_pairs == 0:
        return 0.0

    return (non_overlapping_pairs / total_pairs) * 100.0


def calculate_polarization(ratings: list[EloRating]) -> float:
    """Calculate the polarization of ratings.

    Polarization is defined as the difference between the maximum and
    minimum ratings. Higher polarization indicates a wider spread in
    performance between the best and worst items.

    Args:
        ratings: List of EloRating objects

    Returns:
        Difference between max and min rating

    Raises:
        ValueError: If ratings list is empty

    Example:
        ```python
        ratings = [
            EloRating("a", 1200),
            EloRating("b", 1100),
            EloRating("c", 1000),
        ]
        pol = calculate_polarization(ratings)  # 200.0
        ```
    """
    if len(ratings) == 0:
        raise ValueError("Cannot calculate polarization: empty ratings list")

    if len(ratings) == 1:
        return 0.0

    ratings_values = [r.rating for r in ratings]
    return max(ratings_values) - min(ratings_values)


def predict_win_rate(
    elo_ratings: dict[str, float],
    scale: float = 400,
    base: float = 10,
) -> dict[str, dict[str, float]]:
    """Predict win rates between all pairs of items.

    Args:
        elo_ratings: Dictionary mapping item_id to ELO rating
        scale: ELO scale factor (default: 400)
        base: Base for the ELO formula (default: 10)

    Returns:
        Nested dictionary where win_rates[a][b] is the probability
        that item_a beats item_b

    Example:
        ```python
        ratings = {"model_a": 1200, "model_b": 1000}
        win_rates = predict_win_rate(ratings)
        print(win_rates["model_a"]["model_b"])  # ~0.76
        ```
    """
    items = sorted(elo_ratings.keys())
    win_rates: dict[str, dict[str, float]] = {}

    for item_a in items:
        win_rates[item_a] = {}
        rating_a = elo_ratings[item_a]

        for item_b in items:
            if item_a == item_b:
                win_rates[item_a][item_b] = 0.5  # Tie against self
            else:
                rating_b = elo_ratings[item_b]
                # Expected score for A against B
                expected = 1.0 / (1.0 + base ** ((rating_b - rating_a) / scale))
                win_rates[item_a][item_b] = expected

    return win_rates
