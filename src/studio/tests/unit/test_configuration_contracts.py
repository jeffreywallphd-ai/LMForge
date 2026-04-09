from __future__ import annotations

import importlib

from django.urls import URLResolver


def test_base_settings_database_configuration_is_env_driven(monkeypatch) -> None:
    monkeypatch.setenv('DATABASE_ENGINE', 'django.db.backends.postgresql')
    monkeypatch.setenv('DATABASE_NAME', 'lmforge')
    monkeypatch.setenv('DATABASE_USER', 'forge_user')
    monkeypatch.setenv('DATABASE_PASSWORD', 'top-secret')
    monkeypatch.setenv('DATABASE_HOST', 'db.example.com')
    monkeypatch.setenv('DATABASE_PORT', '5432')

    import config.settings.base as base_settings

    reloaded = importlib.reload(base_settings)
    default_db = reloaded.DATABASES['default']

    assert default_db['ENGINE'] == 'django.db.backends.postgresql'
    assert default_db['NAME'] == 'lmforge'
    assert default_db['USER'] == 'forge_user'
    assert default_db['PASSWORD'] == 'top-secret'
    assert default_db['HOST'] == 'db.example.com'
    assert default_db['PORT'] == '5432'


def test_project_urls_have_single_root_entry() -> None:
    import config.urls as project_urls

    root_patterns = [
        pattern
        for pattern in project_urls.urlpatterns
        if str(getattr(pattern, 'pattern', '')) == '' and isinstance(pattern, URLResolver)
    ]

    assert len(root_patterns) == 1
    assert root_patterns[0].urlconf_name.__name__ == 'studio.presentation.web.urls'
