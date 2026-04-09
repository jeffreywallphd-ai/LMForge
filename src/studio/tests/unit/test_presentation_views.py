from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from studio.presentation.api.views.scraping import remove_emojis
from studio.presentation.web.views import datasets as datasets_views
from studio.presentation.web.views import home as home_views
from studio.presentation.web.views import settings as settings_views


@pytest.fixture
def request_factory() -> RequestFactory:
    return RequestFactory()


def test_remove_emojis_strips_non_bmp() -> None:
    assert remove_emojis("Hello 😀 world 🌍") == "Hello  world "
    assert remove_emojis(None) == ""


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


def test_home_view_post_delete_collection_returns_success(request_factory, monkeypatch) -> None:
    request = request_factory.post(
        "/home/",
        data=json.dumps({"collection_name": "demo"}),
        content_type="application/json",
    )

    class FakeClient:
        def __init__(self, host: str, port: int) -> None:
            self.host = host
            self.port = port

        def delete_collection(self, collection_name: str) -> None:
            assert collection_name == "demo"

    monkeypatch.setattr(home_views, "QDRANT_AVAILABLE", True)
    monkeypatch.setattr(home_views, "QdrantClient", FakeClient)

    response = home_views.home_view(request)

    assert response.status_code == 200
    assert json.loads(response.content) == {"success": True}


def test_dataset_workflow_view_reads_and_clears_redirect_message(request_factory, monkeypatch) -> None:
    request = request_factory.get("/datasets/")
    request.session = {"redirect_message": "Done"}

    fake_qs = Mock()
    fake_qs.order_by.return_value = [SimpleNamespace(title="Doc")]

    meta_manager = Mock()
    meta_manager.all.return_value = fake_qs
    monkeypatch.setattr(datasets_views.ScrapedDataMeta, "objects", meta_manager)

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
