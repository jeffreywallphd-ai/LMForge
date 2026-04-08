"""Qdrant vector store adapter.

Migrated from ``lmforge_core.utils.qdrant_utils`` with safer collection checks and
explicit exports.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_EMBEDDING_MODEL_NAME = os.environ.get("QA_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
_DEFAULT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "qa_chunks")

_embedding_model: SentenceTransformer | None = None
_qdrant_client: QdrantClient | None = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading embedding model: %s", _EMBEDDING_MODEL_NAME)
        _embedding_model = SentenceTransformer(_EMBEDDING_MODEL_NAME)
    return _embedding_model


def get_qdrant_client(host: str = "localhost", port: int = 6333) -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        url = f"http://{host}:{port}"
        logger.info("Connecting to Qdrant at %s", url)
        _qdrant_client = QdrantClient(url=url)
    return _qdrant_client


def ensure_collection(
    collection_name: str = _DEFAULT_COLLECTION,
    vector_size: int = 384,
    distance: str = "cosine",
) -> None:
    client = get_qdrant_client()
    existing = client.get_collections().collections
    if any(col.name == collection_name for col in existing):
        return

    metric = {
        "cosine": qmodels.Distance.COSINE,
        "euclid": qmodels.Distance.EUCLID,
        "dot": qmodels.Distance.DOT,
    }.get(distance.lower(), qmodels.Distance.COSINE)

    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=qmodels.VectorParams(size=vector_size, distance=metric),
    )


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return embeddings.tolist()


def upsert_qa_items(items: list[dict[str, Any]], collection_name: str = _DEFAULT_COLLECTION) -> dict[str, Any]:
    if not items:
        return {"upserted": 0}

    concat_texts = [f"Q: {it.get('question', '')} A: {it.get('answer', '')}" for it in items]
    vectors = embed_texts(concat_texts)
    ensure_collection(collection_name=collection_name, vector_size=len(vectors[0]), distance="cosine")

    client = get_qdrant_client()
    point_ids: list[str] = []
    points: list[qmodels.PointStruct] = []
    for vec, item in zip(vectors, items):
        point_id = str(uuid.uuid4())
        payload = dict(item)
        payload.pop("vector", None)
        points.append(qmodels.PointStruct(id=point_id, vector=vec, payload=payload))
        point_ids.append(point_id)

    client.upsert(collection_name=collection_name, points=points)
    return {"upserted": len(points), "point_ids": point_ids}


def search_similar(query: str, top_k: int = 5, collection_name: str = _DEFAULT_COLLECTION) -> list[dict[str, Any]]:
    client = get_qdrant_client()
    query_vector = embed_texts([query])[0]
    hits = client.search(collection_name=collection_name, query_vector=query_vector, limit=top_k)
    return [{"id": hit.id, "score": hit.score, "payload": hit.payload} for hit in hits]


__all__ = [
    "get_embedding_model",
    "get_qdrant_client",
    "ensure_collection",
    "embed_texts",
    "upsert_qa_items",
    "search_similar",
]
