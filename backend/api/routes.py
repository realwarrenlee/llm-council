"""HTTP API routes for LLM Council.

Provides REST endpoints for:
- Listing and retrieving roles (Now purely model-based, returns empty/default)
- Listing and retrieving templates (Returns empty)
- Running deliberations (sync)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status

# Add the src directory to Python path for importing llm_council
SRC_DIR = Path(__file__).parent.parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Removed: from llm_council.roles.presets import PRESET_ROLES
from llm_council.roles.registry import RoleRegistry
from llm_council.council import Council
from llm_council.config import CouncilConfig
# Removed: from llm_council.templates.loader import TemplateLoader, TemplateRegistry

import schemas

router = APIRouter()

# =============================================================================
# Role Endpoints
# =============================================================================

@router.get("/roles", response_model=list[schemas.Role])
async def list_roles() -> list[schemas.Role]:
    """List available roles.
    
    In Model-Based mode, this returns a default 'General' role to ensure
    frontend compatibility, as presets have been removed.
    """
    # Return a single default role so frontend doesn't show empty state
    return [
        schemas.Role(
            name="General Assistant",
            prompt="You are a helpful AI assistant.",
            model="anthropic/claude-sonnet-4",
            description="Standard LLM assistant",
            config=schemas.RoleConfig(),
            weight=1.0,
            depends_on=[]
        )
    ]


@router.get("/roles/{name}", response_model=schemas.Role)
async def get_role(name: str) -> schemas.Role:
    """Get a specific role by name."""
    # Mock response for frontend compatibility
    return schemas.Role(
        name=name,
        prompt="You are a helpful AI assistant.",
        model="anthropic/claude-sonnet-4",
        description="Standard LLM assistant",
        config=schemas.RoleConfig(),
        weight=1.0,
        depends_on=[],
    )


# =============================================================================
# Template Endpoints
# =============================================================================

@router.get("/templates", response_model=list[schemas.Template])
async def list_templates() -> list[schemas.Template]:
    """List all available templates.
    
    Returns valid but empty list as templates are deprecated.
    """
    return []


@router.get("/templates/{name}", response_model=schemas.Template)
async def get_template(name: str) -> schemas.Template:
    """Get a specific template by name."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Templates are no longer supported.",
    )


# =============================================================================
# Deliberation Endpoints
# =============================================================================

def _convert_role_to_domain(role_schema: schemas.Role) -> Any:
    """Convert a Pydantic Role schema to a domain Role object."""
    from llm_council.roles.role import Role, RoleConfig
    
    # If prompt is missing, use empty string (model-based approach)
    prompt = role_schema.prompt if role_schema.prompt else ""
    
    return Role(
        name=role_schema.name,
        prompt=prompt,
        model=role_schema.model,
        description=role_schema.description or "",
        config=RoleConfig(
            temperature=role_schema.config.temperature,
            max_tokens=role_schema.config.max_tokens,
            top_p=role_schema.config.top_p,
            presence_penalty=role_schema.config.presence_penalty,
            frequency_penalty=role_schema.config.frequency_penalty,
            extra=role_schema.config.extra,
        ),
        weight=role_schema.weight,
        depends_on=role_schema.depends_on,
    )


def _convert_result_to_schema(result: Any) -> schemas.CouncilResult:
    """Convert a domain CouncilResult to a Pydantic schema."""
    if isinstance(result, dict):
        return schemas.CouncilResult(
            role_name=result.get("role_name", ""),
            content=result.get("content", ""),
            model=result.get("model", ""),
            tokens_used=result.get("tokens_used"),
            latency_ms=result.get("latency_ms"),
            error=result.get("error"),
            success=result.get("success", True),
        )
    return schemas.CouncilResult(
        role_name=result.role_name,
        content=result.content,
        model=result.model,
        tokens_used=result.tokens_used,
        latency_ms=result.latency_ms,
        error=result.error,
        success=result.success,
    )


class OpenRouterResult:
    """Result object for OpenRouter provider."""
    def __init__(self, content: str, model: str, tokens_used: int = None, latency_ms: float = None, error: str = None):
        self.content = content
        self.model = model
        self.tokens_used = tokens_used
        self.latency_ms = latency_ms
        self.error = error
        self.success = error is None


class OpenRouterProvider:
    """Simple OpenRouter provider for making LLM calls."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"

    async def generate(self, prompt: str, model: str, **kwargs):
        """Generate a response from the LLM."""
        import aiohttp
        import time

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "LLM Council",
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 32000),
        }

        print(f"DEBUG: Calling OpenRouter with model={model}, prompt_length={len(prompt)}")

        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    latency_ms = (time.time() - start_time) * 1000

                    if response.status != 200:
                        error_text = await response.text()
                        print(f"DEBUG: OpenRouter error - status={response.status}, error={error_text}")
                        return OpenRouterResult(
                            content="",
                            model=model,
                            latency_ms=latency_ms,
                            error=f"OpenRouter error: {error_text}",
                        )

                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
                    print(f"DEBUG: OpenRouter success - model={model}, content_length={len(content)}")
                    return OpenRouterResult(
                        content=content,
                        model=data.get("model", model),
                        tokens_used=data.get("usage", {}).get("total_tokens"),
                        latency_ms=latency_ms,
                    )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            print(f"DEBUG: OpenRouter exception - model={model}, error={str(e)}")
            return OpenRouterResult(
                content="",
                model=model,
                latency_ms=latency_ms,
                error=str(e),
            )


@router.post("/run", response_model=schemas.CouncilOutput)
async def run_deliberation(
    request: schemas.DeliberationRequest,
    api_key: str = "",
) -> schemas.CouncilOutput:
    """Start a council deliberation (synchronous)."""
    # Debug logging
    print(f"DEBUG: Received {len(request.roles)} roles")
    
    if not request.task or not request.task.strip():
        raise HTTPException(status_code=400, detail="Task cannot be empty")

    if not request.roles:
        raise HTTPException(status_code=400, detail="At least one role is required")

    try:
        # Build role registry from request
        registry = RoleRegistry()
        for role_schema in request.roles:
            role = _convert_role_to_domain(role_schema)
            registry.add(role)

        # Build Config from request
        config = CouncilConfig(
            output_mode=request.options.output_mode if request.options and request.options.output_mode else "perspectives",
            aggregation_method=request.options.aggregation if request.options and request.options.aggregation else "borda",
            enable_peer_review=request.options.review if request.options and request.options.review is not None else True,
            anonymize=request.options.anonymize if request.options and request.options.anonymize is not None else False,
            chairman_model=request.options.chairman_model if request.options and request.options.chairman_model else None,
        )

        # Create provider
        provider = None
        if api_key:
            provider = OpenRouterProvider(api_key)

        # Create council with new config API
        council = Council(
            registry,
            provider=provider,
            config=config
        )

        # Run deliberation
        output = await council.deliberate(request.task)

        # Convert to schema
        return schemas.CouncilOutput(
            task=output.task,
            results=[_convert_result_to_schema(r) for r in output.results],
            output_mode=output.output_mode,
            synthesis=output.synthesis,
            metadata=output.metadata,
            confidence_scores=output.confidence_scores,
            aggregate_rankings=output.aggregate_rankings,
            aggregation_scores=output.aggregation_scores if hasattr(output, 'aggregation_scores') else {},
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"ERROR: Deliberation failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Deliberation failed: {str(e)}")
