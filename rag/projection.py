"""3D projection of the embeddings for the retrieval cloud (PCA, pure Python).

Display only: retrieval still ranks by cosine distance in the full space.
With at most MAX_CHUNKS vectors, PCA runs on the n x n Gram matrix, which is
much cheaper than the d x d covariance when n < d.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from operator import mul

DIMS = 3
_ITERATIONS = 200
_TOLERANCE = 1e-10


@dataclass
class Projection:
    mean: list[float]
    components: list[list[float]]  # DIMS unit vectors in embedding space (zero when degenerate)
    scale: float
    points: list[list[float]]  # one [x, y, z] per embedding, inside the unit sphere
    variance: float  # share of the total variance kept by the 3 axes, 0..1

    def project(self, vector, limit=1.6):
        """Place a new vector (the query) in the same 3D space as the points."""
        centered = [a - m for a, m in zip(_unit(vector), self.mean)]
        coords = [_dot(centered, component) / self.scale for component in self.components]
        norm = _norm(coords)
        if norm > limit:
            coords = [value * limit / norm for value in coords]
        return [round(value, 3) for value in coords]


def fit(vectors, seed=7):
    """Fit a 3-axis PCA on cosine-normalized vectors."""
    rows = [_unit(vector) for vector in vectors]
    count = len(rows)
    width = len(rows[0])
    mean = [sum(column) / count for column in zip(*rows)]
    centered = [[a - m for a, m in zip(row, mean)] for row in rows]
    gram = [[0.0] * count for _ in range(count)]
    for i in range(count):
        for j in range(i, count):
            gram[i][j] = gram[j][i] = _dot(centered[i], centered[j])
    total = sum(gram[i][i] for i in range(count)) or 1.0
    columns = list(zip(*centered))

    rng = random.Random(seed)
    components = []
    kept = 0.0
    for _ in range(DIMS):
        value, vector = _top_eigen(gram, rng)
        # Relative cutoff: what is left after deflating a low-rank input is rounding noise.
        if value <= total * 1e-9:
            components.append([0.0] * width)
            continue
        # Embedding-space axis: C^T u, kept orthogonal to the previous axes.
        axis = [sum(map(mul, vector, column)) for column in columns]
        for previous in components:
            overlap = _dot(axis, previous)
            axis = [a - overlap * p for a, p in zip(axis, previous)]
        norm = _norm(axis)
        if norm <= 1e-9:
            components.append([0.0] * width)
            continue
        kept += value
        axis = _scaled(axis, 1 / norm)
        # Fixed orientation so the same document always looks the same.
        if max(axis, key=abs) < 0:
            axis = [-a for a in axis]
        components.append(axis)
        # Deflate: remove this eigenpair from the Gram matrix.
        for i in range(count):
            row = gram[i]
            factor = value * vector[i]
            for j in range(count):
                row[j] -= factor * vector[j]

    coords = [[_dot(row, axis) for axis in components] for row in centered]
    scale = max((_norm(point) for point in coords), default=0.0) or 1.0
    points = [[round(value / scale, 3) for value in point] for point in coords]
    return Projection(mean=mean, components=components, scale=scale, points=points, variance=kept / total)


def _top_eigen(matrix, rng):
    """Largest eigenpair of a symmetric positive semi-definite matrix (power iteration)."""
    size = len(matrix)
    vector = [rng.uniform(-1, 1) for _ in range(size)]
    vector = _scaled(vector, 1 / (_norm(vector) or 1.0))
    value = 0.0
    for _ in range(_ITERATIONS):
        product = [_dot(row, vector) for row in matrix]
        value = _norm(product)
        if value <= 1e-12:
            return 0.0, vector
        nxt = _scaled(product, 1 / value)
        converged = abs(_dot(nxt, vector)) > 1 - _TOLERANCE
        vector = nxt
        if converged:
            break
    return value, vector


def _dot(left, right):
    return sum(map(mul, left, right))


def _norm(vector):
    return _dot(vector, vector) ** 0.5


def _scaled(vector, factor):
    return [value * factor for value in vector]


def _unit(vector):
    norm = _norm(vector)
    return _scaled(vector, 1 / norm) if norm else list(vector)
