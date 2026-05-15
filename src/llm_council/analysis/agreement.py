"""Judge agreement analysis for peer review evaluations.

This module provides tools for analyzing agreement between judges in peer review
scenarios, including exact agreement, sidewise agreement (direction only), and
Cohen's kappa coefficient.

Example:
    ```python
    from llm_council.analysis.agreement import JudgeAgreementAnalyzer
    from llm_council.peer_review import RoleReview

    # Create reviews from multiple judges
    reviews_by_judge = {
        "judge_a": [review1, review2, ...],
        "judge_b": [review3, review4, ...],
    }

    analyzer = JudgeAgreementAnalyzer(reviews_by_judge)

    # Calculate agreement between two judges
    agreement = analyzer.calculate_agreement("judge_a", "judge_b", method="exact")

    # Get full agreement matrix
    matrix = analyzer.get_agreement_matrix(method="sidewise")

    # Find items all judges agree on
    consensus_items = analyzer.find_consensus_items()
    ```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_council.peer_review import RoleReview

# Optional sklearn import for Cohen's kappa
try:
    from sklearn.metrics import cohen_kappa_score

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


# Agreement method constants
AGREEMENT_METHODS = ["exact", "sidewise", "cohen_kappa"]


@dataclass
class AgreementMetrics:
    """Metrics for agreement between two judges.

    Attributes:
        judge_a: Name of the first judge
        judge_b: Name of the second judge
        exact_agreement: Percentage of identical ratings (0.0 to 1.0)
        sidewise_agreement: Percentage agreeing on direction (0.0 to 1.0)
        cohen_kappa: Cohen's kappa coefficient (-1.0 to 1.0), None if sklearn unavailable
        num_comparisons: Number of items compared between the two judges
    """

    judge_a: str
    judge_b: str
    exact_agreement: float
    sidewise_agreement: float
    cohen_kappa: float | None
    num_comparisons: int

    def to_dict(self) -> dict:
        """Convert metrics to a dictionary representation."""
        return {
            "judge_a": self.judge_a,
            "judge_b": self.judge_b,
            "exact_agreement": self.exact_agreement,
            "sidewise_agreement": self.sidewise_agreement,
            "cohen_kappa": self.cohen_kappa,
            "num_comparisons": self.num_comparisons,
        }


@dataclass
class ComparisonRating:
    """Internal representation of a comparison rating.

    This normalizes different rating formats into a consistent structure
    for agreement calculation.

    Attributes:
        item_a: First item being compared
        item_b: Second item being compared
        winner: Which item won ("a", "b", or "tie")
        strength: Strength of preference ("major" or "minor")
        raw_rating: Original rating string
    """

    item_a: str
    item_b: str
    winner: str  # "a", "b", or "tie"
    strength: str  # "major", "minor", or "none"
    raw_rating: str


def extract_ranking_from_review(review: RoleReview) -> list[str]:
    """Extract the ranking from a RoleReview as a list of item IDs.

    Args:
        review: The RoleReview to extract ranking from

    Returns:
        List of item IDs in ranked order (best first)

    Example:
        ```python
        review = RoleReview(
            reviewer_role="critic",
            rankings=["Response A", "Response B", "Response C"]
        )
        ranking = extract_ranking_from_review(review)
        # Returns: ["Response A", "Response B", "Response C"]
        ```
    """
    return list(review.rankings)


def convert_reviews_to_matrix(
    reviews: list[RoleReview],
) -> dict[tuple[str, str], ComparisonRating]:
    """Convert a list of RoleReviews to a comparison matrix.

    This converts rankings into pairwise comparison ratings. For example,
    a ranking [A, B, C] becomes comparisons: A>B, A>C, B>C.

    Args:
        reviews: List of RoleReview objects

    Returns:
        Dictionary mapping (item_a, item_b) tuples to ComparisonRating objects

    Example:
        ```python
        reviews = [
            RoleReview(reviewer_role="judge1", rankings=["A", "B", "C"]),
        ]
        matrix = convert_reviews_to_matrix(reviews)
        # matrix[("A", "B")] -> ComparisonRating(winner="a", ...)
        ```
    """
    comparisons: dict[tuple[str, str], ComparisonRating] = {}

    for review in reviews:
        rankings = extract_ranking_from_review(review)

        # Generate all pairwise comparisons from the ranking
        for i, item_a in enumerate(rankings):
            for item_b in rankings[i + 1 :]:
                # item_a is ranked higher than item_b
                comparison = ComparisonRating(
                    item_a=item_a,
                    item_b=item_b,
                    winner="a",
                    strength="minor",
                    raw_rating=f"{item_a}>{item_b}",
                )
                comparisons[(item_a, item_b)] = comparison

    return comparisons


def _get_comparison_side(rating: ComparisonRating | str) -> str:
    """Get the side/direction of a comparison.

    Args:
        rating: Either a ComparisonRating object or a raw rating string

    Returns:
        "a" if A wins, "b" if B wins, "tie" for ties
    """
    if isinstance(rating, ComparisonRating):
        return rating.winner

    # Handle string ratings
    rating_str = str(rating).upper().strip()

    if rating_str in ("A>B", "A>>B", "A", "A WINS", "1"):
        return "a"
    if rating_str in ("B>A", "B>>A", "B", "B WINS", "2"):
        return "b"
    return "tie"


def _normalize_rating(rating: str) -> str:
    """Normalize a rating string to a standard format.

    Args:
        rating: Raw rating string

    Returns:
        Normalized rating string
    """
    rating_str = str(rating).upper().strip()

    # Map various formats to standard format
    if rating_str in ("A>>B", "A STRONGLY WINS"):
        return "A>>B"
    if rating_str in ("A>B", "A WINS"):
        return "A>B"
    if rating_str in ("B>>A", "B STRONGLY WINS"):
        return "B>>A"
    if rating_str in ("B>A", "B WINS"):
        return "B>A"
    if rating_str in ("TIE", "EQUAL", "SAME", "A=B"):
        return "TIE"

    return rating_str


def _calculate_exact_agreement(
    ratings_a: list[str], ratings_b: list[str]
) -> float:
    """Calculate exact agreement percentage.

    Args:
        ratings_a: List of ratings from judge A
        ratings_b: List of ratings from judge B

    Returns:
        Percentage of identical ratings (0.0 to 1.0)
    """
    if not ratings_a or not ratings_b or len(ratings_a) != len(ratings_b):
        return 0.0

    matches = sum(
        1 for r_a, r_b in zip(ratings_a, ratings_b) if r_a == r_b
    )
    return matches / len(ratings_a)


def _calculate_sidewise_agreement(
    ratings_a: list[str], ratings_b: list[str]
) -> float:
    """Calculate sidewise agreement percentage (agreement on direction).

    Sidewise agreement counts matches where both judges agree on which
    side wins (A wins, B wins, or tie), even if the strength differs.

    Args:
        ratings_a: List of ratings from judge A
        ratings_b: List of ratings from judge B

    Returns:
        Percentage of sidewise agreement (0.0 to 1.0)
    """
    if not ratings_a or not ratings_b or len(ratings_a) != len(ratings_b):
        return 0.0

    matches = 0
    for r_a, r_b in zip(ratings_a, ratings_b):
        side_a = _get_comparison_side(r_a)
        side_b = _get_comparison_side(r_b)

        # Count as agreement if sides match, or if either is a tie
        if side_a == side_b or side_a == "tie" or side_b == "tie":
            matches += 1

    return matches / len(ratings_a)


def _calculate_cohen_kappa(
    ratings_a: list[str], ratings_b: list[str]
) -> float | None:
    """Calculate Cohen's kappa coefficient.

    Args:
        ratings_a: List of ratings from judge A
        ratings_b: List of ratings from judge B

    Returns:
        Cohen's kappa coefficient (-1.0 to 1.0), or None if sklearn unavailable
    """
    if not SKLEARN_AVAILABLE:
        return None

    if not ratings_a or not ratings_b or len(ratings_a) != len(ratings_b):
        return None

    try:
        # Get unique labels from both raters
        all_labels = sorted(set(ratings_a) | set(ratings_b))

        if len(all_labels) < 2:
            return None

        kappa = cohen_kappa_score(ratings_a, ratings_b, labels=all_labels)
        return float(kappa)
    except Exception:
        return None


class JudgeAgreementAnalyzer:
    """Analyzer for calculating agreement between judges in peer review.

    This class provides methods to calculate various agreement metrics between
    judges, including exact agreement, sidewise agreement, and Cohen's kappa.

    Attributes:
        reviews_by_judge: Dictionary mapping judge names to their RoleReview lists

    Example:
        ```python
        reviews_by_judge = {
            "judge_a": [review1, review2],
            "judge_b": [review3, review4],
        }

        analyzer = JudgeAgreementAnalyzer(reviews_by_judge)

        # Calculate specific agreement
        agreement = analyzer.calculate_agreement("judge_a", "judge_b")

        # Get full metrics
        metrics = analyzer.get_agreement_metrics("judge_a", "judge_b")
        ```
    """

    def __init__(self, reviews_by_judge: dict[str, list[RoleReview]]) -> None:
        """Initialize the analyzer with reviews organized by judge.

        Args:
            reviews_by_judge: Dictionary mapping judge names to lists of RoleReview
        """
        self.reviews_by_judge = reviews_by_judge
        self._comparison_cache: dict[str, dict[tuple[str, str], ComparisonRating]] = {}

    def _get_judge_comparisons(
        self, judge: str
    ) -> dict[tuple[str, str], ComparisonRating]:
        """Get cached comparisons for a judge.

        Args:
            judge: Name of the judge

        Returns:
            Dictionary of comparisons for this judge
        """
        if judge not in self._comparison_cache:
            reviews = self.reviews_by_judge.get(judge, [])
            self._comparison_cache[judge] = convert_reviews_to_matrix(reviews)
        return self._comparison_cache[judge]

    def _get_common_items(
        self, judge_a: str, judge_b: str
    ) -> list[tuple[tuple[str, str], ComparisonRating, ComparisonRating]]:
        """Get items that both judges have rated.

        Args:
            judge_a: Name of first judge
            judge_b: Name of second judge

        Returns:
            List of tuples (item_key, rating_a, rating_b)
        """
        comparisons_a = self._get_judge_comparisons(judge_a)
        comparisons_b = self._get_judge_comparisons(judge_b)

        # Find common comparison keys
        common_keys = set(comparisons_a.keys()) & set(comparisons_b.keys())

        return [
            (key, comparisons_a[key], comparisons_b[key])
            for key in common_keys
        ]

    def calculate_agreement(
        self, judge_a: str, judge_b: str, method: str = "exact"
    ) -> float:
        """Calculate agreement between two judges.

        Args:
            judge_a: Name of the first judge
            judge_b: Name of the second judge
            method: Agreement method ("exact", "sidewise", or "cohen_kappa")

        Returns:
            Agreement score (0.0 to 1.0 for exact/sidewise, -1.0 to 1.0 for kappa)

        Raises:
            ValueError: If method is not recognized

        Example:
            ```python
            analyzer = JudgeAgreementAnalyzer(reviews_by_judge)

            # Exact agreement
            exact = analyzer.calculate_agreement("judge_a", "judge_b", "exact")

            # Sidewise agreement
            side = analyzer.calculate_agreement("judge_a", "judge_b", "sidewise")
            ```
        """
        if method not in AGREEMENT_METHODS:
            raise ValueError(f"Unknown agreement method: {method}")

        common_items = self._get_common_items(judge_a, judge_b)

        if not common_items:
            return 0.0

        # Extract raw ratings for comparison
        ratings_a = [item[1].raw_rating for item in common_items]
        ratings_b = [item[2].raw_rating for item in common_items]

        if method == "exact":
            return _calculate_exact_agreement(ratings_a, ratings_b)
        elif method == "sidewise":
            return _calculate_sidewise_agreement(ratings_a, ratings_b)
        elif method == "cohen_kappa":
            kappa = _calculate_cohen_kappa(ratings_a, ratings_b)
            return kappa if kappa is not None else 0.0

        return 0.0

    def get_agreement_metrics(self, judge_a: str, judge_b: str) -> AgreementMetrics:
        """Get comprehensive agreement metrics between two judges.

        Args:
            judge_a: Name of the first judge
            judge_b: Name of the second judge

        Returns:
            AgreementMetrics object with all agreement measures
        """
        common_items = self._get_common_items(judge_a, judge_b)
        num_comparisons = len(common_items)

        if num_comparisons == 0:
            return AgreementMetrics(
                judge_a=judge_a,
                judge_b=judge_b,
                exact_agreement=0.0,
                sidewise_agreement=0.0,
                cohen_kappa=None,
                num_comparisons=0,
            )

        ratings_a = [item[1].raw_rating for item in common_items]
        ratings_b = [item[2].raw_rating for item in common_items]

        exact = _calculate_exact_agreement(ratings_a, ratings_b)
        sidewise = _calculate_sidewise_agreement(ratings_a, ratings_b)
        kappa = _calculate_cohen_kappa(ratings_a, ratings_b)

        return AgreementMetrics(
            judge_a=judge_a,
            judge_b=judge_b,
            exact_agreement=exact,
            sidewise_agreement=sidewise,
            cohen_kappa=kappa,
            num_comparisons=num_comparisons,
        )

    def get_agreement_matrix(self, method: str = "exact") -> dict[str, dict[str, float]]:
        """Get an agreement matrix for all judges.

        Args:
            method: Agreement method ("exact", "sidewise", or "cohen_kappa")

        Returns:
            Nested dictionary mapping judge_a -> judge_b -> agreement score

        Example:
            ```python
            analyzer = JudgeAgreementAnalyzer(reviews_by_judge)
            matrix = analyzer.get_agreement_matrix("exact")

            # Access agreement between specific judges
            agreement = matrix["judge_a"]["judge_b"]
            ```
        """
        judges = list(self.reviews_by_judge.keys())
        matrix: dict[str, dict[str, float]] = {}

        for judge_a in judges:
            matrix[judge_a] = {}
            for judge_b in judges:
                if judge_a == judge_b:
                    # Perfect agreement with self
                    matrix[judge_a][judge_b] = 1.0
                else:
                    matrix[judge_a][judge_b] = self.calculate_agreement(
                        judge_a, judge_b, method
                    )

        return matrix

    def get_mean_agreement(self, method: str = "exact") -> dict[str, float]:
        """Calculate mean agreement for each judge with all other judges.

        Args:
            method: Agreement method ("exact", "sidewise", or "cohen_kappa")

        Returns:
            Dictionary mapping judge name to mean agreement score

        Example:
            ```python
            analyzer = JudgeAgreementAnalyzer(reviews_by_judge)
            mean_agreements = analyzer.get_mean_agreement("exact")

            # Get mean agreement for a specific judge
            judge_a_mean = mean_agreements["judge_a"]
            ```
        """
        matrix = self.get_agreement_matrix(method)
        mean_agreement: dict[str, float] = {}

        for judge, agreements in matrix.items():
            # Exclude self-agreement (always 1.0)
            other_agreements = [
                score for other_judge, score in agreements.items()
                if other_judge != judge
            ]

            if other_agreements:
                mean_agreement[judge] = sum(other_agreements) / len(other_agreements)
            else:
                mean_agreement[judge] = 0.0

        return mean_agreement

    def find_consensus_items(self) -> list[str]:
        """Find items that all judges agree on.

        An item is considered to have consensus if all judges who rated it
        give it the same relative ranking or comparison outcome.

        Returns:
            List of item identifiers with consensus
        """
        # Get all unique items from all reviews
        all_items: set[str] = set()
        for reviews in self.reviews_by_judge.values():
            for review in reviews:
                all_items.update(review.rankings)

        consensus_items: list[str] = []

        for item in all_items:
            # Collect all rankings for this item
            rankings: dict[str, int] = {}
            for judge, reviews in self.reviews_by_judge.items():
                for review in reviews:
                    rank = review.get_ranking_score(item)
                    if rank is not None:
                        rankings[judge] = rank
                        break

            if len(rankings) < 2:
                # Not enough judges rated this item
                continue

            # Check if all judges agree on the relative position
            # For now, we consider consensus if all judges rank it in the same position
            rank_values = list(rankings.values())
            if len(set(rank_values)) == 1:
                consensus_items.append(item)

        return consensus_items

    def find_disputed_items(self) -> list[str]:
        """Find items with disagreement between judges.

        An item is considered disputed if judges give it different rankings
        or comparison outcomes.

        Returns:
            List of item identifiers with disagreement
        """
        # Get all unique items from all reviews
        all_items: set[str] = set()
        for reviews in self.reviews_by_judge.values():
            for review in reviews:
                all_items.update(review.rankings)

        consensus_items = set(self.find_consensus_items())

        # Return items that are not in consensus
        disputed = [
            item for item in all_items
            if item not in consensus_items
        ]

        return disputed

    def get_all_metrics(self) -> list[AgreementMetrics]:
        """Get agreement metrics for all judge pairs.

        Returns:
            List of AgreementMetrics for all unique judge pairs
        """
        judges = list(self.reviews_by_judge.keys())
        metrics: list[AgreementMetrics] = []

        for i, judge_a in enumerate(judges):
            for judge_b in judges[i + 1 :]:
                metrics.append(self.get_agreement_metrics(judge_a, judge_b))

        return metrics

    def summarize(self) -> dict:
        """Get a summary of agreement across all judges.

        Returns:
            Dictionary with summary statistics
        """
        all_metrics = self.get_all_metrics()

        if not all_metrics:
            return {
                "num_judges": len(self.reviews_by_judge),
                "num_pairs": 0,
                "mean_exact_agreement": 0.0,
                "mean_sidewise_agreement": 0.0,
                "mean_cohen_kappa": None,
            }

        exact_agreements = [m.exact_agreement for m in all_metrics]
        sidewise_agreements = [m.sidewise_agreement for m in all_metrics]
        kappas = [m.cohen_kappa for m in all_metrics if m.cohen_kappa is not None]

        summary = {
            "num_judges": len(self.reviews_by_judge),
            "num_pairs": len(all_metrics),
            "mean_exact_agreement": sum(exact_agreements) / len(exact_agreements),
            "mean_sidewise_agreement": sum(sidewise_agreements)
            / len(sidewise_agreements),
            "mean_cohen_kappa": sum(kappas) / len(kappas) if kappas else None,
            "consensus_items": len(self.find_consensus_items()),
            "disputed_items": len(self.find_disputed_items()),
        }

        return summary
