"""Core RAG utilities used by the Django application."""

from .chunking import chunk_text
from .client import get_client
from .config import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    GENERATION_MODEL,
)
from .embeddings import embed_text
from .generation import generate_answer

__all__ = [
    "chunk_text",
    "get_client",
    "EMBEDDING_DIM",
    "EMBEDDING_MODEL",
    "GENERATION_MODEL",
    "embed_text",
    "generate_answer",
]
