"""Application service: embedding and vector store operations."""

from __future__ import annotations

import importlib
from typing import Any


class VectorStoreService:
    """Qdrant functionality migrated from `generate_dataset_chunks.py`."""

    def safe_import_qdrant(self):
        try:
            qdrant_client = importlib.import_module("qdrant_client")
            qmodels = importlib.import_module("qdrant_client.http.models")
            return qdrant_client.QdrantClient, qmodels
        except ImportError:
            return None, None

    def get_client(self, host: str = "localhost", port: int = 6333):
        qdrant_cls, _ = self.safe_import_qdrant()
        if not qdrant_cls:
            return None
        return qdrant_cls(host=host, port=port)

    def get_existing_collections(self, client) -> list[str]:
        if not client:
            return []
        return [c.name for c in client.get_collections().collections]

    def ensure_collection_exists(self, client, collection_name: str, vector_size: int) -> None:
        _, qmodels = self.safe_import_qdrant()
        if not client or not qmodels:
            return
        if collection_name in self.get_existing_collections(client):
            return
        client.create_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(size=vector_size, distance=qmodels.Distance.COSINE),
        )

    def store_chunks_in_qdrant(self, chunks: list[str], collection_name: str, client=None) -> bool:
        if not chunks:
            return False
        if client is None:
            client = self.get_client()
        if not client:
            return False

        _, qmodels = self.safe_import_qdrant()
        if not qmodels:
            return False

        from sentence_transformers import SentenceTransformer

        embedder = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = embedder.encode(chunks).tolist()
        vector_size = len(embeddings[0])
        self.ensure_collection_exists(client, collection_name, vector_size)

        try:
            existing_count = client.count(collection_name=collection_name).count
        except Exception:
            existing_count = 0

        points = [
            qmodels.PointStruct(id=existing_count + i + 1, vector=embeddings[i], payload={"text": chunks[i]})
            for i in range(len(chunks))
        ]
        client.upsert(collection_name=collection_name, points=points)
        return True

    def fetch_chunks_from_collection(self, collection_name: str, batch_size: int = 100, client=None) -> list[str]:
        if client is None:
            client = self.get_client()
        if not client:
            return []

        all_chunks: list[str] = []
        offset: Any = None
        while True:
            result, offset = client.scroll(
                collection_name=collection_name,
                limit=batch_size,
                with_payload=True,
                offset=offset,
            )
            if not result:
                break
            all_chunks.extend([p.payload.get("text", "") for p in result])
            if offset is None:
                break
        return all_chunks
