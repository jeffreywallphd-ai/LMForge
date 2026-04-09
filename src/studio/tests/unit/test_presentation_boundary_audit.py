from __future__ import annotations

import ast
from pathlib import Path

import pytest


SRC_ROOT = Path(__file__).resolve().parents[3]
API_VIEWS_DIR = SRC_ROOT / 'studio' / 'presentation' / 'api' / 'views'
WEB_VIEWS_DIR = SRC_ROOT / 'studio' / 'presentation' / 'web' / 'views'


def _python_files(directory: Path) -> list[Path]:
    return sorted(path for path in directory.glob('*.py') if path.name != '__init__.py')


def _parse_imports(module_path: Path) -> tuple[set[str], set[str]]:
    tree = ast.parse(module_path.read_text(encoding='utf-8'))
    imported_modules: set[str] = set()
    imported_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
            for alias in node.names:
                imported_names.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)

    return imported_modules, imported_names


def test_root_urlconf_delegates_to_split_api_and_web_modules() -> None:
    import config.urls as root_urls

    includes = [
        pattern.urlconf_name.__name__
        for pattern in root_urls.urlpatterns
        if hasattr(pattern, 'urlconf_name') and hasattr(pattern.urlconf_name, '__name__')
    ]

    assert 'studio.presentation.api.urls' in includes
    assert 'studio.presentation.web.urls' in includes


def test_split_url_modules_mount_expected_prefixes() -> None:
    import config.urls_api as urls_api
    import config.urls_web as urls_web

    assert any(str(pattern.pattern) == 'api/' for pattern in urls_api.urlpatterns)
    assert any(str(pattern.pattern) == '' for pattern in urls_web.urlpatterns)


@pytest.mark.xfail(
    reason='Story 2.1 audit identified API modules still rendering templates; refactor tracked in boundary audit doc.',
    strict=False,
)
def test_api_views_do_not_import_template_rendering() -> None:
    violating_modules: list[str] = []

    for module_path in _python_files(API_VIEWS_DIR):
        imported_modules, imported_names = _parse_imports(module_path)
        if 'django.shortcuts' in imported_modules and 'render' in imported_names:
            violating_modules.append(module_path.name)

    assert violating_modules == []


@pytest.mark.xfail(
    reason='Story 2.1 audit identified web views importing API handlers directly; migrate shared behavior to application layer.',
    strict=False,
)
def test_web_views_do_not_import_api_view_modules() -> None:
    violating_modules: list[str] = []

    for module_path in _python_files(WEB_VIEWS_DIR):
        imported_modules, _ = _parse_imports(module_path)
        if any(module.startswith('studio.presentation.api.views') for module in imported_modules):
            violating_modules.append(module_path.name)

    assert violating_modules == []
