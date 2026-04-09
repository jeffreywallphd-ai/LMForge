from __future__ import annotations

import json
import logging

import markdown
import pdfplumber
from rest_framework import status
from rest_framework.request import Request
from rest_framework.views import APIView

from studio.application.services.scraping_service import ScrapeRequest, ScrapingService
from studio.models import SourceDocument as ScrapedData
from studio.presentation.api.response_contracts import error_response, success_response, validation_error_response

logger = logging.getLogger(__name__)
MAX_TITLE_LENGTH = 100


class ScrapeDataView(APIView):
    """Machine-facing JSON endpoint for URL scraping."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scraping_service = ScrapingService()

    def get(self, request: Request):
        return self._handle(request)

    def post(self, request: Request):
        return self._handle(request)

    def _handle(self, request: Request):
        payload = request.data if hasattr(request, "data") and request.data else request.query_params
        result = self.scraping_service.execute(
            ScrapeRequest(
                url=str(payload.get("url", "")),
                title=str(payload.get("title", "")),
                source_type=str(payload.get("source_type", "generic")),
            )
        )

        if result.ok and result.data:
            return success_response(
                {
                    "document_id": result.data.document_id,
                    "url": result.data.url,
                    "title": result.data.title,
                    "file_type": result.data.file_type,
                    "content": result.data.content,
                }
            )

        if result.error and result.error.code == "validation_error":
            return validation_error_response(result.error.message)

        if result.error and result.error.code == "unexpected_error":
            return error_response(
                result.error.message,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                code="scrape_unexpected_failure",
            )

        message = result.error.message if result.error else "Unexpected scraping failure."
        return error_response(
            message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="scrape_failed",
        )


class UploadPDFView(APIView):
    """Upload a PDF and convert it to text/html/json as requested."""

    def post(self, request: Request):
        pdf_file = request.FILES.get("pdf_file")
        output_format = request.POST.get("output_format") or request.data.get("output_format") or "text"
        title = request.POST.get("title") or request.data.get("title") or (getattr(pdf_file, "name", "") if pdf_file else "uploaded_pdf")

        if not pdf_file:
            return validation_error_response("No PDF file uploaded")

        try:
            text_parts = []
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    text_parts.append(page.extract_text() or "")
            text = "\n\n".join([t for t in text_parts if t])

            if output_format == "html":
                content = markdown.markdown(text)
                file_type = "html"
            elif output_format == "json":
                content = json.dumps({"text": text}, indent=2)
                file_type = "json"
            else:
                content = text
                file_type = "text"

            scraped_record: ScrapedData = ScrapedData.objects.create(
                url="https://local/uploaded_pdf",
                file_type=file_type,
                content=content,
                title=title[:MAX_TITLE_LENGTH],
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("PDF conversion failed: %s", exc)
            return error_response("Failed to convert PDF", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, code="conversion_failed")

        return success_response(
            {
                "message": "PDF converted and saved",
                "id": scraped_record.id,
                "file_type": scraped_record.file_type,
                "content": scraped_record.content,
            }
        )


class SaveManualTextView(APIView):
    """Save manually entered text to ScrapedData."""

    def post(self, request: Request):
        text: str | None = request.data.get("text") or request.POST.get("text")
        title: str = request.data.get("title") or request.POST.get("title") or "manual"

        if not text:
            return validation_error_response("No text provided")

        try:
            scraped_record: ScrapedData = ScrapedData.objects.create(
                url="https://local/manual",
                file_type="text",
                content=text,
                title=title[:MAX_TITLE_LENGTH],
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to save manual text: %s", exc)
            return error_response("Failed to save text", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, code="save_failed")

        return success_response(
            {
                "message": "Text saved",
                "id": scraped_record.id,
                "file_type": scraped_record.file_type,
                "content": scraped_record.content,
            }
        )
