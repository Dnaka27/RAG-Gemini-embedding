from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from .chunking import chunk_text
from .client import get_client
from .embeddings import embed_text
from .generation import generate_answer


@dataclass
class InMemoryIndex:
    chunks: list[str]
    embeddings: list[list[float]]


_index: InMemoryIndex | None = None
_lock = Lock()


def process_document(text, max_size=1500, overlap=100):
    """Chunk and embed a document, replacing the process-local index."""
    chunks = chunk_text(text, max_size=max_size, overlap=overlap)
    if not chunks:
        raise ValueError("The document did not produce any chunks.")

    client = get_client()
    embeddings = [embed_text(client, chunk, task="document") for chunk in chunks]
    global _index
    with _lock:
        _index = InMemoryIndex(chunks=chunks, embeddings=embeddings)
    return len(chunks)


def clear_index():
    global _index
    with _lock:
        _index = None


def has_context():
    return _index is not None and bool(_index.chunks)


def ask_question(question, top_k=5):
    if not has_context():
        raise RuntimeError("No document is currently available. Upload and process one first.")

    client = get_client()
    query_embedding = embed_text(client, question, task="query")
    index = _index
    ranked = sorted(
        (
            (_cosine_distance(query_embedding, embedding), chunk)
            for chunk, embedding in zip(index.chunks, index.embeddings)
        ),
        key=lambda item: item[0],
    )[:top_k]
    retrieved = [{"text": chunk, "distance": distance} for distance, chunk in ranked]
    context = "\n\n".join(item["text"] for item in retrieved)
    answer = generate_answer(client, question, context)
    return {"answer": answer, "sources": retrieved}


def _cosine_distance(left, right):
    # Gemini embeddings are normalized in practice, but this remains safe if
    # that changes and avoids a dependency on a vector database for the MVP.
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if not left_norm or not right_norm:
        return 1.0
    similarity = sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)
    return 1.0 - similarity
