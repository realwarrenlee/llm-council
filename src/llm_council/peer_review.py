"""Peer review system for anonymized multi-role evaluation.

This module implements a two-stage deliberation process where:
1. Stage 1: All roles generate initial responses to a task
2. Stage 2: Roles review anonymized responses from Stage 1 and provide rankings/evaluations

Example:
    ```python
    from llm_council import Council, RoleRegistry
    from llm_council.peer_review import PeerReview
    from llm_council.providers import OpenRouterProvider

    # Setup
    registry = RoleRegistry.from_presets("advocate", "critic", "synthesizer")
    provider = OpenRouterProvider()
    council = Council(registry, provider=provider)

    # Create peer review system
    peer_review = PeerReview(council)

    # Run two-stage deliberation with ranking
    result = await peer_review.deliberate_with_review(
        task="Should we use microservices?",
        review_prompt_template=PeerReview.RANKING_PROMPT,
    )

    # Access results
    print(f"Initial responses: {len(result.initial_output.results)}")
    print(f"Review rounds: {len(result.review_rounds)}")
    print(f"Final rankings: {result.get_aggregate_rankings()}")
    ```
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from llm_council.anonymization import parse_ranking_from_text

if TYPE_CHECKING:
    from llm_council.council import Council, CouncilOutput, CouncilResult
    from llm_council.roles import Role


@dataclass
class AnonymousResponse:
    """An anonymized response for peer review.

    Attributes:
        anonymous_id: Unique identifier for this anonymized response (e.g., "Response A")
        content: The actual response content
        original_role: The original role that generated this response (revealed after review)
    """

    anonymous_id: str
    content: str
    original_role: str


@dataclass
class RoleReview:
    """A single role's review of anonymized responses.

    Attributes:
        reviewer_role: Name of the role providing the review
        rankings: Ordered list of anonymous_ids from best to worst (for ranking mode)
        evaluations: Dict mapping anonymous_id to evaluation score/feedback (for evaluation mode)
        reasoning: Optional reasoning/explanation for the review
        error: Error message if review generation failed
    """

    reviewer_role: str
    rankings: list[str] = field(default_factory=list)
    evaluations: dict[str, str] = field(default_factory=dict)
    reasoning: str = ""
    error: str | None = None

    @property
    def success(self) -> bool:
        """Check if this review was successfully generated."""
        return self.error is None

    def get_ranking_score(self, anonymous_id: str) -> int | None:
        """Get the ranking score for a response (lower is better, 1 = top ranked).

        Args:
            anonymous_id: The anonymous response ID

        Returns:
            The rank position (1-indexed) or None if not ranked
        """
        if anonymous_id in self.rankings:
            return self.rankings.index(anonymous_id) + 1
        return None


@dataclass
class ReviewRound:
    """A complete round of peer reviews.

    Attributes:
        round_number: Which review round this is (1-indexed)
        anonymous_responses: List of anonymized responses being reviewed
        reviews: List of reviews from participating roles
        prompt_template: The prompt template used for this round
    """

    round_number: int
    anonymous_responses: list[AnonymousResponse] = field(default_factory=list)
    reviews: list[RoleReview] = field(default_factory=list)
    prompt_template: str = ""

    def get_response_by_id(self, anonymous_id: str) -> AnonymousResponse | None:
        """Get an anonymized response by its ID."""
        for resp in self.anonymous_responses:
            if resp.anonymous_id == anonymous_id:
                return resp
        return None

    def get_reviews_for_response(self, anonymous_id: str) -> list[RoleReview]:
        """Get all reviews that mention a specific response."""
        return [
            review for review in self.reviews
            if anonymous_id in review.rankings or anonymous_id in review.evaluations
        ]

    def get_average_rank(self, anonymous_id: str) -> float | None:
        """Calculate the average rank for a response across all reviews.

        Args:
            anonymous_id: The anonymous response ID

        Returns:
            Average rank (lower is better) or None if no rankings
        """
        ranks = [
            review.get_ranking_score(anonymous_id)
            for review in self.reviews
            if review.get_ranking_score(anonymous_id) is not None
        ]
        if not ranks:
            return None
        return sum(ranks) / len(ranks)


@dataclass
class PeerReviewResult:
    """Complete result from a peer review deliberation.

    Attributes:
        task: The original task/prompt
        initial_output: Output from Stage 1 (initial responses)
        review_rounds: List of review rounds conducted
        final_synthesis: Optional synthesis of review results
    """

    task: str
    initial_output: CouncilOutput
    review_rounds: list[ReviewRound] = field(default_factory=list)
    final_synthesis: str | None = None

    def get_aggregate_rankings(self) -> dict[str, float]:
        """Get aggregate rankings from the first review round.

        Returns:
            Dict mapping anonymous_id to average rank (lower is better)
        """
        if not self.review_rounds:
            return {}

        round_one = self.review_rounds[0]
        rankings = {}
        for resp in round_one.anonymous_responses:
            avg_rank = round_one.get_average_rank(resp.anonymous_id)
            if avg_rank is not None:
                rankings[resp.anonymous_id] = avg_rank

        # Sort by rank (lower is better)
        return dict(sorted(rankings.items(), key=lambda x: x[1]))

    def get_best_response(self) -> AnonymousResponse | None:
        """Get the best response based on aggregate rankings.

        Returns:
            The highest-ranked anonymous response or None if no rankings
        """
        rankings = self.get_aggregate_rankings()
        if not rankings:
            return None

        best_id = min(rankings.keys(), key=lambda k: rankings[k])

        if not self.review_rounds:
            return None

        return self.review_rounds[0].get_response_by_id(best_id)

    def get_response_ranking_with_roles(self) -> list[tuple[str, float, str]]:
        """Get ranking with original role names revealed.

        Returns:
            List of tuples (role_name, average_rank, content) sorted by rank
        """
        if not self.review_rounds:
            return []

        round_one = self.review_rounds[0]
        rankings = self.get_aggregate_rankings()

        result = []
        for anonymous_id, avg_rank in rankings.items():
            resp = round_one.get_response_by_id(anonymous_id)
            if resp:
                result.append((resp.original_role, avg_rank, resp.content))

        return result

    def get_evaluation_summary(self) -> dict[str, dict[str, str]]:
        """Get a summary of all evaluations by response.

        Returns:
            Dict mapping anonymous_id to dict of reviewer -> evaluation
        """
        if not self.review_rounds:
            return {}

        summary = {}
        for resp in self.review_rounds[0].anonymous_responses:
            summary[resp.anonymous_id] = {}

        for review in self.review_rounds[0].reviews:
            for anonymous_id, evaluation in review.evaluations.items():
                if anonymous_id in summary:
                    summary[anonymous_id][review.reviewer_role] = evaluation

        return summary


class PeerReview:
    """Manages anonymized peer review of council deliberations.

    The PeerReview class implements a two-stage deliberation process:
    1. Stage 1: Initial responses from all participating roles
    2. Stage 2: Anonymized peer review where roles rank/evaluate responses

    Attributes:
        council: The Council instance to use for deliberation
        anonymization_fn: Optional custom function to anonymize responses

    Example:
        ```python
        peer_review = PeerReview(council)

        # Using ranking prompt
        result = await peer_review.deliberate_with_review(
            task="Evaluate this architecture proposal",
            review_prompt_template=PeerReview.RANKING_PROMPT,
        )

        # Using evaluation prompt
        result = await peer_review.deliberate_with_review(
            task="Evaluate this architecture proposal",
            review_prompt_template=PeerReview.EVALUATION_PROMPT,
            review_mode="evaluate",
        )

        # Custom anonymization
        def custom_anonymize(response, index):
            return AnonymousResponse(
                anonymous_id=f"Option {index + 1}",
                content=response.content,
                original_role=response.role_name,
            )

        peer_review = PeerReview(council, anonymization_fn=custom_anonymize)
        ```
    """

    # Default prompt templates
    RANKING_PROMPT = """You are participating in a peer review process. Below are anonymized responses to the task: "{task}"

