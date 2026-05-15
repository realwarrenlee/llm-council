"""SQLite database for persisting conversations and messages.

This module provides a simple SQLite-based persistence layer for LLM Council
conversations, allowing users to save, retrieve, and manage their deliberation
history.
"""

from __future__ import annotations

import sqlite3
import json
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
from contextlib import contextmanager


# Default database location in the project root
DEFAULT_DB_PATH = Path(__file__).parent.parent / "llm_council.db"


@dataclass
class Message:
    """A single message in a conversation."""

    id: Optional[int] = None
    conversation_id: Optional[int] = None
    role: str = ""  # "user" or assistant role name
    content: str = ""
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Conversation:
    """A conversation containing multiple messages."""

    id: Optional[int] = None
    title: str = ""
    task: str = ""  # The original task/prompt
    output_mode: str = "perspectives"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    message_count: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class Database:
    """SQLite database manager for LLM Council conversations."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        """Initialize database connection.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self._init_database()

    @contextmanager
    def _get_connection(self):
        """Get a database connection as a context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_database(self) -> None:
        """Initialize database tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create conversations table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    task TEXT NOT NULL,
                    output_mode TEXT DEFAULT 'perspectives',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0
                )
                """
            )

            # Create messages table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    model TEXT,
                    tokens_used INTEGER,
                    latency_ms REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
                """
            )

            # Create aggregation_scores table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS aggregation_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    method TEXT NOT NULL,
                    scores TEXT NOT NULL,
                    confidence_intervals TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
                """
            )

            # Create index for faster message lookups
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
                ON messages(conversation_id)
                """
            )

            # Create index for faster aggregation_scores lookups
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_aggregation_scores_conversation_id
                ON aggregation_scores(conversation_id)
                """
            )

    # =========================================================================
    # Conversation Operations
    # =========================================================================

    def create_conversation(
        self, title: str, task: str, output_mode: str = "perspectives"
    ) -> Conversation:
        """Create a new conversation.

        Args:
            title: The conversation title.
            task: The original task/prompt.
            output_mode: The output mode used (synthesis, perspectives, both).

        Returns:
            The created Conversation with ID.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO conversations (title, task, output_mode)
                VALUES (?, ?, ?)
                """,
                (title, task, output_mode),
            )
            conversation_id = cursor.lastrowid

            # Fetch the created conversation
            cursor.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            row = cursor.fetchone()
            return self._row_to_conversation(row)

    def get_conversation(self, conversation_id: int) -> Optional[Conversation]:
        """Get a conversation by ID.

        Args:
            conversation_id: The conversation ID.

        Returns:
            The Conversation or None if not found.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_conversation(row)
            return None

    def list_conversations(
        self, limit: int = 50, offset: int = 0
    ) -> list[Conversation]:
        """List conversations ordered by most recent.

        Args:
            limit: Maximum number of conversations to return.
            offset: Number of conversations to skip.

        Returns:
            List of Conversation objects.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM conversations
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            rows = cursor.fetchall()
            return [self._row_to_conversation(row) for row in rows]

    def update_conversation(
        self, conversation_id: int, title: Optional[str] = None
    ) -> Optional[Conversation]:
        """Update a conversation.

        Args:
            conversation_id: The conversation ID.
            title: New title (optional).

        Returns:
            The updated Conversation or None if not found.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Build update query dynamically
            updates = []
            params = []
            if title is not None:
                updates.append("title = ?")
                params.append(title)

            if not updates:
                return self.get_conversation(conversation_id)

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(conversation_id)

            cursor.execute(
                f"""
                UPDATE conversations
                SET {', '.join(updates)}
                WHERE id = ?
                """,
                params,
            )

            if cursor.rowcount == 0:
                return None

            return self.get_conversation(conversation_id)

    def delete_conversation(self, conversation_id: int) -> bool:
        """Delete a conversation and all its messages.

        Args:
            conversation_id: The conversation ID.

        Returns:
            True if deleted, False if not found.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            return cursor.rowcount > 0

    # =========================================================================
    # Message Operations
    # =========================================================================

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        model: Optional[str] = None,
        tokens_used: Optional[int] = None,
        latency_ms: Optional[float] = None,
    ) -> Message:
        """Add a message to a conversation.

        Args:
            conversation_id: The conversation ID.
            role: The role name (e.g., "user", "advocate", "critic").
            content: The message content.
            model: The model used (optional).
            tokens_used: Number of tokens used (optional).
            latency_ms: Response latency in milliseconds (optional).

        Returns:
            The created Message with ID.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Insert the message
            cursor.execute(
                """
                INSERT INTO messages
                (conversation_id, role, content, model, tokens_used, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (conversation_id, role, content, model, tokens_used, latency_ms),
            )
            message_id = cursor.lastrowid

            # Update message count and timestamp
            cursor.execute(
                """
                UPDATE conversations
                SET message_count = message_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (conversation_id,),
            )

            # Fetch the created message
            cursor.execute(
                "SELECT * FROM messages WHERE id = ?",
                (message_id,),
            )
            row = cursor.fetchone()
            return self._row_to_message(row)

    def get_messages(self, conversation_id: int) -> list[Message]:
        """Get all messages for a conversation.

        Args:
            conversation_id: The conversation ID.

        Returns:
            List of Message objects ordered by creation time.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                """,
                (conversation_id,),
            )
            rows = cursor.fetchall()
            return [self._row_to_message(row) for row in rows]

    def delete_message(self, message_id: int) -> bool:
        """Delete a single message.

        Args:
            message_id: The message ID.

        Returns:
            True if deleted, False if not found.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get conversation_id first to update count
            cursor.execute(
                "SELECT conversation_id FROM messages WHERE id = ?",
                (message_id,),
            )
            row = cursor.fetchone()
            if not row:
                return False

            conversation_id = row["conversation_id"]

            # Delete the message
            cursor.execute(
                "DELETE FROM messages WHERE id = ?",
                (message_id,),
            )

            # Update message count
            cursor.execute(
                """
                UPDATE conversations
                SET message_count = message_count - 1
                WHERE id = ?
                """,
                (conversation_id,),
            )

            return True

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _row_to_conversation(self, row: sqlite3.Row) -> Conversation:
        """Convert a database row to a Conversation object."""
        return Conversation(
            id=row["id"],
            title=row["title"],
            task=row["task"],
            output_mode=row["output_mode"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            message_count=row["message_count"],
        )

    def _row_to_message(self, row: sqlite3.Row) -> Message:
        """Convert a database row to a Message object."""
        return Message(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row["content"],
            model=row["model"],
            tokens_used=row["tokens_used"],
            latency_ms=row["latency_ms"],
            created_at=row["created_at"],
        )

    def add_aggregation_scores(
        self,
        conversation_id: int,
        method: str,
        scores: dict[str, float],
        confidence_intervals: Optional[dict[str, tuple[float, float]]] = None,
    ) -> None:
        """Add aggregation scores for a conversation.

        Args:
            conversation_id: The conversation ID.
            method: The aggregation method name (e.g., "borda", "bradley_terry", "elo").
            scores: Dictionary mapping model names to scores.
            confidence_intervals: Optional confidence intervals for each model.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO aggregation_scores
                (conversation_id, method, scores, confidence_intervals)
                VALUES (?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    method,
                    json.dumps(scores),
                    json.dumps(confidence_intervals) if confidence_intervals else None,
                ),
            )

    def get_aggregation_scores(
        self, conversation_id: int
    ) -> dict[str, dict]:
        """Get all aggregation scores for a conversation.

        Args:
            conversation_id: The conversation ID.

        Returns:
            Dictionary mapping method names to score data with structure:
            {
                "method_name": {
                    "scores": {"model": score, ...},
                    "confidence_intervals": {"model": (lower, upper), ...} or None
                }
            }
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT method, scores, confidence_intervals
                FROM aggregation_scores
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                """,
                (conversation_id,),
            )
            rows = cursor.fetchall()

            result = {}
            for row in rows:
                method = row["method"]
                scores = json.loads(row["scores"])
                confidence_intervals = (
                    json.loads(row["confidence_intervals"])
                    if row["confidence_intervals"]
                    else None
                )
                result[method] = {
                    "scores": scores,
                    "confidence_intervals": confidence_intervals,
                }

            return result

    def save_council_output(
        self,
        task: str,
        output: dict,
        title: Optional[str] = None,
    ) -> Conversation:
        """Save a complete council output as a conversation.

        This is a convenience method to save all results from a deliberation
        in one call.

        Args:
            task: The original task/prompt.
            output: The CouncilOutput dictionary with results, synthesis, etc.
            title: Optional title (defaults to truncated task).

        Returns:
            The created Conversation.
        """
        # Generate title from task if not provided
        if title is None:
            title = task[:50] + "..." if len(task) > 50 else task

        output_mode = output.get("output_mode", "perspectives")

        # Create conversation
        conversation = self.create_conversation(
            title=title,
            task=task,
            output_mode=output_mode,
        )

        # Add user message (the task)
        self.add_message(
            conversation_id=conversation.id,
            role="user",
            content=task,
        )

        # Add role responses
        for result in output.get("results", []):
            self.add_message(
                conversation_id=conversation.id,
                role=result.get("role_name", "unknown"),
                content=result.get("content", ""),
                model=result.get("model"),
                tokens_used=result.get("tokens_used"),
                latency_ms=result.get("latency_ms"),
            )

        # Add synthesis if present
        synthesis = output.get("synthesis")
        if synthesis:
            self.add_message(
                conversation_id=conversation.id,
                role="synthesis",
                content=synthesis,
            )

        # Add aggregation scores if present
        aggregation_scores = output.get("aggregation_scores", {})
        if aggregation_scores:
            for method, data in aggregation_scores.items():
                scores = data.get("scores", {})
                confidence_intervals = data.get("confidence_intervals")
                if scores:
                    self.add_aggregation_scores(
                        conversation_id=conversation.id,
                        method=method,
                        scores=scores,
                        confidence_intervals=confidence_intervals,
                    )

        return conversation


# Global database instance (initialized on first use)
_db_instance: Optional[Database] = None


def get_database(db_path: Optional[Path | str] = None) -> Database:
    """Get the global database instance.

    Args:
        db_path: Optional path to database file.

    Returns:
        Database instance.
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(db_path or DEFAULT_DB_PATH)
    return _db_instance


def reset_database() -> None:
    """Reset the global database instance (useful for testing)."""
    global _db_instance
    _db_instance = None
