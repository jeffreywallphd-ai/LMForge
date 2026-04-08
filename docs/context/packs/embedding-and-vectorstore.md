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
- Workflow layer coordinates source text chunking with vector store persistence.
- There are two implementation surfaces today: workflow/service abstractions and a legacy integrated dataset view.

## Important Constraints

- Keep behavior resilient when Qdrant is down or client package is missing.
- Ensure collection vector dimension consistency before upsert.
