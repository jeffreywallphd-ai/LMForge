import types

import pytest

from studio.application.services.dataset_service import DatasetGenerationFailure, DatasetGenerationResult
from studio.application.workflows.dataset_generation import DatasetGenerationWorkflow


class _DatasetSvc:
    def __init__(self, result):
        self._result = result
        self.last_request = None
        self.last_persist = None

    def generate_dataset(self, request, *, model_name, persist_artifact):
        self.last_request = (request, model_name)
        self.last_persist = persist_artifact
        return self._result


class _ExportSvc:
    def as_json_text(self, data):
        return f"json:{len(data)}"

    def as_csv_text(self, rows):
        return f"csv:{len(rows)}"


def test_generate_raises_when_service_returns_failure():
    dataset = _DatasetSvc(
        DatasetGenerationResult(
            ok=False,
            failure=DatasetGenerationFailure(code="validation_error", message="At least one source document is required"),
        )
    )
    workflow = DatasetGenerationWorkflow(dataset_service=dataset, export_service=_ExportSvc())

    with pytest.raises(ValueError, match="At least one source document"):
        workflow.generate(document_ids=[])


def test_generate_uses_service_contract_and_exports():
    service_result = DatasetGenerationResult(
        ok=True,
        records=[{"question": "Q", "answer": "A"}],
        normalized_request=types.SimpleNamespace(document_ids=[1, 2], chunk_limit=1),
        chunk_count=3,
        processed_chunk_count=1,
        persisted_artifact={"artifact_id": 9},
    )
    dataset = _DatasetSvc(service_result)
    workflow = DatasetGenerationWorkflow(dataset_service=dataset, export_service=_ExportSvc())

    result = workflow.generate(
        document_ids=[1, 2],
        questions_per_chunk=0,
        chunk_limit=0,
        instruction_prompt="Follow",
        model_name="gpt2",
        persist_artifact=lambda *_: {"artifact_id": 9},
    )

    req, model_name = dataset.last_request
    assert req.questions_per_chunk == 0
    assert req.chunk_limit == 0
    assert req.instruction_prompt == "Follow"
    assert model_name == "gpt2"
    assert dataset.last_persist is not None
    assert result.json_text == "json:1"
    assert result.csv_text == "csv:1"
    assert result.document_count == 2
    assert result.chunk_count == 3
    assert result.processed_chunk_count == 1
    assert result.persisted_artifact == {"artifact_id": 9}


def test_list_documents_returns_pagination(monkeypatch):
    docs = [types.SimpleNamespace(id=i) for i in range(1, 6)]

    class _QS:
        def all(self):
            return self

        def order_by(self, _arg):
            return self

        def count(self):
            return len(docs)

        def __getitem__(self, slc):
            return docs[slc]

    monkeypatch.setattr(
        "studio.application.workflows.dataset_generation.SourceDocument.objects",
        _QS(),
    )

    workflow = DatasetGenerationWorkflow(dataset_service=_DatasetSvc(DatasetGenerationResult(ok=True)), export_service=_ExportSvc())
    page = workflow.list_documents(page=2, page_size=2)

    assert [item.id for item in page["items"]] == [3, 4]
    assert page["total_pages"] == 3