Your job is to rank these responses from best to worst based on:
- Accuracy and correctness
- Clarity and coherence
- Completeness of the answer
- Insightfulness and depth

{responses}

Please provide your ranking as a simple ordered list (best first):
1. Response X
2. Response Y
3. Response Z

Also briefly explain your reasoning (2-3 sentences)."""

    EVALUATION_PROMPT = """You are participating in a peer review process. Below are anonymized responses to the task: "{task}"

Your job is to evaluate each response on the following criteria:
- Strengths: What does this response do well?
- Weaknesses: What could be improved?
- Score: Rate 1-10 (10 = excellent)

{responses}

Please provide your evaluation for each response in this format:

Response X:
- Score: [1-10]
- Strengths: [your assessment]
- Weaknesses: [your assessment]

Response Y:
- Score: [1-10]
- Strengths: [your assessment]
- Weaknesses: [your assessment]

(Continue for all responses...)"""

    SYNTHESIS_PROMPT = """You are synthesizing peer review results. The task was: "{task}"

Initial responses were anonymized and reviewed by multiple roles. Here are the results:

{review_results}

Please synthesize these reviews into a coherent summary that:
1. Identifies which responses were most highly rated and why
2. Highlights key points of agreement/disagreement among reviewers
3. Provides actionable insights for improving the overall response quality

