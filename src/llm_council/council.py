"""Core Council orchestration engine - Model-Based and Streamlined."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from llm_council.config import CouncilConfig
from llm_council.exceptions import CouncilError
from llm_council.logging import get_logger, log_exception
from . import prompts
from enum import Enum

if TYPE_CHECKING:
    from llm_council.providers import Provider
    from llm_council.roles import RoleRegistry
    from llm_council.peer_review_orchestrator import PeerReviewOrchestrator

logger = get_logger(__name__)


class OutputMode(Enum):
    """Output mode for council deliberation results."""

    SYNTHESIS = "synthesis"
    PERSPECTIVES = "perspectives"
    BOTH = "both"

    @classmethod
    def from_string(cls, value: str) -> OutputMode:
        """Parse output mode from string."""
        value = value.lower().strip()
        try:
            return cls(value)
        except ValueError:
            valid = [m.value for m in cls]
            raise ValueError(f"Invalid output mode '{value}'. Valid modes: {valid}")


@dataclass
class CouncilResult:
    """Result from a single role's execution."""
    role_name: str
    content: str
    model: str
    tokens_used: int | None = None
    latency_ms: float | None = None
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


@dataclass
class CouncilOutput:
    """Complete output from a council deliberation."""
    task: str
    results: list[CouncilResult] = field(default_factory=list)
    output_mode: str = "perspectives"
    synthesis: str | None = None
    metadata: dict = field(default_factory=dict)
    confidence_scores: dict[str, float] = field(default_factory=dict)
    aggregate_rankings: dict[str, float] = field(default_factory=dict)
    aggregation_scores: dict[str, dict] = field(default_factory=dict)
    peer_review_texts: dict[str, list[str]] = field(default_factory=dict)


class Council:
    """Orchestrates multi-model LLM deliberation (Parallel Execution)."""

    def __init__(
        self,
        registry: RoleRegistry,
        provider: Provider | None = None,
        config: CouncilConfig | None = None,
        # Legacy args for backward compatibility (mapped to config)
        output_mode: str | None = None,
        aggregation_method: str | None = None,
        enable_peer_review: bool | None = None,
        anonymize: bool | None = None,
        chairman_model: str | None = None,
    ) -> None:
        self.registry = registry
        self.provider = provider
        
        # Initialize config
        if config is None:
            self.config = CouncilConfig()
        else:
            self.config = config

        # Override config with legacy args if provided
        if output_mode is not None:
            self.config.output_mode = output_mode
        if aggregation_method is not None:
            self.config.aggregation_method = aggregation_method
        if enable_peer_review is not None:
            self.config.enable_peer_review = enable_peer_review
        if anonymize is not None:
            self.config.anonymize = anonymize
        if chairman_model is not None:
            self.config.chairman_model = chairman_model
            
        # Initialize Peer Review Orchestrator
        from llm_council.peer_review_orchestrator import PeerReviewOrchestrator
        self.peer_review_orchestrator = PeerReviewOrchestrator(self)

    async def deliberate(self, task: str) -> CouncilOutput:
        """Execute deliberation."""
        logger.info(f"Starting deliberation on: {task}")
        
        output = CouncilOutput(
            task=task,
            output_mode=self.config.output_mode,
        )

        try:
            # 1. Execute all roles in parallel
            logger.debug(f"Executing {len(self.registry)} roles in parallel")
            tasks = [self._execute_role(role, task) for role in self.registry]
            if not tasks:
                 logger.warning("No roles in registry!")
            
            results = await asyncio.gather(*tasks)
            output.results.extend(results)

            # 2. Peer Review (if enabled)
            successful_results = [r for r in output.results if r.success]
            if self.config.enable_peer_review and len(successful_results) > 1:
                logger.info("Starting Peer Review phase")
                pairwise_comparisons, peer_review_texts = \
                    await self.peer_review_orchestrator.conduct_peer_review(task, successful_results)
                
                output.peer_review_texts = peer_review_texts
                
                if pairwise_comparisons:
                     output.aggregation_scores = \
                        self.peer_review_orchestrator.compute_scores_from_pairwise(pairwise_comparisons)
                     
                     # Set primary rankings
                     primary = self.config.aggregation_method
                     if primary in output.aggregation_scores:
                         output.aggregate_rankings = output.aggregation_scores[primary]["scores"]

            # 3. Synthesis (if enabled)
            if self.config.output_mode in ("synthesis", "both"):
                logger.info("Starting Synthesis phase")
                output.synthesis = await self._synthesize(output)

            return output

        except Exception as e:
            log_exception(logger, e, "Deliberation failed")
            raise CouncilError(f"Deliberation failed: {e}") from e

    async def _execute_role(self, role, task: str) -> CouncilResult:
        """Execute a single role."""
        if self.provider is None:
            # Placeholder mode
            return CouncilResult(
                role_name=role.name,
                content=f"[Placeholder] {role.name} response to: {task}",
                model=role.model,
                tokens_used=0,
                latency_ms=0
            )

        try:
            # Construct prompt with instruction to be concise
            system_prompt = role.prompt
            full_prompt = f"{system_prompt}\n\nTask: {task}\n\nBe parsimonious in your response. Focus on key points without unnecessary elaboration."
            
            result = await self.provider.generate(
                prompt=full_prompt,
                model=role.model,
                temperature=role.config.temperature,
                max_tokens=role.config.max_tokens
            )
            
            return CouncilResult(
                role_name=role.name,
                content=result.content,
                model=role.model,
                tokens_used=getattr(result, "tokens_used", 0),
                latency_ms=getattr(result, "latency_ms", 0)
            )
        except Exception as e:
            logger.error(f"Role {role.name} failed: {e}")
            return CouncilResult(
                role_name=role.name,
                content="",
                model=role.model,
                error=str(e)
            )

    async def _synthesize(self, output: CouncilOutput) -> str:
        """Synthesize results using Chairman model."""
        if self.provider is None:
            return "[Placeholder] Synthesis of results..."

        # Format inputs
        inputs = []
        for r in output.results:
             if r.success:
                 inputs.append(f"--- Perspective: {r.role_name} ({r.model}) ---\n{r.content}")
        
        reviews = []
        for judge, texts in output.peer_review_texts.items():
            for text in texts:
                reviews.append(f"Review by {judge}: {text}")

        prompt = prompts.CHAIRMAN_SYNTHESIS_PROMPT.format(
            task=output.task,
            stage1_responses="\n\n".join(inputs),
            stage2_reviews="\n\n".join(reviews) if reviews else "No peer reviews available."
        )
        
        model = self.config.chairman_model or "gpt-4" # Default fallback
        
        try:
            result = await self.provider.generate(
                prompt=prompt,
                model=model,
                temperature=0.7,
                max_tokens=4000
            )
            return result.content
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return f"Synthesis failed: {e}"
