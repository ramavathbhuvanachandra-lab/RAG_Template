"""Reusable embedding runtime adapter.

Embedding implementation is deployment infrastructure. The model and Ollama
endpoint are configurable through environment variables and are not tied to
a particular institution.
"""

from __future__ import annotations

import os

from langchain_ollama import OllamaEmbeddings


import logging

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
).strip()

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "nomic-embed-text:latest",
).strip()

def _parse_keep_alive(val: str) -> int | None:
    try:
        return int(val)
    except (ValueError, TypeError):
        return 3600

EMBEDDING_KEEP_ALIVE = _parse_keep_alive(os.getenv("EMBEDDING_KEEP_ALIVE", "3600"))


def get_embeddings() -> OllamaEmbeddings:
    """Create the configured embedding model."""

    if not OLLAMA_BASE_URL:
        raise ValueError("OLLAMA_BASE_URL cannot be empty")

    if not EMBEDDING_MODEL:
        raise ValueError("EMBEDDING_MODEL cannot be empty")

    return OllamaEmbeddings(
        model=EMBEDDING_MODEL,
        base_url=OLLAMA_BASE_URL,
        keep_alive=EMBEDDING_KEEP_ALIVE,
    )


# Runtime singleton for the current application.
embeddings = get_embeddings()


def warmup_embeddings() -> None:
    """Pre-warm the embedding model in GPU/RAM to prevent first-query cold-start latency."""
    try:
        embeddings.embed_query("warmup")
    except Exception as exc:
        logger.warning("Embedding warmup skipped: %s", exc)


__all__ = [
    "OLLAMA_BASE_URL",
    "EMBEDDING_MODEL",
    "EMBEDDING_KEEP_ALIVE",
    "get_embeddings",
    "embeddings",
    "warmup_embeddings",
]
