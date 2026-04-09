"""Application service: source ingestion and chunk preparation."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from studio.domain.models import SourceDocument
from studio.infrastructure.scraping.generic_web import GenericWebScraper


EMOJI_RE = re.compile(r"[\U00010000-\U0010FFFF]")


@dataclass(slots=True)
class ScrapedPayload:
    url: str
    file_type: str
    title: str
    content: str


class DocumentService:
    """Service migrated from `lmforge_core.views.scrape` and dataset chunking flows."""

    max_title_length = 100
    max_url_title_length = 95

    def __init__(self, generic_web_scraper: GenericWebScraper | None = None) -> None:
        self.generic_web_scraper = generic_web_scraper or GenericWebScraper()

    def remove_emojis(self, text: str) -> str:
        return EMOJI_RE.sub("", text or "")

    def split_text(self, text: str, max_tokens: int = 1000, tokenizer: Any | None = None) -> list[str]:
        """Paragraph-based chunking compatible with legacy workflow behavior."""
        paragraphs = (text or "").split("\n\n")
        chunks: list[str] = []
        current_chunk: list[str] = []
        current_tokens = 0

        for paragraph in paragraphs:
            para_tokens = len(tokenizer.encode(paragraph)) if tokenizer else len(paragraph.split())
            if current_tokens + para_tokens > max_tokens and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [paragraph]
                current_tokens = para_tokens
            else:
                current_chunk.append(paragraph)
                current_tokens += para_tokens

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
        return [chunk for chunk in chunks if chunk.strip()]

    def scrape_generic_url(self, url: str, title: str = "") -> ScrapedPayload:
        parsed = self.generic_web_scraper.scrape(url)
        if not title.strip() and parsed.extracted_title:
            title = parsed.extracted_title

        final_title = (title or url[: self.max_url_title_length] or "scraped")[: self.max_title_length]
        return ScrapedPayload(
            url=url,
            file_type=parsed.file_type,
            title=final_title,
            content=self.remove_emojis(parsed.content),
        )

    def persist_source_document(self, payload: ScrapedPayload) -> SourceDocument:
        return SourceDocument.objects.create(
            url=payload.url,
            file_type=payload.file_type,
            content=payload.content,
            title=payload.title,
        )
