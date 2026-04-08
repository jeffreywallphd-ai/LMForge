import pytest

from src.studio.application.services.dataset_service import DatasetGenerationRequest, DatasetService


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
        "src.studio.application.services.dataset_service.SourceDocument.objects.filter",
        lambda **_kwargs: docs,
    )

    service = DatasetService(document_service=_DocSvc())
    assert service.get_documents_text([1, 2]) == "A\n\nB"


def test_generate_qa_pairs_skips_invalid_json_and_uses_chunk_limit(monkeypatch):
    service = DatasetService(document_service=_DocSvc())
    monkeypatch.setattr(service, "get_documents_text", lambda _ids: "text")

    outputs = iter(
        [
            "no json here",
            '[{"question": "q2", "answer": "a2"}]',
        ]
    )
    monkeypatch.setattr(service, "_model_chat", lambda *_a, **_k: next(outputs))

    request = DatasetGenerationRequest(document_ids=[1], questions_per_chunk=1, chunk_limit=2)
    result = service.generate_qa_pairs(request)

    assert result == [{"question": "q2", "answer": "a2"}]


def test_generate_qa_pairs_validates_request():
    service = DatasetService(document_service=_DocSvc())
    with pytest.raises(ValueError, match="At least one source document"):
        service.generate_qa_pairs(DatasetGenerationRequest(document_ids=[]))
