from __future__ import annotations

import types

from django.test import RequestFactory
from rest_framework.test import APIRequestFactory



def test_scraping_api_contract_stays_json(monkeypatch) -> None:
    from studio.presentation.api.views import scraping as api_scraping

    class _FakeService:
        def execute(self, _request):
            return types.SimpleNamespace(
                ok=True,
                data=types.SimpleNamespace(
                    document_id=7,
                    url="https://example.com",
                    title="Example",
                    file_type="html",
                    content="ok",
                ),
                error=None,
            )

    monkeypatch.setattr(api_scraping, "ScrapingService", _FakeService)

    request = APIRequestFactory().post(
        "/api/scrape/",
        {"url": "https://example.com", "title": "Example", "source_type": "generic"},
        format="json",
    )
    response = api_scraping.ScrapeDataView.as_view()(request)

    assert response.status_code == 200
    assert response.data["status"] == "success"


def test_scraping_web_flow_stays_template_oriented(monkeypatch) -> None:
    from studio.presentation.web.views import scraping as web_scraping

    class _FakeService:
        def execute(self, _request):
            return types.SimpleNamespace(
                ok=True,
                data=types.SimpleNamespace(
                    url="https://example.com",
                    title="Example",
                    file_type="html",
                    content="ok",
                ),
                error=None,
            )

    class _FakeQuerySet:
        def first(self):
            return None

    monkeypatch.setattr(web_scraping, "ScrapingService", _FakeService)
    monkeypatch.setattr(web_scraping.SourceDocument.objects, "order_by", lambda *_a, **_k: _FakeQuerySet())

    request = RequestFactory().post(
        "/scraping/",
        data={"url": "https://example.com", "title": "Example", "source_type": "generic"},
    )
    response = web_scraping.scrape_view(request)

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/html")
    assert "Document saved from https://example.com" in response.content.decode()


def test_scraping_web_flow_maps_service_errors_to_template_feedback(monkeypatch) -> None:
    from studio.presentation.web.views import scraping as web_scraping

    class _FakeService:
        def execute(self, _request):
            return types.SimpleNamespace(
                ok=False,
                data=None,
                error=types.SimpleNamespace(code="validation_error", message="Please provide a URL."),
            )

    class _FakeQuerySet:
        def first(self):
            return None

    monkeypatch.setattr(web_scraping, "ScrapingService", _FakeService)
    monkeypatch.setattr(web_scraping.SourceDocument.objects, "order_by", lambda *_a, **_k: _FakeQuerySet())

    request = RequestFactory().post(
        "/scraping/",
        data={"url": "", "title": "", "source_type": "generic"},
    )
    response = web_scraping.scrape_view(request)

    assert response.status_code == 200
    assert "Please provide a URL." in response.content.decode()
