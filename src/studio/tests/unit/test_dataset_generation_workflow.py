import types

import pytest

from studio.application.workflows.dataset_generation import DatasetGenerationWorkflow


class _DatasetSvc:
    def __init__(self, records):
        self._records = records
        self.last_request = None

    def generate_qa_pairs(self, request, *, model_name):
        self.last_request = (request, model_name)
        return self._records


class _ExportSvc:
    def as_json_text(self, data):
        return f"json:{len(data)}"

    def as_csv_text(self, rows):
        return f"csv:{len(rows)}"


def test_generate_requires_document_ids():
    workflow = DatasetGenerationWorkflow(dataset_service=_DatasetSvc([]), export_service=_ExportSvc())
    with pytest.raises(ValueError, match="At least one document"):
        workflow.generate(document_ids=[])


def test_generate_builds_request_and_exports():
    dataset = _DatasetSvc([{"q": "a"}])
    workflow = DatasetGenerationWorkflow(dataset_service=dataset, export_service=_ExportSvc())

    result = workflow.generate(
        document_ids=[1, 2],
        questions_per_chunk=0,
        chunk_limit=0,
        instruction_prompt="Follow",
        model_name="gpt2",
    )

    req, model_name = dataset.last_request
    assert req.questions_per_chunk == 1
    assert req.chunk_limit == 1
    assert req.instruction_prompt == "Follow"
    assert model_name == "gpt2"
    assert result.json_text == "json:1"
    assert result.csv_text == "csv:1"
    assert result.document_count == 2


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

    workflow = DatasetGenerationWorkflow(dataset_service=_DatasetSvc([]), export_service=_ExportSvc())
    page = workflow.list_documents(page=2, page_size=2)

    assert [item.id for item in page["items"]] == [3, 4]
    assert page["total_pages"] == 3
