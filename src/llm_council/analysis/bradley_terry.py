"""Bradley-Terry analysis module for pairwise comparison aggregation.

This module implements the Bradley-Terry model for aggregating pairwise
comparisons into global rankings. It supports weighted wins (major vs minor)
and ties, with optional choix library integration.

Example:
    ```python
    from llm_council.analysis.bradley_terry import (
        PairwiseResult, BradleyTerryAnalyzer, pairwise_from_rankings
    )

    # Create pairwise results from rankings
    rankings = [
        ["Response A", "Response B", "Response C"],  # Reviewer 1
        ["Response B", "Response A", "Response C"],  # Reviewer 2
    ]
    pairwise_results = pairwise_from_rankings(rankings)

    # Fit Bradley-Terry model
    analyzer = BradleyTerryAnalyzer(pairwise_results)
    scores = analyzer.fit()

    # Get rankings
    ranked_items = analyzer.get_rankings()
    print(f"Best: {ranked_items[0][0]} (score: {ranked_items[0][1]:.3f})")

    # Get win probability between two items
    prob_a, prob_b = analyzer.get_win_probability("Response A", "Response B")
    print(f"P(A wins): {prob_a:.2%}, P(B wins): {prob_b:.2%}")
    ```
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_council.peer_review import RoleReview


# Constants for pairwise comparison outcomes
MAJOR_A_WIN = "A>>B"
MINOR_A_WIN = "A>B"
MINOR_B_WIN = "B>A"
MAJOR_B_WIN = "B>>A"
TIE = "A=B"


@dataclass
class PairwiseResult:
    """Store a single pairwise comparison between two items.

    Attributes:
        item_a: ID of the first item (e.g., role name or anonymous ID)
        item_b: ID of the second item
        winner: "a" if item_a won, "b" if item_b won, None for tie
        margin: "major" or "minor" indicating how decisive the win was
        metadata: Additional context about the comparison

    Example:
        ```python
        result = PairwiseResult(
            item_a="Response A",
            item_b="Response B",
            winner="a",
            margin="major",
            metadata={"reviewer": "critic", "round": 1}
        )
        ```
    """

    item_a: str
    item_b: str
    winner: str | None
    margin: str = "minor"
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        """Validate the winner and margin values."""
        if self.winner not in ("a", "b", None):
            raise ValueError(f"winner must be 'a', 'b', or None, got {self.winner}")
        if self.margin not in ("major", "minor"):
            raise ValueError(f"margin must be 'major' or 'minor', got {self.margin}")

    def get_winner_id(self) -> str | None:
        """Get the ID of the winning item, or None for tie.

        Returns:
            The ID of the winning item, or None if tied
        """
        if self.winner == "a":
            return self.item_a
        if self.winner == "b":
            return self.item_b
        return None

    def get_loser_id(self) -> str | None:
        """Get the ID of the losing item, or None for tie.

        Returns:
            The ID of the losing item, or None if tied
        """
        if self.winner == "a":
            return self.item_b
        if self.winner == "b":
            return self.item_a
        return None

    def to_choix_format(self, item_map: dict[str, int]) -> list[tuple[int, int]]:
        """Convert to choix library format.

        Args:
            item_map: Mapping from item IDs to integer indices

        Returns:
            List of (winner_idx, loser_idx) tuples. For ties, returns
            both possible outcomes with 0.5 weight each.
        """
        idx_a = item_map[self.item_a]
        idx_b = item_map[self.item_b]

        if self.winner == "a":
            return [(idx_a, idx_b)]
        if self.winner == "b":
            return [(idx_b, idx_a)]
        # Tie: return both directions (handled by weight in get_choix_data)
        return [(idx_a, idx_b), (idx_b, idx_a)]


class BradleyTerryAnalyzer:
    """Analyze pairwise comparisons using the Bradley-Terry model.

    The Bradley-Terry model assigns a score to each item such that the
    probability of item i beating item j is proportional to the ratio
    of their scores: P(i > j) = score_i / (score_i + score_j)

    This implementation supports:
    - Weighted wins (major wins count more than minor wins)
    - Ties (counted as 0.5 win for each item)
    - Optional choix library for advanced algorithms
    - Fallback iterative scaling when choix is unavailable

    Attributes:
        results: List of pairwise comparison results
        scores: Computed Bradley-Terry scores (available after fit())
        major_win_multiplier: How much more a major win counts (default: 3)

    Example:
        ```python
        results = [
            PairwiseResult("A", "B", winner="a", margin="major"),
            PairwiseResult("B", "C", winner="b", margin="minor"),
            PairwiseResult("A", "C", winner="a", margin="minor"),
        ]
        analyzer = BradleyTerryAnalyzer(results)
        scores = analyzer.fit()
        rankings = analyzer.get_rankings()
        ```
    """

    def __init__(
        self,
        results: list[PairwiseResult],
        major_win_multiplier: int = 3,
    ) -> None:
        """Initialize the analyzer with pairwise results.

        Args:
            results: List of pairwise comparison results
            major_win_multiplier: How much more a major win counts vs minor
        """
        self.results = results
        self.major_win_multiplier = major_win_multiplier
        self.scores: dict[str, float] = {}
        self._item_list: list[str] = []
        self._item_map: dict[str, int] = {}
        self._choix_params: list[float] | None = None

    def _build_item_map(self) -> None:
        """Build mapping from item IDs to integer indices."""
        items = set()
        for result in self.results:
            items.add(result.item_a)
            items.add(result.item_b)
        self._item_list = sorted(items)
        self._item_map = {item: i for i, item in enumerate(self._item_list)}

    def _get_choix_data(self) -> list[tuple[int, int]]:
        """Convert results to choix library format with weights.

        Returns:
            List of (winner_idx, loser_idx) tuples, with major wins
            repeated according to the multiplier.
        """
        data = []
        for result in self.results:
            if result.winner == "a":
                idx_winner = self._item_map[result.item_a]
                idx_loser = self._item_map[result.item_b]
                multiplier = (
                    self.major_win_multiplier if result.margin == "major" else 1
                )
                for _ in range(multiplier):
                    data.append((idx_winner, idx_loser))
            elif result.winner == "b":
                idx_winner = self._item_map[result.item_b]
                idx_loser = self._item_map[result.item_a]
                multiplier = (
                    self.major_win_multiplier if result.margin == "major" else 1
                )
                for _ in range(multiplier):
                    data.append((idx_winner, idx_loser))
            else:
                # Tie: add both directions (each counts as half)
                idx_a = self._item_map[result.item_a]
                idx_b = self._item_map[result.item_b]
                data.append((idx_a, idx_b))
                data.append((idx_b, idx_a))
        return data

    def _compute_win_matrix(self) -> dict[tuple[str, str], float]:
        """Compute weighted win counts between all pairs.

        Returns:
            Dictionary mapping (winner, loser) to weighted win count.
            Ties contribute 0.5 to both directions.
        """
        wins: dict[tuple[str, str], float] = {}
        for result in self.results:
            if result.winner == "a":
                weight = (
                    self.major_win_multiplier if result.margin == "major" else 1.0
                )
                key = (result.item_a, result.item_b)
                wins[key] = wins.get(key, 0.0) + weight
            elif result.winner == "b":
                weight = (
                    self.major_win_multiplier if result.margin == "major" else 1.0
                )
                key = (result.item_b, result.item_a)
                wins[key] = wins.get(key, 0.0) + weight
            else:
                # Tie: 0.5 to each
                key_ab = (result.item_a, result.item_b)
                key_ba = (result.item_b, result.item_a)
                wins[key_ab] = wins.get(key_ab, 0.0) + 0.5
                wins[key_ba] = wins.get(key_ba, 0.0) + 0.5
        return wins

    def _fit_iterative_scaling(
        self, max_iter: int = 100, tol: float = 1e-6
    ) -> dict[str, float]:
        """Fit Bradley-Terry model using iterative scaling (fallback method).

        This is a simple implementation that doesn't require the choix library.
        It uses the MM algorithm to estimate parameters.

        Args:
            max_iter: Maximum number of iterations
            tol: Convergence tolerance

        Returns:
            Dictionary mapping item IDs to scores
        """
        wins = self._compute_win_matrix()
        items = self._item_list
        n = len(items)

        if n == 0:
            return {}
        if n == 1:
            return {items[0]: 1.0}

        # Compute total weighted wins and losses for each item
        total_wins = {item: 0.0 for item in items}
        total_losses = {item: 0.0 for item in items}

        for (winner, loser), count in wins.items():
            total_wins[winner] += count
            total_losses[loser] += count

        # Initialize scores uniformly
        scores = {item: 1.0 for item in items}

        # Iterative scaling (MM algorithm)
        for _ in range(max_iter):
            new_scores = {}
            max_change = 0.0

            for item in items:
                # Denominator: sum over all opponents
                denom = 0.0
                for other in items:
                    if other != item:
                        # Count of comparisons between item and other
                        n_comparisons = wins.get(
                            (item, other), 0.0
                        ) + wins.get((other, item), 0.0)
                        if n_comparisons > 0:
                            denom += n_comparisons / (scores[item] + scores[other])

                if denom > 0:
                    new_scores[item] = total_wins[item] / denom
                else:
                    new_scores[item] = scores[item]

                # Ensure score is positive
                new_scores[item] = max(new_scores[item], 1e-10)

                # Normalize to prevent overflow/underflow
                max_change = max(max_change, abs(new_scores[item] - scores[item]))

            scores = new_scores

            # Normalize scores (geometric mean = 1)
            log_sum = sum(math.log(max(s, 1e-10)) for s in scores.values())
            geo_mean = math.exp(log_sum / len(scores))
            scores = {k: max(v / geo_mean, 1e-10) for k, v in scores.items()}

            if max_change < tol:
                break

        return scores

    def fit(self) -> dict[str, float]:
        """Compute Bradley-Terry scores for all items.

        Uses the choix library if available, otherwise falls back to
        a simple iterative scaling implementation.

        Returns:
            Dictionary mapping item IDs to Bradley-Terry scores.
            Higher scores indicate stronger items.
        """
        self._build_item_map()

        if not self._item_list:
            self.scores = {}
            return self.scores

        # Try to use choix library
        try:
            import choix

            data = self._get_choix_data()
            n_items = len(self._item_list)

            if n_items == 1:
                self.scores = {self._item_list[0]: 1.0}
                return self.scores

            if not data:
                # No comparisons, return uniform scores
                self.scores = {item: 1.0 for item in self._item_list}
                return self.scores

            # Use iterative Luce spectral ranking
            params = choix.ilsr_pairwise(n_items, data)
            self._choix_params = list(params)
            self.scores = {
                self._item_list[i]: math.exp(params[i])
                for i in range(n_items)
            }
        except (ImportError, ValueError):
            # Fallback to iterative scaling if choix not available or fails
            # ValueError can occur if Markov chain isn't fully connected
            self.scores = self._fit_iterative_scaling()

        return self.scores

    def get_win_probability(self, item_a: str, item_b: str) -> tuple[float, float]:
        """Get the probability of each item winning against the other.

        Args:
            item_a: ID of the first item
            item_b: ID of the second item

        Returns:
            Tuple of (probability_a_wins, probability_b_wins)

        Raises:
            ValueError: If scores haven't been computed or items not found
        """
        if not self.scores:
            raise ValueError("Must call fit() before get_win_probability()")

        if item_a not in self.scores:
            raise ValueError(f"Item '{item_a}' not found in scores")
        if item_b not in self.scores:
            raise ValueError(f"Item '{item_b}' not found in scores")

        score_a = self.scores[item_a]
        score_b = self.scores[item_b]

        # If using choix, use their probability function for consistency
        if self._choix_params is not None and hasattr(self, "_item_map"):
            try:
                import choix

                idx_a = self._item_map[item_a]
                idx_b = self._item_map[item_b]
                probs = choix.probabilities([idx_a, idx_b], self._choix_params)
                return (probs[0], probs[1])
            except ImportError:
                pass

        # Standard Bradley-Terry formula
        total = score_a + score_b
        prob_a = score_a / total
        prob_b = score_b / total
        return (prob_a, prob_b)

    def get_rankings(self) -> list[tuple[str, float]]:
        """Get items sorted by their Bradley-Terry scores.

        Returns:
            List of (item_id, score) tuples sorted by score descending
            (highest score first)

        Raises:
            ValueError: If scores haven't been computed
        """
        if not self.scores:
            raise ValueError("Must call fit() before get_rankings()")

        return sorted(self.scores.items(), key=lambda x: x[1], reverse=True)

    def to_dataframe(self) -> "pd.DataFrame":
        """Export rankings to a pandas DataFrame.

        Returns:
            DataFrame with columns: item, score, rank

        Raises:
            ValueError: If scores haven't been computed
            ImportError: If pandas is not installed
        """
        if not self.scores:
            raise ValueError("Must call fit() before to_dataframe()")

        try:
            import pandas as pd
        except ImportError as e:
            raise ImportError(
                "pandas is required for to_dataframe(). "
                "Install with: pip install pandas"
            ) from e

        rankings = self.get_rankings()
        data = [
            {"item": item, "score": score, "rank": i + 1}
            for i, (item, score) in enumerate(rankings)
        ]
        return pd.DataFrame(data)

    def get_expected_win_matrix(self) -> dict[str, dict[str, float]]:
        """Get expected win probability matrix for all pairs.

        Returns:
            Nested dictionary where result[i][j] is the probability
            of item i beating item j.

        Raises:
            ValueError: If scores haven't been computed
        """
        if not self.scores:
            raise ValueError("Must call fit() before get_expected_win_matrix()")

        items = list(self.scores.keys())
        matrix: dict[str, dict[str, float]] = {
            item: {} for item in items
        }

        for item_i in items:
            for item_j in items:
                if item_i == item_j:
                    matrix[item_i][item_j] = 0.5  # Tie with self
                else:
                    prob_i, prob_j = self.get_win_probability(item_i, item_j)
                    matrix[item_i][item_j] = prob_i

        return matrix


def pairwise_from_rankings(
    rankings: list[list[str]],
    major_gap_threshold: int = 2,
) -> list[PairwiseResult]:
    """Convert a list of rankings to pairwise comparison results.

    For each ranking, generates pairwise comparisons between all pairs
    of items. The winner is the item that appears earlier in the ranking.

    Args:
        rankings: List of rankings, where each ranking is an ordered list
            of item IDs from best to worst
        major_gap_threshold: Rank difference threshold for considering
            a win as "major" (default: 2 positions)

    Returns:
        List of PairwiseResult objects

    Example:
        ```python
        rankings = [
            ["A", "B", "C"],  # A > B > C
            ["B", "A", "C"],  # B > A > C
        ]
        results = pairwise_from_rankings(rankings)
        # Generates: A>B (minor), A>C (major), B>C (minor)
        #            B>A (minor), B>C (minor), A>C (major)
        ```
    """
    results = []

    for ranking in rankings:
        n = len(ranking)
        for i in range(n):
            for j in range(i + 1, n):
                item_a = ranking[i]
                item_b = ranking[j]
                gap = j - i

                # Earlier in ranking = winner
                margin = "major" if gap >= major_gap_threshold else "minor"
                results.append(
                    PairwiseResult(
                        item_a=item_a,
                        item_b=item_b,
                        winner="a",
                        margin=margin,
                        metadata={"rank_gap": gap},
                    )
                )

    return results


def pairwise_from_reviews(
    reviews: list["RoleReview"],
    major_gap_threshold: int = 2,
) -> list[PairwiseResult]:
    """Convert RoleReview rankings to pairwise comparison results.

    Extracts rankings from RoleReview objects and converts them to
    pairwise comparisons. Each review generates comparisons between
    all pairs in the ranking.

    Args:
        reviews: List of RoleReview objects containing rankings
        major_gap_threshold: Rank difference threshold for major wins

    Returns:
        List of PairwiseResult objects with reviewer metadata

    Example:
        ```python
        from llm_council.peer_review import RoleReview

        reviews = [
            RoleReview(reviewer_role="critic", rankings=["A", "B", "C"]),
            RoleReview(reviewer_role="expert", rankings=["B", "A", "C"]),
        ]
        results = pairwise_from_reviews(reviews)
        ```
    """
    results = []

    for review in reviews:
        if not review.rankings:
            continue

        ranking = review.rankings
        n = len(ranking)

        for i in range(n):
            for j in range(i + 1, n):
                item_a = ranking[i]
                item_b = ranking[j]
                gap = j - i

                margin = "major" if gap >= major_gap_threshold else "minor"
                results.append(
                    PairwiseResult(
                        item_a=item_a,
                        item_b=item_b,
                        winner="a",
                        margin=margin,
                        metadata={
                            "reviewer": review.reviewer_role,
                            "rank_gap": gap,
                        },
                    )
                )

    return results
