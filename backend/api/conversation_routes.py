"""API routes for conversation persistence.

Provides REST endpoints for managing saved conversations:
- List, create, get, update, delete conversations
- Get messages for a conversation
- Save council output as a conversation
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status

import sys
from pathlib import Path

# Add src to path for imports
SRC_DIR = Path(__file__).parent.parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database import get_database, Conversation, Message

router = APIRouter(prefix="/conversations", tags=["conversations"])


# =============================================================================
# Request/Response Schemas
# =============================================================================


class ConversationCreate(BaseModel):
    """Request to create a new conversation."""

    title: str = Field(..., min_length=1, max_length=200)
    task: str = Field(..., min_length=1)
    output_mode: str = Field(default="perspectives")


class ConversationUpdate(BaseModel):
    """Request to update a conversation."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)


class ConversationResponse(BaseModel):
    """Response containing conversation data."""

    id: int
    title: str
    task: str
    output_mode: str
    created_at: str
    updated_at: str
    message_count: int
    aggregation_scores: Optional[dict[str, dict]] = None

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Response containing message data."""

    id: int
    conversation_id: int
    role: str
    content: str
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None
    created_at: str

    class Config:
        from_attributes = True


class ConversationDetailResponse(ConversationResponse):
    """Response containing conversation with messages."""

    messages: list[MessageResponse] = []


class SaveCouncilOutputRequest(BaseModel):
    """Request to save a council output as a conversation."""

    task: str
    output: dict
    title: Optional[str] = None


class ConversationListResponse(BaseModel):
    """Response containing list of conversations."""

    conversations: list[ConversationResponse]
    total: int


# =============================================================================
# Helper Functions
# =============================================================================


def _conversation_to_response(conv: Conversation, aggregation_scores: Optional[dict] = None) -> ConversationResponse:
    """Convert a Conversation to a response model."""
    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        task=conv.task,
        output_mode=conv.output_mode,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=conv.message_count,
        aggregation_scores=aggregation_scores,
    )


def _message_to_response(msg: Message) -> MessageResponse:
    """Convert a Message to a response model."""
    return MessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        role=msg.role,
        content=msg.content,
        model=msg.model,
        tokens_used=msg.tokens_used,
        latency_ms=msg.latency_ms,
        created_at=msg.created_at,
    )


# =============================================================================
# Conversation Endpoints
# =============================================================================


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
) -> ConversationListResponse:
    """List all conversations ordered by most recent.

    Args:
        limit: Maximum number of conversations to return.
        offset: Number of conversations to skip.

    Returns:
        List of conversations and total count.
    """
    db = get_database()
    conversations = db.list_conversations(limit=limit, offset=offset)

    return ConversationListResponse(
        conversations=[_conversation_to_response(c) for c in conversations],
        total=len(conversations),
    )


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: ConversationCreate,
) -> ConversationResponse:
    """Create a new conversation.

    Args:
        request: The conversation creation request.

    Returns:
        The created conversation.
    """
    db = get_database()
    conversation = db.create_conversation(
        title=request.title,
        task=request.task,
        output_mode=request.output_mode,
    )
    return _conversation_to_response(conversation)


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: int,
) -> ConversationDetailResponse:
    """Get a conversation by ID with all messages.

    Args:
        conversation_id: The conversation ID.

    Returns:
        The conversation with messages.

    Raises:
        HTTPException: If conversation not found.
    """
    db = get_database()
    conversation = db.get_conversation(conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    messages = db.get_messages(conversation_id)
    aggregation_scores = db.get_aggregation_scores(conversation_id)

    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        task=conversation.task,
        output_mode=conversation.output_mode,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=conversation.message_count,
        messages=[_message_to_response(m) for m in messages],
        aggregation_scores=aggregation_scores if aggregation_scores else None,
    )


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    request: ConversationUpdate,
) -> ConversationResponse:
    """Update a conversation.

    Args:
        conversation_id: The conversation ID.
        request: The update request.

    Returns:
        The updated conversation.

    Raises:
        HTTPException: If conversation not found.
    """
    db = get_database()
    conversation = db.update_conversation(
        conversation_id=conversation_id,
        title=request.title,
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    return _conversation_to_response(conversation)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
) -> None:
    """Delete a conversation and all its messages.

    Args:
        conversation_id: The conversation ID.

    Raises:
        HTTPException: If conversation not found.
    """
    db = get_database()
    deleted = db.delete_conversation(conversation_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )


# =============================================================================
# Save Council Output Endpoint
# =============================================================================


@router.post("/save-council-output", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def save_council_output(
    request: SaveCouncilOutputRequest,
) -> ConversationResponse:
    """Save a council deliberation output as a conversation.

    This is a convenience endpoint that creates a conversation and adds
    all role responses and synthesis in one call.

    Args:
        request: The save request containing task and output.

    Returns:
        The created conversation.
    """
    db = get_database()
    conversation = db.save_council_output(
        task=request.task,
        output=request.output,
        title=request.title,
    )
    
    # Retrieve aggregation scores if they were saved
    aggregation_scores = db.get_aggregation_scores(conversation.id)
    
    return _conversation_to_response(conversation, aggregation_scores if aggregation_scores else None)


# =============================================================================
# Message Endpoints (for potential future use)
# =============================================================================


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: int,
) -> list[MessageResponse]:
    """Get all messages for a conversation.

    Args:
        conversation_id: The conversation ID.

    Returns:
        List of messages.

    Raises:
        HTTPException: If conversation not found.
    """
    db = get_database()

    # Verify conversation exists
    conversation = db.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    messages = db.get_messages(conversation_id)
    return [_message_to_response(m) for m in messages]
