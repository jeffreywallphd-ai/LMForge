from __future__ import annotations

import json
from types import SimpleNamespace

from django.test import RequestFactory

from studio.presentation.api.views import datasets as dataset_views


class _FakeEmbeddingWorkflow:
    def __init__(self, run_result):
        self.run_result = run_result
        self.run_request = None

    def list_collections(self, *, host: str = "localhost", port: int = 6333):
        return [f"{host}:{port}", "docs"]

    def fetch_collection_chunks(self, *, collection_name: str, host: str = "localhost", port: int = 6333, batch_size: int = 100):
        return [f"{collection_name}:{batch_size}"]

    def run(self, request):
        self.run_request = request
        return self.run_result


def _json(response):
    return json.loads(response.content.decode())


def test_database_workflow_post_delegates_orchestration_to_embedding_workflow(monkeypatch):
    fake_workflow = _FakeEmbeddingWorkflow(
        SimpleNamespace(
            ok=True,
            collection_name="docs",
            chunk_count=2,
            stored=True,
            failure=None,
        )
    )
    monkeypatch.setattr(dataset_views, "get_embedding_workflow", lambda: fake_workflow)

    request = RequestFactory().post(
        "/api/database_workflow/",
        data={
            "selected_documents": ["10", "11"],
            "new_collection_name": "docs",
        },
    )

    response = dataset_views.database_workflow(request)
    body = _json(response)

    assert response.status_code == 200
    assert body["status"] == "success"
    assert body["data"]["total_chunks"] == 2
    assert fake_workflow.run_request.document_ids == [10, 11]
    assert fake_workflow.run_request.collection_name == "docs"


def test_database_workflow_maps_workflow_validation_failure(monkeypatch):
    fake_workflow = _FakeEmbeddingWorkflow(
        SimpleNamespace(
            ok=False,
            collection_name="",
            chunk_count=0,
            stored=False,
            failure=SimpleNamespace(code="validation_error", message="Please select or enter a collection name."),
        )
    )
    monkeypatch.setattr(dataset_views, "get_embedding_workflow", lambda: fake_workflow)

    request = RequestFactory().post(
        "/api/database_workflow/",
        data={
            "selected_documents": ["9"],
            "new_collection_name": "",
            "collection_name": "",
        },
    )

    response = dataset_views.database_workflow(request)
    body = _json(response)

    assert response.status_code == 400
    assert body["status"] == "error"
    assert body["error"]["code"] == "validation_error"


def test_database_workflow_get_chunks_uses_workflow_fetch(monkeypatch):
    fake_workflow = _FakeEmbeddingWorkflow(
        SimpleNamespace(ok=True, collection_name="docs", chunk_count=0, stored=True, failure=None)
    )
    monkeypatch.setattr(dataset_views, "get_embedding_workflow", lambda: fake_workflow)

    request = RequestFactory().get("/api/database_workflow/?collection_name=docs")

    response = dataset_views.database_workflow(request)
    body = _json(response)

    assert response.status_code == 200
    assert body["chunks"] == ["docs:100"]
