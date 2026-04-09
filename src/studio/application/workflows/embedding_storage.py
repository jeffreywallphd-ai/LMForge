"""Application workflow: embedding storage orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from studio.application.services.document_service import DocumentService
from studio.application.services.vector_store_service import VectorStoreService
from studio.domain.models import SourceDocument


@dataclass(slots=True)
class EmbeddingStorageWorkflowRequest:
    """Workflow contract for storing document embeddings."""

    document_ids: list[int]
    collection_name: str
    max_tokens: int = 1000
    host: str = "localhost"
    port: int = 6333


@dataclass(slots=True)
class EmbeddingStorageWorkflowFailure:
    """Typed failure payload for expected workflow errors."""

    code: str
    message: str


@dataclass(slots=True)
class EmbeddingStorageResult:
    """Normalized workflow outcome consumable by presentation handlers."""

    ok: bool
    collection_name: str
    chunk_count: int
    stored: bool
    failure: EmbeddingStorageWorkflowFailure | None = None


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

    def run(self, request: EmbeddingStorageWorkflowRequest) -> EmbeddingStorageResult:
        collection_name = request.collection_name.strip()
        if not collection_name:
            return EmbeddingStorageResult(
                ok=False,
                collection_name="",
                chunk_count=0,
                stored=False,
                failure=EmbeddingStorageWorkflowFailure(
                    code="validation_error",
                    message="Please select or enter a collection name.",
                ),
            )

        chunks = self.preview_chunks(document_ids=request.document_ids, max_tokens=request.max_tokens)
        if not chunks:
            return EmbeddingStorageResult(
                ok=False,
                collection_name=collection_name,
                chunk_count=0,
                stored=False,
                failure=EmbeddingStorageWorkflowFailure(
                    code="validation_error",
                    message="You must select at least one document to proceed.",
                ),
            )

        client = self.vector_store_service.get_client(host=request.host, port=request.port)
        stored = self.vector_store_service.store_chunks_in_qdrant(chunks, collection_name, client=client)
        if not stored:
            return EmbeddingStorageResult(
                ok=False,
                collection_name=collection_name,
                chunk_count=len(chunks),
                stored=False,
                failure=EmbeddingStorageWorkflowFailure(
                    code="storage_failure",
                    message=f"Failed to store chunks in '{collection_name}'. Ensure Qdrant is running.",
                ),
            )

        return EmbeddingStorageResult(
            ok=True,
            collection_name=collection_name,
            chunk_count=len(chunks),
            stored=True,
            failure=None,
        )

    def store_document_embeddings(
        self,
        *,
        document_ids: list[int],
        collection_name: str,
        max_tokens: int = 1000,
        host: str = "localhost",
        port: int = 6333,
    ) -> EmbeddingStorageResult:
        """Compatibility wrapper for legacy callers."""

        result = self.run(
            EmbeddingStorageWorkflowRequest(
                document_ids=document_ids,
                collection_name=collection_name,
                max_tokens=max_tokens,
                host=host,
                port=port,
            )
        )
        if not result.ok and result.failure and result.failure.code == "validation_error" and not collection_name.strip():
            raise ValueError("collection_name is required")
        return result

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
