from __future__ import annotations

import types

from studio.application.services.document_service import ScrapedPayload
from studio.application.services.scraping_service import ScrapeRequest, ScrapingService


class _FakeDocumentService:
    max_title_length = 100

    def __init__(self) -> None:
        self.scrape_called_with: tuple[str, str] | None = None
        self.persisted: ScrapedPayload | None = None

    def scrape_generic_url(self, url: str, title: str = "") -> ScrapedPayload:
        self.scrape_called_with = (url, title)
        return ScrapedPayload(url=url, file_type="html", title=title or "from-page", content="content")

    def persist_source_document(self, payload: ScrapedPayload):
        self.persisted = payload
        return types.SimpleNamespace(id=123)

    def remove_emojis(self, text: str) -> str:
        return text.replace("😀", "")


class _FakeRedditScraper:
    def scrape(self, _url: str):
        return types.SimpleNamespace(file_type="reddit_post", extracted_title="reddit-title", content="hello 😀")


def test_scraping_service_returns_validation_error_for_missing_url() -> None:
    service = ScrapingService(document_service=_FakeDocumentService(), reddit_scraper=_FakeRedditScraper())

    result = service.execute(ScrapeRequest(url="", title="x", source_type="generic"))

    assert result.ok is False
    assert result.error is not None
    assert result.error.code == "validation_error"


def test_scraping_service_scrapes_generic_and_persists() -> None:
    document_service = _FakeDocumentService()
    service = ScrapingService(document_service=document_service, reddit_scraper=_FakeRedditScraper())

    result = service.execute(ScrapeRequest(url=" https://example.com ", title="  Example  ", source_type="generic"))

    assert result.ok is True
    assert result.data is not None
    assert result.data.document_id == 123
    assert document_service.scrape_called_with == ("https://example.com", "Example")
    assert document_service.persisted is not None


def test_scraping_service_uses_reddit_scraper_path_and_normalizes_content() -> None:
    document_service = _FakeDocumentService()
    service = ScrapingService(document_service=document_service, reddit_scraper=_FakeRedditScraper())

    result = service.execute(ScrapeRequest(url="https://reddit.com/r/test", title="", source_type="reddit"))

    assert result.ok is True
    assert result.data is not None
    assert result.data.file_type == "reddit_post"
    assert result.data.title == "reddit-title"
    assert "😀" not in result.data.content
