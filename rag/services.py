from __future__ import annotations

import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock

from .chunking import chunk_text
from .client import get_client
from .config import EMBED_CONCURRENCY, MAX_CHUNKS, MAX_SESSIONS, MAX_TEXT_CHARS, SESSION_TTL_SECONDS
from .embeddings import embed_text
from .generation import generate_answer


@dataclass
class InMemoryIndex:
    chunks: list[str]
    embeddings: list[list[float]]


# One index per owner (an opaque session token), most recently used last.
_indexes: OrderedDict[str, tuple[float, InMemoryIndex]] = OrderedDict()
_lock = Lock()


def _get(owner):
    """Return the owner's live index and refresh its expiry, or None."""
    if not owner:
        return None
    now = time.monotonic()
    with _lock:
        entry = _indexes.get(owner)
        if entry is None or entry[0] < now:
            _indexes.pop(owner, None)
            return None
        _indexes[owner] = (now + SESSION_TTL_SECONDS, entry[1])
        _indexes.move_to_end(owner)
        return entry[1]


def _put(owner, index):
    now = time.monotonic()
    with _lock:
        _indexes[owner] = (now + SESSION_TTL_SECONDS, index)
        _indexes.move_to_end(owner)
        for key in [key for key, (expires_at, _) in _indexes.items() if expires_at < now]:
            del _indexes[key]
        while len(_indexes) > MAX_SESSIONS:
            _indexes.popitem(last=False)


def process_document(owner, text, max_size=1500, overlap=100):
    """Chunk and embed a document, replacing the owner's in-memory index."""
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError(f"The document has too much text (limit {MAX_TEXT_CHARS:,} characters). Use a shorter file.")
    chunks = chunk_text(text, max_size=max_size, overlap=overlap)
    if not chunks:
        raise ValueError("The document did not produce any chunks.")
    if len(chunks) > MAX_CHUNKS:
        raise ValueError(f"The document produced {len(chunks)} chunks (limit {MAX_CHUNKS}). Use a larger chunk size or a shorter file.")

    client = get_client()
    with ThreadPoolExecutor(max_workers=EMBED_CONCURRENCY) as pool:
        embeddings = list(pool.map(lambda chunk: embed_text(client, chunk, task="document"), chunks))
    _put(owner, InMemoryIndex(chunks=chunks, embeddings=embeddings))
    return len(chunks)


def clear_index(owner):
    with _lock:
        _indexes.pop(owner, None)


def has_context(owner):
    index = _get(owner)
    return index is not None and bool(index.chunks)


def chunk_previews(owner, limit=3, max_chars=220):
    """First chunks of the owner's index, shortened for display."""
    index = _get(owner)
    if index is None:
        return []
    return [
        {"number": number, "size": len(chunk), "text": chunk if len(chunk) <= max_chars else chunk[:max_chars].rstrip() + "..."}
        for number, chunk in enumerate(index.chunks[:limit], start=1)
    ]


def ask_question(owner, question, top_k=5):
    index = _get(owner)
    if index is None or not index.chunks:
        raise RuntimeError("No document is currently available. Upload and process one first.")

    client = get_client()
    query_embedding = embed_text(client, question, task="query")
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
