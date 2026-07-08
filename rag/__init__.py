"""Core RAG pipeline: chunking, embeddings (gemini-embedding-2), vector store (ChromaDB) and generation.

Shared by main.ipynb and app.py so both entry points stay in sync.
"""
from .chunking import chunk_text
from .client import get_client
from .config import (
    COLLECTION_NAME,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    GENERATION_MODEL,
    PERSIST_DIR,
)
from .embeddings import embed_text
from .generation import generate_answer
from .vector_store import add_chunks, get_collection, reset_collection, retrieve

__all__ = [
    "chunk_text",
    "get_client",
    "COLLECTION_NAME",
    "EMBEDDING_DIM",
    "EMBEDDING_MODEL",
    "GENERATION_MODEL",
    "PERSIST_DIR",
    "embed_text",
    "generate_answer",
    "add_chunks",
    "get_collection",
    "reset_collection",
    "retrieve",
]
