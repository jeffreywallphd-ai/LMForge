import pytest

from studio.application.services.dataset_service import DatasetGenerationRequest, DatasetService


class _DocSvc:
    def split_text(self, text, max_tokens=256):
        assert max_tokens == 256
        return ["chunk-1", "chunk-2"]


def test_build_prompt_includes_instruction_when_present():
    service = DatasetService(document_service=_DocSvc())
    prompt = service.build_prompt("abc", questions_num=2, instruction_prompt="Use concise style")
    assert '"instruction": "Use concise style"' in prompt


def test_get_documents_text_joins_content(monkeypatch):
    docs = [type("D", (), {"content": "A"})(), type("D", (), {"content": "B"})()]
    monkeypatch.setattr(
        "studio.application.services.dataset_service.SourceDocument.objects.filter",
        lambda **_kwargs: docs,
    )

    service = DatasetService(document_service=_DocSvc())
    assert service.get_documents_text([1, 2]) == "A\n\nB"


def test_generate_dataset_skips_invalid_json_and_normalizes_records(monkeypatch):
    service = DatasetService(document_service=_DocSvc())
    monkeypatch.setattr(service, "get_documents_text", lambda _ids: "text")

    outputs = iter(
        [
            "no json here",
            '[{"question": " q2 ", "answer": " a2 ", "unused": 1}]',
        ]
    )
    monkeypatch.setattr(service, "_model_chat", lambda *_a, **_k: next(outputs))

    request = DatasetGenerationRequest(document_ids=[1], questions_per_chunk=1, chunk_limit=2)
    result = service.generate_dataset(request)

    assert result.ok
    assert result.processed_chunk_count == 1
    assert result.chunk_count == 2
    assert result.records == [{"question": "q2", "answer": "a2"}]


def test_generate_dataset_normalizes_request_and_returns_validation_failure():
    service = DatasetService(document_service=_DocSvc())
    result = service.generate_dataset(DatasetGenerationRequest(document_ids=[]))

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "validation_error"
    assert "At least one source document" in result.failure.message


def test_generate_dataset_supports_explicit_persistence_handoff(monkeypatch):
    service = DatasetService(document_service=_DocSvc())
    monkeypatch.setattr(service, "get_documents_text", lambda _ids: "text")
    monkeypatch.setattr(
        service,
        "_model_chat",
        lambda *_a, **_k: '[{"question": "Q?", "answer": "A."}]',
    )

    observed = {}

    def _persist(records, normalized_request):
        observed["records"] = records
        observed["doc_ids"] = normalized_request.document_ids
        return {"artifact_id": 101, "record_count": len(records)}

    result = service.generate_dataset(
        DatasetGenerationRequest(document_ids=[3, 2, 2], questions_per_chunk=1, chunk_limit=1),
        persist_artifact=_persist,
    )

    assert result.ok
    assert observed["doc_ids"] == [2, 3]
    assert observed["records"] == [{"question": "Q?", "answer": "A."}]
    assert result.persisted_artifact == {"artifact_id": 101, "record_count": 1}


def test_generate_qa_pairs_raises_on_invalid_request():
    service = DatasetService(document_service=_DocSvc())
    with pytest.raises(ValueError, match="At least one source document"):
        service.generate_qa_pairs(DatasetGenerationRequest(document_ids=[]))
