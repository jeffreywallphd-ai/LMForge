# Context Pack: Embedding and Vector Store

## Use When

- Working on Qdrant collection management, embedding upserts, or retrieval of stored chunks.

## Primary Files

- `src/studio/application/services/vector_store_service.py`
- `src/studio/application/workflows/embedding_storage.py`
- `src/studio/infrastructure/vectorstores/qdrant.py`
- `src/studio/presentation/api/views/datasets.py`

## Core Facts

- `VectorStoreService` dynamically imports Qdrant client modules and no-ops gracefully if unavailable.
- Embeddings use `all-MiniLM-L6-v2` before upsert operations.
- `EmbeddingStorageWorkflow.run(...)` is the orchestration boundary for embedding storage: validate collection input -> chunk selected documents -> delegate vector persistence through `VectorStoreService` -> normalize `ok/failure` result contract for presentation adapters.
- API callers should invoke the workflow (for example `database_workflow`) instead of coordinating chunking/storage directly.

## Important Constraints

- Keep behavior resilient when Qdrant is down or client package is missing.
- Ensure collection vector dimension consistency before upsert.

## Embedding Storage Workflow Lifecycle

1. Presentation parses primitive payload values (`selected_documents`, collection inputs).
2. `EmbeddingStorageWorkflow.run(...)` validates workflow input and builds chunks through `DocumentService.split_text(...)`.
3. Workflow delegates embedding/upsert operations to `VectorStoreService.store_chunks_in_qdrant(...)`.
4. Workflow returns normalized `EmbeddingStorageResult` with `ok`, `chunk_count`, and typed failure metadata (`validation_error` or `storage_failure`).
