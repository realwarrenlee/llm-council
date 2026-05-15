"""WebSocket endpoint for streaming LLM Council deliberations.

Provides real-time streaming of deliberation results via WebSocket.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse

# Add the src directory to Python path for importing llm_council
SRC_DIR = Path(__file__).parent.parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from llm_council.roles.registry import RoleRegistry
from llm_council.roles.role import Role, RoleConfig
from llm_council.council import Council, CouncilResult, CouncilOutput

import schemas

router = APIRouter()


class StreamingCouncil(Council):
    """Extended Council that supports streaming results."""

    def __init__(self, *args, websocket: WebSocket | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.websocket = websocket

    async def _send_message(self, message: dict[str, Any]) -> None:
        """Send a message via WebSocket if available."""
        if self.websocket:
            # Add timestamp
            message["timestamp"] = datetime.now(timezone.utc).isoformat()
            await self.websocket.send_json(message)

    async def _execute_role(
        self,
        role: Any,
        task: str,
        output: CouncilOutput,
    ) -> CouncilResult:
        """Execute a single role with streaming support."""
        # Send role_start message
        await self._send_message({
            "type": "role_start",
            "role_name": role.name,
        })

        if self.provider is None:
            # Placeholder mode - simulate streaming
            content = f"[Placeholder] {role.name} would respond to: {task[:50]}..."

            # Simulate chunks for streaming effect
            chunks = [
                f"As {role.name}, I approach this task with my unique perspective. ",
                f"The key considerations for '{task[:30]}...' include: ",
                f"1) Understanding the context, 2) Applying expertise, 3) Providing actionable insights. ",
                f"In my professional opinion, this requires careful analysis and thoughtful implementation.",
            ]

            full_content = ""
            for chunk in chunks:
                await asyncio.sleep(0.1)  # Simulate network delay
                full_content += chunk
                await self._send_message({
                    "type": "role_chunk",
                    "role_name": role.name,
                    "content": chunk,
                })

            result = CouncilResult(
                role_name=role.name,
                content=full_content,
                model=role.model,
            )
        else:
            # Real provider execution with streaming
            prompt = task
            if role.depends_on:
                dep_parts = ["Input from other roles:"]
                for dep_name in role.depends_on:
                    dep_result = output.get_by_role(dep_name)
                    if dep_result:
                        dep_parts.append(f"\n--- {dep_name} ---\n{dep_result.content}")
                prompt = "\n\n".join(dep_parts) + f"\n\nNow respond to: {task}"

            # For non-streaming providers, we simulate chunks
            provider_result = await self.provider.generate(
                prompt=prompt,
                system_prompt=role.prompt,
                model=role.model,
                temperature=role.config.temperature,
                max_tokens=role.config.max_tokens,
            )

            # Simulate streaming by sending the full content as one chunk
            # In a real implementation, the provider would support streaming
            await self._send_message({
                "type": "role_chunk",
                "role_name": role.name,
                "content": provider_result.content,
            })

            result = CouncilResult(
                role_name=role.name,
                content=provider_result.content,
                model=provider_result.model,
                tokens_used=provider_result.tokens_used,
                latency_ms=provider_result.latency_ms,
                error=provider_result.error,
            )

        # Send role_complete message
        await self._send_message({
            "type": "role_complete",
            "role_name": role.name,
            "result": {
                "role_name": result.role_name,
                "content": result.content,
                "model": result.model,
                "tokens_used": result.tokens_used,
                "latency_ms": result.latency_ms,
                "error": result.error,
                "success": result.success,
            },
        })

        return result

    async def _synthesize(
        self,
        output: CouncilOutput,
        include_weights: bool = True,
        include_confidence: bool = True,
    ) -> str:
        """Synthesize results with streaming support."""
        # Send synthesis_start message
        await self._send_message({
            "type": "synthesis_start",
        })

        # Get synthesis from parent class
        synthesis = await super()._synthesize(output, include_weights, include_confidence)

        # Stream synthesis in chunks
        chunk_size = 100
        for i in range(0, len(synthesis), chunk_size):
            chunk = synthesis[i:i + chunk_size]
            await self._send_message({
                "type": "synthesis_chunk",
                "content": chunk,
            })
            await asyncio.sleep(0.05)  # Small delay for streaming effect

        # Send synthesis_complete message
        await self._send_message({
            "type": "synthesis_complete",
            "content": synthesis,
        })

        return synthesis


@router.websocket("/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming deliberation.

    Accepts a deliberation request and streams results in real-time.

    Message Types:
        - role_start: A role has started generating
        - role_chunk: A content chunk from a role
        - role_complete: A role has finished
        - role_error: An error occurred for a role
        - synthesis_start: Synthesis has started
        - synthesis_chunk: A chunk of synthesized content
        - synthesis_complete: Synthesis is complete
        - complete: All processing is complete
        - error: A general error occurred
    """
    await websocket.accept()

    try:
        # Receive the deliberation request
        data = await websocket.receive_json()

        # Parse and validate request
        try:
            request = schemas.DeliberationRequest(**data)
        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "error": f"Invalid request format: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            await websocket.close(code=4001)
            return

        # Validate request
        if not request.task or not request.task.strip():
            await websocket.send_json({
                "type": "error",
                "error": "Task cannot be empty",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            await websocket.close(code=4002)
            return

        if not request.roles:
            await websocket.send_json({
                "type": "error",
                "error": "At least one role is required",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            await websocket.close(code=4003)
            return

        for role in request.roles:
            if not role.name or not role.name.strip():
                await websocket.send_json({
                    "type": "error",
                    "error": "Role name cannot be empty",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                await websocket.close(code=4004)
                return
            # Prompt is now optional for model-based approach

        # Build role registry from request
        registry = RoleRegistry()
        for role_schema in request.roles:
            role = Role(
                name=role_schema.name,
                prompt=role_schema.prompt,
                model=role_schema.model,
                description=role_schema.description,
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
            registry.add(role)

        # Determine output mode
        output_mode = "perspectives"
        if request.options and request.options.output_mode:
            output_mode = request.options.output_mode

        # Create streaming council
        council = StreamingCouncil(registry, provider=None, output_mode=output_mode)
        council.websocket = websocket

        # Run deliberation
        output = await council.deliberate(request.task)

        # Send complete message
        await websocket.send_json({
            "type": "complete",
            "metadata": {
                "task": output.task,
                "output_mode": output.output_mode,
                "confidence_scores": output.confidence_scores,
                "results_count": len(output.results),
                "successful_count": len(output.get_successful()),
                "failed_count": len(output.get_failed()),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        await websocket.close(code=1000)

    except WebSocketDisconnect:
        # Client disconnected
        pass
    except Exception as e:
        # Send error message
        try:
            await websocket.send_json({
                "type": "error",
                "error": f"Deliberation failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            await websocket.close(code=4000)
        except Exception:
            # WebSocket might already be closed
            pass
