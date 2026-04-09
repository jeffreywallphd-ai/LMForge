from django.shortcuts import render

from studio.models import SourceDocument as ScrapedData


def scrape_view(request):
    latest = ScrapedData.objects.order_by("-created_at").first()
    return render(request, "scrape.html", {"latest_scraped_data": latest})
