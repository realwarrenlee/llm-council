"""Refactored peer review orchestration - extracted from Council."""

from __future__ import annotations

import itertools
import re
from typing import TYPE_CHECKING, Any

from llm_council.exceptions import PeerReviewError
from llm_council.logging import get_logger, log_exception
from llm_council import prompts

if TYPE_CHECKING:
    from llm_council.council import Council, CouncilResult
    from llm_council.roles import Role

logger = get_logger(__name__)


class PeerReviewOrchestrator:
    """Orchestrates peer review process for Council deliberations.

    This class extracts the peer review logic from the Council class,
    providing a cleaner separation of concerns.
    """

    def __init__(self, council: Council) -> None:
        """Initialize the peer review orchestrator.

        Args:
            council: The Council instance to use for peer review
        """
        self.council = council

    async def conduct_peer_review(
        self,
        task: str,
        results: list[CouncilResult],
    ) -> tuple[list[tuple[str, str, str, str]], dict[str, list[str]]]:
        """Conduct peer review using explicit pairwise comparisons.

        Args:
            task: The original task
            results: List of successful results to review

        Returns:
            Tuple of:
            - List of tuples: (judge_model, model_a, model_b, verdict)
            - Dict of peer review texts: judge_model -> list of full review texts
        """
        try:
            from llm_council.anonymization import anonymize_responses

            # Build model map
            model_map = {r.model: r for r in results}
            models = list(model_map.keys())

            logger.debug(f"Starting peer review for {len(models)} models")

            # Anonymize responses if enabled
            if self.council.config.anonymize:
                anonymized_results = anonymize_responses(results)
                anonymous_map = {ar.model: ar.anonymous_id for ar in anonymized_results}
                response_map = {ar.anonymous_id: ar.content for ar in anonymized_results}
                logger.debug("Responses anonymized")
            else:
                anonymous_map = {r.model: r.model for r in results}
                response_map = {r.model: r.content for r in results}

            # Generate all pairwise comparisons
            pairwise_comparisons = []
            peer_review_texts = {}

            # For each judge model
            for judge_role in self.council.registry:
                judge_model = judge_role.model
                peer_review_texts[judge_model] = []

                # Compare all pairs of responses
                for model_a, model_b in itertools.combinations(models, 2):
                    anon_a = anonymous_map[model_a]
                    anon_b = anonymous_map[model_b]

                    # Create pairwise comparison prompt
                    prompt = prompts.PAIRWISE_COMPARISON_PROMPT.format(
                        task=task,
                        id_a=anon_a,
                        id_b=anon_b,
                        content_a=response_map[anon_a],
                        content_b=response_map[anon_b],
                    )

                    # Get judgment from this judge
                    judgment_text = await self._get_ranking_from_role(judge_role, prompt)

                    if judgment_text:
                        # Store the full review text
                        peer_review_texts[judge_model].append(
                            f"Comparing {anon_a} vs {anon_b}:\n{judgment_text}"
                        )

                        # Parse the verdict
                        verdict = self._parse_pairwise_verdict(judgment_text, anon_a, anon_b)

                        if verdict:
                            # De-anonymize and store
                            if self.council.config.anonymize:
                                verdict_deAnon = verdict.replace(anon_a, "A").replace(anon_b, "B")
                            else:
                                verdict_deAnon = verdict.replace(model_a, "A").replace(model_b, "B")

                            pairwise_comparisons.append((
                                judge_model,
                                model_a,
                                model_b,
                                verdict_deAnon
                            ))

            logger.info(f"Peer review complete: {len(pairwise_comparisons)} comparisons collected")
            return pairwise_comparisons, peer_review_texts

        except Exception as e:
            log_exception(logger, e, "Peer review process failed")
            raise PeerReviewError(f"Peer review failed: {e}") from e

    def compute_scores_from_pairwise(
        self, pairwise_comparisons: list[tuple[str, str, str, str]]
    ) -> dict[str, dict]:
        """Compute all three aggregation methods from explicit pairwise comparisons."""
        from llm_council.analysis.bradley_terry import PairwiseResult, BradleyTerryAnalyzer
        from llm_council.analysis.elo import bootstrap_elo

        result = {}

        # Convert pairwise comparisons to PairwiseResult format
        pairwise_results = []
        for judge_model, model_a, model_b, verdict in pairwise_comparisons:
            # Map verdict to winner and margin
            if verdict == "A>>B":
                winner, margin = "a", "major"
            elif verdict == "A>B":
                winner, margin = "a", "minor"
            elif verdict == "A=B":
                winner, margin = "tie", "tie"
            elif verdict == "B>A":
                winner, margin = "b", "minor"
            elif verdict == "B>>A":
                winner, margin = "b", "major"
            else:
                continue

            pairwise_results.append(
                PairwiseResult(
                    item_a=model_a,
                    item_b=model_b,
                    winner=winner,
                    margin=margin,
                    metadata={"judge": judge_model, "verdict": verdict},
                )
            )

        # 1. Borda Count
        try:
            borda_scores = self._borda_from_pairwise(pairwise_results)
            result["borda"] = {"scores": borda_scores, "confidence_intervals": None}
        except Exception as e:
            logger.error(f"Borda aggregation failed: {e}")
            result["borda"] = {"scores": {}, "confidence_intervals": None}

        # 2. Bradley-Terry
        try:
            if pairwise_results:
                analyzer = BradleyTerryAnalyzer(pairwise_results)
                bt_scores = analyzer.fit()
                result["bradley_terry"] = {"scores": bt_scores, "confidence_intervals": None}
            else:
                result["bradley_terry"] = {"scores": {}, "confidence_intervals": None}
        except Exception as e:
            logger.error(f"Bradley-Terry aggregation failed: {e}")
            result["bradley_terry"] = {"scores": {}, "confidence_intervals": None}

        # 3. ELO
        try:
            if pairwise_results and len(pairwise_results) >= 2:
                elo_with_ci = bootstrap_elo(pairwise_results, num_rounds=1000)
                if elo_with_ci:
                    elo_scores = {k: v[0] for k, v in elo_with_ci.items()}
                    elo_ci = {k: (v[1], v[2]) for k, v in elo_with_ci.items()}
                    result["elo"] = {"scores": elo_scores, "confidence_intervals": elo_ci}
                else:
                    result["elo"] = {"scores": {}, "confidence_intervals": None}
            else:
                result["elo"] = {"scores": {}, "confidence_intervals": None}
        except Exception as e:
            logger.error(f"ELO aggregation failed: {e}")
            result["elo"] = {"scores": {}, "confidence_intervals": None}

        return result

    def _borda_from_pairwise(self, pairwise_results: list[Any]) -> dict[str, float]:
        """Compute Borda counts from pairwise results."""
        scores = {}
        # weights matching original config
        weights = {"major": 3.0, "minor": 1.0, "tie": 0.5}

        for res in pairwise_results:
            scores.setdefault(res.item_a, 0.0)
            scores.setdefault(res.item_b, 0.0)

            if res.winner == "a":
                scores[res.item_a] += weights.get(res.margin, 1.0)
            elif res.winner == "b":
                scores[res.item_b] += weights.get(res.margin, 1.0)
            elif res.winner == "tie":
                scores[res.item_a] += weights["tie"]
                scores[res.item_b] += weights["tie"]

        return scores

    async def _get_ranking_from_role(self, role: Role, review_prompt: str) -> str:
        """Get a ranking from a specific role."""
        if self.council.provider is None:
            return ""

        try:
            result = await self.council.provider.generate(
                prompt=review_prompt,
                model=role.model,
                temperature=0.3,
                max_tokens=500,
            )
            return result.content if result.content else ""
        except Exception as e:
            log_exception(logger, e, f"Failed to get ranking from {role.name}")
            return ""

    def _parse_pairwise_verdict(self, text: str, id_a: str, id_b: str) -> str | None:
        """Parse pairwise verdict from LLM response."""
        # Look for patterns like [[A>>B]], [[A>B]], [[A=B]], [[B>A]], [[B>>A]]
        patterns = [
            f"\\[\\[{re.escape(id_a)}>>{re.escape(id_b)}\\]\\]",
            f"\\[\\[{re.escape(id_a)}>{re.escape(id_b)}\\]\\]",
            f"\\[\\[{re.escape(id_a)}={re.escape(id_b)}\\]\\]",
            f"\\[\\[{re.escape(id_b)}>{re.escape(id_a)}\\]\\]",
            f"\\[\\[{re.escape(id_b)}>>{re.escape(id_a)}\\]\\]",
        ]
        verdicts = ["A>>B", "A>B", "A=B", "B>A", "B>>A"]
        
        for pattern, verdict in zip(patterns, verdicts):
            if re.search(pattern, text):
                return verdict

        # Fallback: look for the verdict patterns without IDs
        simple_patterns = [
            r"\[\[A>>B\]\]", r"\[\[A>B\]\]", r"\[\[A=B\]\]", r"\[\[B>A\]\]", r"\[\[B>>A\]\]"
        ]
        for pattern, verdict in zip(simple_patterns, verdicts):
            if re.search(pattern, text):
                return verdict

        return None
