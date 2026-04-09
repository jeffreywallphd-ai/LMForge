from __future__ import annotations

import re
from pathlib import Path

from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.test import RequestFactory

TEMPLATES_ROOT = Path(__file__).resolve().parents[3] / "studio" / "presentation" / "web" / "templates" / "web"
STATIC_ROOT = Path(__file__).resolve().parents[3] / "studio" / "presentation" / "web" / "static" / "web"


PAGE_TEMPLATE_PATHS = {
    "chatbot_view": "web/pages/chat/chatbot.html",
    "dataset_workflow_view": "web/pages/datasets/workflow.html",
    "dataset_workflow_document_processor": "web/pages/datasets/document_upload.html",
    "model_statistics_view": "web/pages/evaluation/model_statistics.html",
    "home_view": "web/pages/home/home.html",
    "scrape_view": "web/pages/scraping/scrape.html",
    "settings_view": "web/pages/settings/settings.html",
    "train_model_view": "web/pages/training/model_training.html",
}


def _iter_template_files() -> list[Path]:
    return sorted(path for path in TEMPLATES_ROOT.rglob("*.html"))


def test_web_views_use_namespaced_page_templates() -> None:
    assert all(path.startswith("web/pages/") for path in PAGE_TEMPLATE_PATHS.values())


def test_namespaced_templates_exist_for_each_web_view() -> None:
    for template_path in PAGE_TEMPLATE_PATHS.values():
        assert (Path(__file__).resolve().parents[3] / "studio" / "presentation" / "web" / "templates" / template_path).exists()


def test_page_templates_extend_shared_layout() -> None:
    page_templates = sorted((TEMPLATES_ROOT / "pages").rglob("*.html"))

    for template_path in page_templates:
        template_text = template_path.read_text(encoding="utf-8")
        assert "{% extends 'web/layouts/base.html' %}" in template_text


def test_template_references_are_loadable() -> None:
    request = RequestFactory().get("/")

    for template_path in PAGE_TEMPLATE_PATHS.values():
        try:
            template = get_template(template_path)
        except TemplateDoesNotExist as exc:  # pragma: no cover - assertion fallback
            raise AssertionError(f"Template not found: {template_path}") from exc
        template.render({}, request=request)


def test_static_css_is_namespaced_under_web_css() -> None:
    css_files = sorted((STATIC_ROOT / "css").glob("*.css"))
    assert [file.name for file in css_files] == ["backend.css", "base_ui.css", "chunks.css"]


def test_templates_use_namespaced_static_paths() -> None:
    pattern = re.compile(r"\{\% static '([^']+)'")

    for template_path in _iter_template_files():
        matches = pattern.findall(template_path.read_text(encoding="utf-8"))
        for static_path in matches:
            assert static_path.startswith("web/"), (
                f"Template {template_path} uses non-namespaced static path: {static_path}"
            )


def test_legacy_reddit_processor_partial_removed() -> None:
    assert not (TEMPLATES_ROOT.parent / "processor_reddit.html").exists()
