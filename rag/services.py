from __future__ import annotations

import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from threading import Lock

from .chunking import chunk_text
from .client import get_client
from .config import EMBED_CONCURRENCY, MAX_CHUNKS, MAX_SESSIONS, MAX_TEXT_CHARS, SESSION_TTL_SECONDS, TOP_K
from .embeddings import embed_text
from .generation import generate_answer
from .projection import Projection, fit


@dataclass
class InMemoryIndex:
    chunks: list[str]
    embeddings: list[list[float]]
    meta: dict = field(default_factory=dict)
    projection: Projection | None = None


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


def process_document(owner, text, max_size=1500, overlap=100, meta=None):
    """Chunk and embed a document, replacing the owner's in-memory index.

    `meta` (filename, kind, extract_ms) is kept next to the index for display;
    chunking and embedding timings are added here.
    """
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError(f"The document has too much text (limit {MAX_TEXT_CHARS:,} characters). Use a shorter file.")
    started = time.perf_counter()
    chunks = chunk_text(text, max_size=max_size, overlap=overlap)
    chunk_ms = _elapsed_ms(started)
    if not chunks:
        raise ValueError("The document did not produce any chunks.")
    if len(chunks) > MAX_CHUNKS:
        raise ValueError(f"The document produced {len(chunks)} chunks (limit {MAX_CHUNKS}). Use a larger chunk size or a shorter file.")

    client = get_client()
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=EMBED_CONCURRENCY) as pool:
        embeddings = list(pool.map(lambda chunk: embed_text(client, chunk, task="document"), chunks))
    embed_ms = _elapsed_ms(started)
    started = time.perf_counter()
    projection = fit(embeddings)
    project_ms = _elapsed_ms(started)
    info = {
        **(meta or {}),
        "chars": len(text),
        "max_size": max_size,
        "overlap": overlap,
        "chunk_ms": chunk_ms,
        "embed_ms": embed_ms,
        "project_ms": project_ms,
    }
    _put(owner, InMemoryIndex(chunks=chunks, embeddings=embeddings, meta=info, projection=projection))
    return len(chunks)


def clear_index(owner):
    with _lock:
        _indexes.pop(owner, None)


def document_stats(owner):
    """Numbers about the owner's index for the inspector, or None without one."""
    index = _get(owner)
    if index is None or not index.chunks:
        return None
    sizes = [len(chunk) for chunk in index.chunks]
    return {
        **index.meta,
        "chunks": len(sizes),
        "avg_size": round(sum(sizes) / len(sizes)),
        "min_size": min(sizes),
        "max_chunk": max(sizes),
        "histogram": _histogram(sizes),
        "expires_in": SESSION_TTL_SECONDS,  # _get just refreshed the expiry
    }


def all_chunks(owner):
    """Every chunk of the owner's index with its number and size."""
    index = _get(owner)
    if index is None:
        return []
    return [{"number": number, "size": len(chunk), "text": chunk} for number, chunk in enumerate(index.chunks, start=1)]


def document_cloud(owner):
    """3D positions of the owner's passages for the retrieval cloud, or None."""
    index = _get(owner)
    if index is None or index.projection is None:
        return None
    return {"points": index.projection.points, "variance": round(index.projection.variance * 100)}


def ask_question(owner, question, top_k=TOP_K):
    index = _get(owner)
    if index is None or not index.chunks:
        raise RuntimeError("No document is currently available. Upload and process one first.")

    client = get_client()
    started = time.perf_counter()
    query_embedding = embed_text(client, question, task="query")
    embed_ms = _elapsed_ms(started)

    started = time.perf_counter()
    ranked = sorted(
        (
            (_cosine_distance(query_embedding, embedding), number, chunk)
            for number, (chunk, embedding) in enumerate(zip(index.chunks, index.embeddings), start=1)
        ),
        key=lambda item: item[0],
    )[:top_k]
    retrieved = [{"text": chunk, "distance": distance, "similarity": 1.0 - distance, "number": number} for distance, number, chunk in ranked]
    retrieve_ms = _elapsed_ms(started)

    context = "\n\n".join(item["text"] for item in retrieved)
    started = time.perf_counter()
    answer = generate_answer(client, question, context)
    generate_ms = _elapsed_ms(started)
    query_point = index.projection.project(query_embedding) if index.projection else None
    return {
        "answer": answer,
        "sources": retrieved,
        "query_point": query_point,
        "timings": {"embed_ms": embed_ms, "retrieve_ms": retrieve_ms, "generate_ms": generate_ms},
    }


def _elapsed_ms(started):
    return round((time.perf_counter() - started) * 1000)


def _histogram(sizes, buckets=8):
    """Chunk sizes grouped into equal-width buckets; `height` is a 0-100 percentage of the tallest."""
    low, high = min(sizes), max(sizes)
    width = (high - low) / buckets or 1
    counts = [0] * buckets
    for size in sizes:
        counts[min(int((size - low) / width), buckets - 1)] += 1
    peak = max(counts)
    return [{"count": count, "height": round(count / peak * 100)} for count in counts]


def _cosine_distance(left, right):
    # Gemini embeddings are normalized in practice, but this remains safe if
    # that changes and avoids a dependency on a vector database for the MVP.
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if not left_norm or not right_norm:
        return 1.0
    similarity = sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)
    return 1.0 - similarity
