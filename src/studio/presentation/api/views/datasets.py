from __future__ import annotations

from django.http import JsonResponse

from studio.application.workflows.embedding_storage import EmbeddingStorageWorkflow, EmbeddingStorageWorkflowRequest


DEFAULT_QDRANT_HOST = "localhost"
DEFAULT_QDRANT_PORT = 6333


def get_embedding_workflow() -> EmbeddingStorageWorkflow:
    return EmbeddingStorageWorkflow()


def _parse_document_ids(raw_values: list[str]) -> list[int]:
    parsed: list[int] = []
    for value in raw_values:
        try:
            parsed.append(int(value))
        except (TypeError, ValueError):
            continue
    return parsed


def database_workflow(request):
    workflow = get_embedding_workflow()
    existing_collections = workflow.list_collections(host=DEFAULT_QDRANT_HOST, port=DEFAULT_QDRANT_PORT)

    if request.method == "GET" and request.GET.get("collection_name"):
        chunks = workflow.fetch_collection_chunks(
            collection_name=request.GET.get("collection_name", ""),
            host=DEFAULT_QDRANT_HOST,
            port=DEFAULT_QDRANT_PORT,
        )
        return JsonResponse({"chunks": chunks})

    if request.method == "POST":
        selected_document_ids = request.POST.getlist("selected_documents")
        document_ids = _parse_document_ids(selected_document_ids)

        new_collection = request.POST.get("new_collection_name", "").strip()
        selected_collection = request.POST.get("collection_name", "").strip()
        collection_name = new_collection if new_collection else selected_collection

        result = workflow.run(
            EmbeddingStorageWorkflowRequest(
                document_ids=document_ids,
                collection_name=collection_name,
                host=DEFAULT_QDRANT_HOST,
                port=DEFAULT_QDRANT_PORT,
            )
        )

        if not result.ok:
            status_code = 400 if result.failure and result.failure.code == "validation_error" else 500
            return JsonResponse(
                {
                    "status": "error",
                    "error": {
                        "code": result.failure.code if result.failure else "storage_failure",
                        "message": result.failure.message if result.failure else "Embedding storage failed.",
                    },
                    "data": {
                        "total_chunks": result.chunk_count,
                        "existing_collections": workflow.list_collections(
                            host=DEFAULT_QDRANT_HOST,
                            port=DEFAULT_QDRANT_PORT,
                        ),
                        "selected_document_ids": selected_document_ids,
                    },
                },
                status=status_code,
            )

        return JsonResponse(
            {
                "status": "success",
                "data": {
                    "total_chunks": result.chunk_count,
                    "existing_collections": workflow.list_collections(
                        host=DEFAULT_QDRANT_HOST,
                        port=DEFAULT_QDRANT_PORT,
                    ),
                    "selected_document_ids": selected_document_ids,
                    "message": f"Stored {result.chunk_count} chunks in Qdrant collection '{result.collection_name}'.",
                },
            }
        )

    return JsonResponse({"status": "success", "data": {"existing_collections": existing_collections}})
