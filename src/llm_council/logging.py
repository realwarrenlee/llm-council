"""Logging configuration for LLM Council."""

import logging
from typing import Any


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given module name.

    Args:
        name: Module name (typically __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if no handlers exist (avoid duplicate configuration)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Default to INFO level, can be overridden by user
        logger.setLevel(logging.INFO)

    return logger


def log_exception(logger: logging.Logger, exc: Exception, context: str = "") -> None:
    """Log an exception with context.

    Args:
        logger: Logger instance
        exc: Exception to log
        context: Additional context about where the exception occurred
    """
    if context:
        logger.error(f"{context}: {type(exc).__name__}: {exc}", exc_info=True)
    else:
        logger.error(f"{type(exc).__name__}: {exc}", exc_info=True)
