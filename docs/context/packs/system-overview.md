# Context Pack: System Overview

## Use When

- You need top-level architecture context.
- You are touching routing, settings, or cross-layer refactors.

## Primary Files

- `manage.py`
- `requirements.txt`
- `src/config/settings/base.py`
- `src/config/urls.py`
- `src/studio/models.py`
- `src/studio/presentation/api/urls.py`
- `src/studio/presentation/web/urls.py`

## Core Facts

- Django settings default to `src.config.settings.development` via `manage.py`.
- The project supports MySQL by default, but uses SQLite fallback in debug mode when DB env vars are missing and server/migrate commands run.
- Root URL configuration mounts both API (`/api/`) and web routes (`/`).
- `src/studio/models.py` re-exports domain models for Django app compatibility.
- API URL config includes current endpoints plus legacy-compatible UI route aliases.

## Architectural Direction

- Keep new business logic in `application/services` and `application/workflows`.
- Keep domain rules in `domain/policies`.
- Use infrastructure modules for external integrations (scraping, vector store, storage).
