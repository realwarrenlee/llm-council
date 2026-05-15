"""LLM Council API routes."""

from fastapi import APIRouter

from api.routes import router as council_router
from api.websocket import router as websocket_router
from api.conversation_routes import router as conversation_router

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(council_router, prefix="/council")
api_router.include_router(websocket_router, prefix="/council")
api_router.include_router(conversation_router)
