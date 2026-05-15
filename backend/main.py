"""FastAPI application for LLM Council backend.

Provides REST API and WebSocket endpoints for running LLM deliberations.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

# Add the src directory to Python path for importing llm_council
SRC_DIR = Path(__file__).parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Add backend directory to path for api imports
BACKEND_DIR = Path(__file__).parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from api import api_router

# Create FastAPI application
app = FastAPI(
    title="LLM Council API",
    description="Local API for LLM Council.",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint returning API info."""
    return {
        "name": "LLM Council API",
        "version": "0.1.0",
        "health": "/health",
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api")
async def api_root() -> dict[str, str]:
    """API root endpoint."""
    return {
        "message": "LLM Council API",
        "version": "0.1.0",
        "endpoints": {
            "roles": "/api/council/roles",
            "templates": "/api/council/templates",
            "run": "POST /api/council/run",
            "stream": "WS /api/council/stream",
            "conversations": "/api/conversations",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
