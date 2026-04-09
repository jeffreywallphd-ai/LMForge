from __future__ import annotations

from django.shortcuts import render

from studio.application.services.scraping_service import ScrapeRequest, ScrapingService
from studio.domain.models import SourceDocument


def scrape_view(request):
    scraping_service = ScrapingService()
    latest = SourceDocument.objects.order_by("-created_at").first()

    context: dict[str, object] = {
        "latest_scraped_data": latest,
        "scrape_result": None,
        "scrape_error": None,
    }

    if request.method == "POST":
        service_result = scraping_service.execute(
            ScrapeRequest(
                url=request.POST.get("url", ""),
                title=request.POST.get("title", ""),
                source_type=request.POST.get("source_type", "generic"),
            )
        )

        if service_result.ok and service_result.data:
            context["scrape_result"] = {
                "url": service_result.data.url,
                "title": service_result.data.title,
                "file_type": service_result.data.file_type,
                "content": service_result.data.content,
            }
        elif service_result.error:
            context["scrape_error"] = service_result.error.message

    return render(request, "web/pages/scraping/scrape.html", context)
