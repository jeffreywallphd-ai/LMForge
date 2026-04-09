from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from studio.presentation.web.views import datasets as datasets_views
from studio.presentation.web.views import home as home_views
from studio.presentation.web.views import scraping as scraping_views
from studio.presentation.web.views import settings as settings_views


@pytest.fixture
def request_factory() -> RequestFactory:
    return RequestFactory()


def test_home_view_adds_configuration_message_when_hf_account_missing(request_factory, monkeypatch) -> None:
    request = request_factory.get("/home/")

    monkeypatch.setattr(home_views, "DEFAULT_HF_ACCOUNT", None)
    monkeypatch.setattr(home_views, "QDRANT_AVAILABLE", False)

    captured = {}

    def fake_render(_request, _template, context):
        captured.update(context)
        return HttpResponse("ok")

    monkeypatch.setattr(home_views, "render", fake_render)

    response = home_views.home_view(request)

    assert response.status_code == 200
    assert any("configured the software" in msg for msg in captured["messages"])
    assert any("Qdrant not installed" in msg for msg in captured["messages"])


def test_home_view_post_delete_collection_adds_success_message(request_factory, monkeypatch) -> None:
    request = request_factory.post(
        "/home/",
        data={"collection_name": "demo"},
    )

    class FakeClient:
        def __init__(self, host: str, port: int) -> None:
            self.host = host
            self.port = port

        def delete_collection(self, collection_name: str) -> None:
            assert collection_name == "demo"

    monkeypatch.setattr(home_views, "DEFAULT_HF_ACCOUNT", None)
    monkeypatch.setattr(home_views, "QDRANT_AVAILABLE", True)
    monkeypatch.setattr(home_views, "QdrantClient", FakeClient)
    monkeypatch.setattr(
        home_views,
        "render",
        lambda _request, _template, context: HttpResponse("|".join(context["messages"])),
    )

    response = home_views.home_view(request)

    assert response.status_code == 200
    assert "Collection 'demo' deleted." in response.content.decode()


def test_dataset_workflow_view_reads_and_clears_redirect_message(request_factory, monkeypatch) -> None:
    request = request_factory.get("/datasets/")
    request.session = {"redirect_message": "Done"}

    fake_qs = Mock()
    fake_qs.order_by.return_value = [SimpleNamespace(title="Doc")]

    meta_manager = Mock()
    meta_manager.all.return_value = fake_qs
    monkeypatch.setattr(datasets_views.SourceDocumentMetadata, "objects", meta_manager)

    captured = {}

    def fake_render(_request, _template, context):
        captured.update(context)
        return HttpResponse("ok")

    monkeypatch.setattr(datasets_views, "render", fake_render)

    response = datasets_views.dataset_workflow_view(request)

    assert response.status_code == 200
    assert captured["messages"] == ["Done"]
    assert "redirect_message" not in request.session


def test_settings_view_reads_existing_env_values(request_factory, tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("HF_API_KEY=abc\nOPENAI_API_KEY=xyz\n", encoding="utf-8")

    monkeypatch.setattr(settings_views.settings, "BASE_DIR", str(tmp_path))

    captured = {}

    def fake_render(_request, _template, context):
        captured.update(context)
        return HttpResponse("ok")

    monkeypatch.setattr(settings_views, "render", fake_render)

    request = request_factory.get("/settings/")
    response = settings_views.settings_view(request)

    assert response.status_code == 200
    assert captured["existing_values"]["HF_API_KEY"] == "abc"
    assert captured["existing_values"]["OPENAI_API_KEY"] == "xyz"


def test_settings_view_post_preserves_existing_values_for_blank_inputs(request_factory, tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("HF_API_KEY=old_hf\nOPENAI_API_KEY=old_openai\n", encoding="utf-8")

    monkeypatch.setattr(settings_views.settings, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(settings_views, "render", lambda *_args, **_kwargs: HttpResponse("ok"))

    request = request_factory.post(
        "/settings/",
        data={
            "HF_API_KEY": "",
            "OPENAI_API_KEY": "new_openai",
        },
    )

    response = settings_views.settings_view(request)

    assert response.status_code == 200
    written = env_path.read_text(encoding="utf-8")
    assert "HF_API_KEY=old_hf" in written
    assert "OPENAI_API_KEY=new_openai" in written


def test_scrape_view_get_renders_latest_record(request_factory, monkeypatch) -> None:
    request = request_factory.get("/scraping/")

    fake_qs = Mock()
    fake_qs.first.return_value = SimpleNamespace(title="Latest")
    monkeypatch.setattr(scraping_views.SourceDocument.objects, "order_by", lambda *_a, **_k: fake_qs)

    captured = {}

    def fake_render(_request, _template, context):
        captured.update(context)
        return HttpResponse("ok")

    monkeypatch.setattr(scraping_views, "render", fake_render)

    response = scraping_views.scrape_view(request)

    assert response.status_code == 200
    assert captured["latest_scraped_data"].title == "Latest"
    assert captured["scrape_result"] is None


def test_scrape_view_post_maps_service_success_to_template_context(request_factory, monkeypatch) -> None:
    request = request_factory.post(
        "/scraping/",
        data={"url": "https://example.com", "title": "Example", "source_type": "generic"},
    )

    fake_qs = Mock()
    fake_qs.first.return_value = None
    monkeypatch.setattr(scraping_views.SourceDocument.objects, "order_by", lambda *_a, **_k: fake_qs)

    class _FakeService:
        def execute(self, _req):
            return SimpleNamespace(
                ok=True,
                data=SimpleNamespace(url="https://example.com", title="Example", file_type="html", content="Hello"),
                error=None,
            )

    monkeypatch.setattr(scraping_views, "ScrapingService", _FakeService)

    captured = {}
    monkeypatch.setattr(
        scraping_views,
        "render",
        lambda _request, _template, context: captured.update(context) or HttpResponse("ok"),
    )

    response = scraping_views.scrape_view(request)

    assert response.status_code == 200
    assert captured["scrape_result"]["url"] == "https://example.com"
    assert captured["scrape_error"] is None
