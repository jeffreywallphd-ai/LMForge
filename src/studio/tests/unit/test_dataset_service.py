from __future__ import annotations

import pytest

from studio.application.services.dataset_service import DatasetGenerationRequest, DatasetService


class _DocSvc:
    def split_text(self, text, max_tokens=256):
        assert text == "text"
        assert max_tokens == 256
        return ["chunk-1", "chunk-2", "chunk-3"]


def test_normalize_request_cleans_and_coerces_fields():
    service = DatasetService(document_service=_DocSvc())

    normalized = service.normalize_request(
        DatasetGenerationRequest(
            document_ids=["4", 4, -1, "2"],
            questions_per_chunk=0,
            chunk_limit=-5,
            instruction_prompt="  be concise  ",
        )
    )

    assert normalized.document_ids == [2, 4]
    assert normalized.questions_per_chunk == 1
    assert normalized.chunk_limit == 1
    assert normalized.instruction_prompt == "be concise"


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


def test_generate_dataset_returns_normalized_records_and_chunk_metrics(monkeypatch):
    service = DatasetService(document_service=_DocSvc())
    monkeypatch.setattr(service, "get_documents_text", lambda _ids: "text")

    outputs = iter(
        [
            "no json here",
            '[{"question": " q2 ", "answer": " a2 ", "unused": 1}]',
            '[{"question": " ", "answer": "ignored"}]',
        ]
    )
    monkeypatch.setattr(service, "_model_chat", lambda *_a, **_k: next(outputs))

    request = DatasetGenerationRequest(document_ids=[1], questions_per_chunk=1, chunk_limit=3)
    result = service.generate_dataset(request)

    assert result.ok
    assert result.processed_chunk_count == 2
    assert result.chunk_count == 3
    assert result.records == [{"question": "q2", "answer": "a2"}]
    assert result.failure is None


def test_generate_dataset_returns_validation_failure():
    service = DatasetService(document_service=_DocSvc())

    result = service.generate_dataset(DatasetGenerationRequest(document_ids=[]))

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "validation_error"
    assert "At least one source document" in result.failure.message


def test_generate_dataset_returns_execution_failure_when_model_collaborator_raises(monkeypatch):
    service = DatasetService(document_service=_DocSvc())
    monkeypatch.setattr(service, "get_documents_text", lambda _ids: "text")
    monkeypatch.setattr(service, "_model_chat", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("llm down")))

    result = service.generate_dataset(DatasetGenerationRequest(document_ids=[7], questions_per_chunk=1, chunk_limit=1))

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "execution_error"
    assert "llm down" in result.failure.message


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


def test_generate_dataset_returns_persistence_failure_when_handoff_raises(monkeypatch):
    service = DatasetService(document_service=_DocSvc())
    monkeypatch.setattr(service, "get_documents_text", lambda _ids: "text")
    monkeypatch.setattr(service, "_model_chat", lambda *_a, **_k: '[{"question": "Q", "answer": "A"}]')

    def _persist(_records, _normalized_request):
        raise RuntimeError("db unavailable")

    result = service.generate_dataset(
        DatasetGenerationRequest(document_ids=[1], questions_per_chunk=1, chunk_limit=1),
        persist_artifact=_persist,
    )

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "persistence_error"
    assert "db unavailable" in result.failure.message


def test_generate_qa_pairs_raises_on_invalid_request():
    service = DatasetService(document_service=_DocSvc())
    with pytest.raises(ValueError, match="At least one source document"):
        service.generate_qa_pairs(DatasetGenerationRequest(document_ids=[]))
