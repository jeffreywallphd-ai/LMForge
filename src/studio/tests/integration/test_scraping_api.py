from __future__ import annotations

import types

from rest_framework.test import APIRequestFactory


def test_scrape_api_success_returns_stable_json_contract(monkeypatch) -> None:
    from studio.presentation.api.views import scraping as scraping_views

    class _FakeService:
        def execute(self, _request):
            return types.SimpleNamespace(
                ok=True,
                data=types.SimpleNamespace(
                    document_id=9,
                    url="https://example.com",
                    title="Example",
                    file_type="html",
                    content="hello",
                ),
                error=None,
            )

    monkeypatch.setattr(scraping_views, "ScrapingService", _FakeService)

    request = APIRequestFactory().post(
        "/api/scrape/",
        {"url": "https://example.com", "title": "Example", "source_type": "generic"},
        format="json",
    )
    response = scraping_views.ScrapeDataView.as_view()(request)

    assert response.status_code == 200
    assert response.data == {
        "status": "success",
        "data": {
            "document_id": 9,
            "url": "https://example.com",
            "title": "Example",
            "file_type": "html",
            "content": "hello",
        },
    }


def test_scrape_api_supports_get_querystring_contract(monkeypatch) -> None:
    from studio.presentation.api.views import scraping as scraping_views

    class _FakeService:
        def execute(self, request):
            assert request.url == "https://example.com"
            assert request.title == "From query"
            assert request.source_type == "generic"
            return types.SimpleNamespace(
                ok=True,
                data=types.SimpleNamespace(
                    document_id=2,
                    url=request.url,
                    title=request.title,
                    file_type="html",
                    content="query payload",
                ),
                error=None,
            )

    monkeypatch.setattr(scraping_views, "ScrapingService", _FakeService)

    request = APIRequestFactory().get(
        "/api/scrape/?url=https://example.com&title=From+query&source_type=generic"
    )
    response = scraping_views.ScrapeDataView.as_view()(request)

    assert response.status_code == 200
    assert response.data["status"] == "success"
    assert response.data["data"]["title"] == "From query"


def test_scrape_api_validation_failure_returns_validation_contract(monkeypatch) -> None:
    from studio.presentation.api.views import scraping as scraping_views

    class _FakeService:
        def execute(self, _request):
            return types.SimpleNamespace(
                ok=False,
                data=None,
                error=types.SimpleNamespace(code="validation_error", message="Please provide a URL."),
            )

    monkeypatch.setattr(scraping_views, "ScrapingService", _FakeService)

    request = APIRequestFactory().post("/api/scrape/", {"url": ""}, format="json")
    response = scraping_views.ScrapeDataView.as_view()(request)

    assert response.status_code == 400
    assert response.data == {
        "status": "error",
        "error": {
            "code": "validation_error",
            "message": "Please provide a URL.",
        },
    }


def test_scrape_api_upstream_error_maps_to_gateway_error(monkeypatch) -> None:
    from studio.presentation.api.views import scraping as scraping_views

    class _FakeService:
        def execute(self, _request):
            return types.SimpleNamespace(
                ok=False,
                data=None,
                error=types.SimpleNamespace(code="upstream_error", message="boom"),
            )

    monkeypatch.setattr(scraping_views, "ScrapingService", _FakeService)

    request = APIRequestFactory().post("/api/scrape/", {"url": "https://example.com"}, format="json")
    response = scraping_views.ScrapeDataView.as_view()(request)

    assert response.status_code == 502
    assert response.data == {
        "status": "error",
        "error": {
            "code": "scrape_failed",
            "message": "boom",
        },
    }


def test_scrape_api_unexpected_error_maps_to_internal_error(monkeypatch) -> None:
    from studio.presentation.api.views import scraping as scraping_views

    class _FakeService:
        def execute(self, _request):
            return types.SimpleNamespace(
                ok=False,
                data=None,
                error=types.SimpleNamespace(code="unexpected_error", message="unexpected"),
            )

    monkeypatch.setattr(scraping_views, "ScrapingService", _FakeService)

    request = APIRequestFactory().post("/api/scrape/", {"url": "https://example.com"}, format="json")
    response = scraping_views.ScrapeDataView.as_view()(request)

    assert response.status_code == 500
    assert response.data == {
        "status": "error",
        "error": {
            "code": "scrape_unexpected_failure",
            "message": "unexpected",
        },
    }
