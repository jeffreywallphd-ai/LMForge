"""Domain value objects for vector store collections."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class VectorCollection:
    name: str
    embedding_model: str
    vector_size: int
    distance_metric: str = "cosine"