Keep your synthesis concise but informative."""

    def __init__(
        self,
        council: Council,
        anonymization_fn: Callable[[CouncilResult, int], AnonymousResponse] | None = None,
    ) -> None:
        """Initialize the peer review system.

        Args:
            council: The Council instance to use for deliberation
            anonymization_fn: Optional custom function to create anonymous responses.
                If not provided, uses default letter-based anonymization (A, B, C...)
        """
        self.council = council
        self.anonymization_fn = anonymization_fn or self._default_anonymize

    def _default_anonymize(self, result: CouncilResult, index: int) -> AnonymousResponse:
        """Default anonymization using letters (A, B, C...).

        Args:
            result: The council result to anonymize
            index: The index of this result (0-based)

        Returns:
            AnonymousResponse with letter-based ID
        """
        letter = chr(ord("A") + index)
        return AnonymousResponse(
            anonymous_id=f"Response {letter}",
            content=result.content,
            original_role=result.role_name,
        )

    async def deliberate_with_review(
        self,
        task: str,
        review_prompt_template: str | None = None,
        review_mode: str = "rank",
        include_failed: bool = False,
        synthesize_results: bool = False,
    ) -> PeerReviewResult:
        """Execute two-stage deliberation with peer review.

        Stage 1: Generate initial responses from all roles
        Stage 2: Conduct anonymized peer review of those responses

        Args:
            task: The task or question to deliberate on
            review_prompt_template: Custom prompt template for reviews.
                If None, uses RANKING_PROMPT or EVALUATION_PROMPT based on review_mode.
            review_mode: "rank" for ranking mode, "evaluate" for evaluation mode
            include_failed: Whether to include failed initial responses in review
            synthesize_results: Whether to generate a synthesis of review results

        Returns:
            PeerReviewResult containing initial output and review rounds
        """
        # Stage 1: Initial responses
        initial_output = await self.council.deliberate(task)

        # Create result container
        result = PeerReviewResult(
            task=task,
            initial_output=initial_output,
        )

        # Stage 2: Peer review
        review_round = await self._conduct_review_round(
            task=task,
            initial_output=initial_output,
            round_number=1,
            review_prompt_template=review_prompt_template,
            review_mode=review_mode,
            include_failed=include_failed,
        )
        result.review_rounds.append(review_round)

        # Optional: Synthesize results
        if synthesize_results:
            result.final_synthesis = await self._synthesize_reviews(result)

        return result

    async def _conduct_review_round(
        self,
        task: str,
        initial_output: CouncilOutput,
        round_number: int,
        review_prompt_template: str | None = None,
        review_mode: str = "rank",
        include_failed: bool = False,
    ) -> ReviewRound:
        """Conduct a single round of peer reviews.

        Args:
            task: The original task
            initial_output: Output from Stage 1
            round_number: Which round this is (1-indexed)
            review_prompt_template: Custom prompt template
            review_mode: "rank" or "evaluate"
            include_failed: Whether to include failed responses

        Returns:
            ReviewRound with all reviews collected
        """
        # Select prompt template
        if review_prompt_template is None:
            if review_mode == "evaluate":
                review_prompt_template = self.EVALUATION_PROMPT
            else:
                review_prompt_template = self.RANKING_PROMPT

        # Create anonymized responses
        results_to_review = (
            initial_output.results
            if include_failed
            else initial_output.get_successful()
        )

        anonymous_responses = [
            self.anonymization_fn(result, i)
            for i, result in enumerate(results_to_review)
        ]

        review_round = ReviewRound(
            round_number=round_number,
            anonymous_responses=anonymous_responses,
            prompt_template=review_prompt_template,
        )

        # Build responses section for prompt
        responses_section = "\n\n".join([
            f"--- {resp.anonymous_id} ---\n{resp.content}"
            for resp in anonymous_responses
        ])

        # Get reviewer roles (all roles participate in review)
        reviewer_roles = list(self.council.registry)

        # Conduct reviews in parallel
        review_tasks = [
            self._generate_review(
                role=role,
                task=task,
                responses_section=responses_section,
                review_prompt_template=review_prompt_template,
                anonymous_ids=[resp.anonymous_id for resp in anonymous_responses],
                review_mode=review_mode,
            )
            for role in reviewer_roles
        ]

        reviews = await asyncio.gather(*review_tasks, return_exceptions=True)

        for review in reviews:
            if isinstance(review, Exception):
                # Handle exception case
                review_round.reviews.append(RoleReview(
                    reviewer_role="unknown",
                    error=str(review),
                ))
            else:
                review_round.reviews.append(review)

        return review_round

    async def _generate_review(
        self,
        role: Role,
        task: str,
        responses_section: str,
        review_prompt_template: str,
        anonymous_ids: list[str],
        review_mode: str,
    ) -> RoleReview:
        """Generate a review from a single role.

        Args:
            role: The reviewing role
            task: The original task
            responses_section: Formatted responses section
            review_prompt_template: The prompt template to use
            anonymous_ids: List of anonymous response IDs
            review_mode: "rank" or "evaluate"

        Returns:
            RoleReview with rankings or evaluations
        """
        # Build the review prompt
        prompt = review_prompt_template.format(
            task=task,
            responses=responses_section,
        )

        # Generate review
        if self.council.provider is None:
            # Placeholder mode
            if review_mode == "rank":
                # Random-ish but deterministic ranking
                import random
                rng = random.Random(hash(role.name) % 10000)
                shuffled = anonymous_ids.copy()
                rng.shuffle(shuffled)
                return RoleReview(
                    reviewer_role=role.name,
                    rankings=shuffled,
                    reasoning=f"[Placeholder] {role.name} would provide reasoning here.",
                )
            else:
                return RoleReview(
                    reviewer_role=role.name,
                    evaluations={
                        aid: f"[Placeholder] Score: {((hash(role.name) + hash(aid)) % 5) + 6}/10"
                        for aid in anonymous_ids
                    },
                    reasoning=f"[Placeholder] {role.name} would provide reasoning here.",
                )

        try:
            result = await self.council.provider.generate(
                prompt=prompt,
                system_prompt=role.prompt,
                model=role.model,
                temperature=role.config.temperature,
                max_tokens=role.config.max_tokens,
            )

            if result.error:
                return RoleReview(
                    reviewer_role=role.name,
                    error=result.error,
                )

            # Parse the review response
            return self._parse_review_response(
                role_name=role.name,
                content=result.content,
                anonymous_ids=anonymous_ids,
                review_mode=review_mode,
            )

        except Exception as e:
            return RoleReview(
                reviewer_role=role.name,
                error=str(e),
            )

    def _parse_review_response(
        self,
        role_name: str,
        content: str,
        anonymous_ids: list[str],
        review_mode: str,
    ) -> RoleReview:
        """Parse a review response into structured data.

        Uses parse_ranking_from_text from anonymization.core for consistent
        ranking parsing across the codebase.

        Args:
            role_name: Name of the reviewing role
            content: The raw response content
            anonymous_ids: List of valid anonymous IDs
            review_mode: "rank" or "evaluate"

        Returns:
            RoleReview with parsed data
        """
        if review_mode == "rank":
            # Use consolidated ranking parser from anonymization module
            rankings = parse_ranking_from_text(
                content,
                valid_ids=anonymous_ids,
                ensure_all_ids=True,
            )

            return RoleReview(
                reviewer_role=role_name,
                rankings=rankings,
                reasoning=content,
            )

        else:  # evaluate mode
            evaluations = {}

            # Try to extract evaluations for each response
            for aid in anonymous_ids:
                aid_lower = aid.lower().replace(" ", "")

                # Look for section starting with this response ID
                pattern = rf"(?:^|\n)\s*{re.escape(aid)}\s*:?\s*(.+?)(?=\n\s*(?:[Rr]esponse|$))"
                match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

                if match:
                    evaluations[aid] = match.group(1).strip()
                else:
                    # Fallback: look for any mention
                    if aid_lower in content_lower:
                        evaluations[aid] = "[Evaluation found but not clearly structured]"

            return RoleReview(
                reviewer_role=role_name,
                evaluations=evaluations,
                reasoning=content,
            )

    async def _synthesize_reviews(self, result: PeerReviewResult) -> str:
        """Generate a synthesis of review results.

        Args:
            result: The peer review result to synthesize

        Returns:
            Synthesis string
        """
        if not result.review_rounds:
            return "No reviews to synthesize."

        round_one = result.review_rounds[0]

        # Build review results section
        lines = []

        # Add aggregate rankings
        rankings = result.get_aggregate_rankings()
        if rankings:
            lines.append("Aggregate Rankings (by average rank, lower is better):")
            for aid, avg_rank in rankings.items():
                resp = round_one.get_response_by_id(aid)
                if resp:
                    lines.append(f"  {aid} (from {resp.original_role}): {avg_rank:.2f}")
            lines.append("")

        # Add individual reviews
        lines.append("Individual Reviews:")
        for review in round_one.reviews:
            lines.append(f"\n{review.reviewer_role}:")
            if review.rankings:
                lines.append(f"  Rankings: {' > '.join(review.rankings)}")
            if review.evaluations:
                for aid, eval_text in review.evaluations.items():
                    lines.append(f"  {aid}: {eval_text[:100]}...")

        review_results = "\n".join(lines)

        # Build synthesis prompt
        prompt = self.SYNTHESIS_PROMPT.format(
            task=result.task,
            review_results=review_results,
        )

        if self.council.provider is None:
            return f"[Placeholder Synthesis]\n\n{review_results}"

        try:
            # Use a generic synthesis role or the first available role
            roles = list(self.council.registry)
            if not roles:
                return "No roles available for synthesis."

            synthesizer_role = roles[0]

            result_data = await self.council.provider.generate(
                prompt=prompt,
                system_prompt="You are a neutral synthesizer who summarizes peer review results objectively.",
                model=synthesizer_role.model,
                temperature=0.5,
            )

            if result_data.error:
                return f"Synthesis error: {result_data.error}\n\nRaw results:\n{review_results}"

            return result_data.content

        except Exception as e:
            return f"Synthesis failed: {e}\n\nRaw results:\n{review_results}"

    async def multi_round_review(
        self,
        task: str,
        num_rounds: int = 2,
        review_prompt_template: str | None = None,
        review_mode: str = "rank",
        synthesize_results: bool = False,
    ) -> PeerReviewResult:
        """Conduct multiple rounds of peer review.

        Each round reviews the anonymized responses from the initial deliberation.
        This can help identify consensus or divergence in rankings.

        Args:
            task: The task or question
            num_rounds: Number of review rounds to conduct
            review_prompt_template: Custom prompt template
            review_mode: "rank" or "evaluate"
            synthesize_results: Whether to synthesize final results

        Returns:
            PeerReviewResult with multiple review rounds
        """
        # Stage 1: Initial responses (once)
        initial_output = await self.council.deliberate(task)

        result = PeerReviewResult(
            task=task,
            initial_output=initial_output,
        )

        # Conduct multiple review rounds
        for round_num in range(1, num_rounds + 1):
            review_round = await self._conduct_review_round(
                task=task,
                initial_output=initial_output,
                round_number=round_num,
                review_prompt_template=review_prompt_template,
                review_mode=review_mode,
                include_failed=False,
            )
            result.review_rounds.append(review_round)

        if synthesize_results:
            result.final_synthesis = await self._synthesize_reviews(result)

        return result

    def compile_review_report(
        self,
        result: PeerReviewResult,
        reveal_identities: bool = True,
    ) -> str:
        """Compile a human-readable review report.

        Args:
            result: The peer review result to compile
            reveal_identities: Whether to reveal which role wrote each response

        Returns:
            Formatted report string
        """
        lines = [
            "=" * 60,
            "PEER REVIEW REPORT",
            "=" * 60,
            f"\nTask: {result.task}",
            f"Initial Responses: {len(result.initial_output.results)}",
            f"Review Rounds: {len(result.review_rounds)}",
        ]

        if result.review_rounds:
            round_one = result.review_rounds[0]

            # Aggregate Rankings
            rankings = result.get_aggregate_rankings()
            if rankings:
                lines.append("\n" + "-" * 40)
                lines.append("AGGREGATE RANKINGS")
                lines.append("-" * 40)

                for i, (aid, avg_rank) in enumerate(rankings.items(), 1):
                    resp = round_one.get_response_by_id(aid)
                    if resp:
                        if reveal_identities:
                            lines.append(f"{i}. {aid} (by {resp.original_role}): {avg_rank:.2f}")
                        else:
                            lines.append(f"{i}. {aid}: {avg_rank:.2f}")

            # Individual Reviews
            lines.append("\n" + "-" * 40)
            lines.append("INDIVIDUAL REVIEWS")
            lines.append("-" * 40)

            for review in round_one.reviews:
                lines.append(f"\nReviewer: {review.reviewer_role}")

                if review.error:
                    lines.append(f"  Error: {review.error}")
                    continue

                if review.rankings:
                    lines.append(f"  Rankings: {' > '.join(review.rankings)}")

                if review.evaluations:
                    lines.append("  Evaluations:")
                    for aid, eval_text in review.evaluations.items():
                        lines.append(f"    {aid}: {eval_text[:150]}...")

                if review.reasoning:
                    # Truncate long reasoning
                    reasoning = review.reasoning[:300]
                    if len(review.reasoning) > 300:
                        reasoning += "..."
                    lines.append(f"  Reasoning: {reasoning}")

        # Final Synthesis
        if result.final_synthesis:
            lines.append("\n" + "-" * 40)
            lines.append("SYNTHESIS")
            lines.append("-" * 40)
            lines.append(result.final_synthesis)

        lines.append("\n" + "=" * 60)

        return "\n".join(lines)
