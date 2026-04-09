"""Application workflow: embedding storage."""

from __future__ import annotations

from dataclasses import dataclass

from studio.application.services.document_service import DocumentService
from studio.application.services.vector_store_service import VectorStoreService
from studio.domain.models import SourceDocument


@dataclass(slots=True)
class EmbeddingStorageResult:
    collection_name: str
    chunk_count: int
    stored: bool


class EmbeddingStorageWorkflow:
    """Coordinates chunk generation and persistence to the vector store."""

    def __init__(
        self,
        document_service: DocumentService | None = None,
        vector_store_service: VectorStoreService | None = None,
    ) -> None:
        self.document_service = document_service or DocumentService()
        self.vector_store_service = vector_store_service or VectorStoreService()

    def list_collections(self, *, host: str = "localhost", port: int = 6333) -> list[str]:
        client = self.vector_store_service.get_client(host=host, port=port)
        return self.vector_store_service.get_existing_collections(client)

    def preview_chunks(self, *, document_ids: list[int], max_tokens: int = 1000) -> list[str]:
        if not document_ids:
            return []
        documents = SourceDocument.objects.filter(id__in=document_ids)
        combined_text = "\n\n".join(doc.content for doc in documents)
        return self.document_service.split_text(combined_text, max_tokens=max_tokens)

    def store_document_embeddings(
        self,
        *,
        document_ids: list[int],
        collection_name: str,
        max_tokens: int = 1000,
        host: str = "localhost",
        port: int = 6333,
    ) -> EmbeddingStorageResult:
        if not collection_name.strip():
            raise ValueError("collection_name is required")
        chunks = self.preview_chunks(document_ids=document_ids, max_tokens=max_tokens)
        if not chunks:
            return EmbeddingStorageResult(collection_name=collection_name, chunk_count=0, stored=False)

        client = self.vector_store_service.get_client(host=host, port=port)
        stored = self.vector_store_service.store_chunks_in_qdrant(chunks, collection_name, client=client)

        return EmbeddingStorageResult(
            collection_name=collection_name,
            chunk_count=len(chunks),
            stored=bool(stored),
        )

    def fetch_collection_chunks(
        self,
        *,
        collection_name: str,
        host: str = "localhost",
        port: int = 6333,
        batch_size: int = 100,
    ) -> list[str]:
        client = self.vector_store_service.get_client(host=host, port=port)
        return self.vector_store_service.fetch_chunks_from_collection(
            collection_name=collection_name,
            batch_size=batch_size,
            client=client,
        )
