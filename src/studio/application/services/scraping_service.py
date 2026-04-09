"""Application service for scraping orchestration across API and web surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlparse

from studio.application.services.document_service import DocumentService, ScrapedPayload
from studio.infrastructure.scraping.reddit import RedditScraper

ScrapeSourceType = Literal["generic", "reddit"]
ScrapeErrorCode = Literal["validation_error", "upstream_error", "unexpected_error"]


@dataclass(slots=True)
class ScrapeRequest:
    """Normalized input contract for scraping requests."""

    url: str
    title: str = ""
    source_type: ScrapeSourceType = "generic"


@dataclass(slots=True)
class ScrapeSuccessData:
    """Service success payload shared by API and web adapters."""

    document_id: int
    url: str
    title: str
    file_type: str
    content: str


@dataclass(slots=True)
class ScrapeErrorData:
    """Service error payload used by presentation adapters."""

    code: ScrapeErrorCode
    message: str


@dataclass(slots=True)
class ScrapeResult:
    """Outcome envelope returned by the scraping service."""

    ok: bool
    data: ScrapeSuccessData | None = None
    error: ScrapeErrorData | None = None


class ScrapingService:
    """Orchestrates scraping + persistence while hiding infrastructure details."""

    allowed_source_types: tuple[ScrapeSourceType, ...] = ("generic", "reddit")

    def __init__(
        self,
        *,
        document_service: DocumentService | None = None,
        reddit_scraper: RedditScraper | None = None,
    ) -> None:
        self.document_service = document_service or DocumentService()
        self.reddit_scraper = reddit_scraper or RedditScraper()

    def execute(self, request: ScrapeRequest) -> ScrapeResult:
        normalized = self._normalize_and_validate(request)
        if isinstance(normalized, ScrapeResult):
            return normalized

        try:
            if normalized.source_type == "reddit":
                payload = self._scrape_reddit(normalized.url, normalized.title)
            else:
                payload = self.document_service.scrape_generic_url(url=normalized.url, title=normalized.title)

            persisted = self.document_service.persist_source_document(payload)
            return ScrapeResult(
                ok=True,
                data=ScrapeSuccessData(
                    document_id=getattr(persisted, "id", 0),
                    url=payload.url,
                    title=payload.title,
                    file_type=payload.file_type,
                    content=payload.content,
                ),
            )
        except ValueError as exc:
            return ScrapeResult(ok=False, error=ScrapeErrorData(code="validation_error", message=str(exc)))
        except RuntimeError as exc:
            return ScrapeResult(ok=False, error=ScrapeErrorData(code="upstream_error", message=str(exc)))
        except Exception as exc:  # noqa: BLE001
            return ScrapeResult(ok=False, error=ScrapeErrorData(code="unexpected_error", message=str(exc)))

    def _normalize_and_validate(self, request: ScrapeRequest) -> ScrapeRequest | ScrapeResult:
        url = (request.url or "").strip()
        title = (request.title or "").strip()
        source_type = (request.source_type or "generic").strip().lower()

        if not url:
            return ScrapeResult(
                ok=False,
                error=ScrapeErrorData(code="validation_error", message="Please provide a URL."),
            )

        if source_type not in self.allowed_source_types:
            allowed = ", ".join(self.allowed_source_types)
            return ScrapeResult(
                ok=False,
                error=ScrapeErrorData(
                    code="validation_error",
                    message=f"Unsupported source_type '{source_type}'. Allowed values: {allowed}.",
                ),
            )

        if not self._is_http_url(url):
            return ScrapeResult(
                ok=False,
                error=ScrapeErrorData(
                    code="validation_error",
                    message="Please provide a valid http(s) URL.",
                ),
            )

        if source_type == "reddit" and not self._is_reddit_url(url):
            return ScrapeResult(
                ok=False,
                error=ScrapeErrorData(
                    code="validation_error",
                    message="Reddit scraping requires a reddit.com URL.",
                ),
            )

        return ScrapeRequest(url=url, title=title, source_type=source_type)

    def _scrape_reddit(self, url: str, title: str) -> ScrapedPayload:
        reddit_result = self.reddit_scraper.scrape(url)
        return self._build_payload(url, title, reddit_result)

    def _build_payload(self, url: str, title: str, reddit_result: Any) -> ScrapedPayload:
        final_title = title or reddit_result.extracted_title or url
        content = self.document_service.remove_emojis(reddit_result.content)
        return ScrapedPayload(
            url=url,
            file_type=reddit_result.file_type,
            title=final_title[: self.document_service.max_title_length],
            content=content,
        )

    @staticmethod
    def _is_http_url(url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    @staticmethod
    def _is_reddit_url(url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return "reddit.com" in host
