import types

from src.studio.application.services.dataset_service import DatasetGenerationRequest, DatasetService
from src.studio.application.services.document_service import DocumentService
from src.studio.application.workflows.dataset_generation import DatasetGenerationWorkflow
from src.studio.application.workflows.document_ingestion import DocumentIngestionWorkflow


class _Parsed:
    extracted_title = "from-page"
    file_type = "html"
    content = "first 😀 paragraph\n\nsecond paragraph"


class _Scraper:
    def scrape(self, _url):
        return _Parsed()


def test_document_ingestion_and_dataset_generation_integration(monkeypatch):
    # Ingest scraped payload through the real service/workflow boundary.
    created_docs = []

    def _create(**kwargs):
        obj = types.SimpleNamespace(id=42, **kwargs)
        created_docs.append(obj)
        return obj

    monkeypatch.setattr(
        "src.studio.application.services.document_service.SourceDocument.objects.create",
        _create,
    )

    document_service = DocumentService(generic_web_scraper=_Scraper())
    ingest = DocumentIngestionWorkflow(document_service=document_service)
    ingest_result = ingest.scrape_and_persist(url="https://example.com", title="")

    assert ingest_result.persisted_document_id == 42
    assert created_docs[0].title == "from-page"
    assert "😀" not in created_docs[0].content

    # Generate dataset via workflow using the stored document content path.
    dataset_service = DatasetService(document_service=document_service)

    monkeypatch.setattr(
        "src.studio.application.services.dataset_service.SourceDocument.objects.filter",
        lambda **_kwargs: created_docs,
    )
    monkeypatch.setattr(
        dataset_service,
        "_model_chat",
        lambda *_a, **_k: '[{"question":"Q?","answer":"A."}]',
    )

    workflow = DatasetGenerationWorkflow(dataset_service=dataset_service)
    result = workflow.generate(document_ids=[42], questions_per_chunk=1, chunk_limit=1, model_name="gpt2")

    assert len(result.records) == 1
    assert result.records[0]["question"] == "Q?"
    assert "Q?" in result.json_text
