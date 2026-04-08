"""Application workflow: document ingestion.

This workflow lifts orchestration concerns out of legacy Django views while
preserving the service behavior implemented in ``DocumentService``.
"""

from __future__ import annotations

from dataclasses import dataclass

from studio.application.services.document_service import DocumentService, ScrapedPayload


@dataclass(slots=True)
class DocumentIngestionResult:
    """Result payload returned by the ingestion workflow."""

    title: str
    url: str
    file_type: str
    persisted_document_id: int | None
    content_preview: str


class DocumentIngestionWorkflow:
    """Coordinates scrape + persistence decisions for source ingestion."""

    def __init__(self, document_service: DocumentService | None = None) -> None:
        self.document_service = document_service or DocumentService()

    def scrape_only(self, *, url: str, title: str = "") -> ScrapedPayload:
        """Scrape and normalize a source without persisting it."""
        return self.document_service.scrape_generic_url(url=url, title=title)

    def scrape_and_persist(self, *, url: str, title: str = "") -> DocumentIngestionResult:
        """Scrape a document and persist it as a domain source document."""
        payload = self.scrape_only(url=url, title=title)
        persisted = self.document_service.persist_source_document(payload)

        return DocumentIngestionResult(
            title=payload.title,
            url=payload.url,
            file_type=payload.file_type,
            persisted_document_id=getattr(persisted, "id", None),
            content_preview=payload.content[:500],
        )
