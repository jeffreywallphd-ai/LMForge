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

- Django settings default to `config.settings.development` via `manage.py`.
- Database configuration is environment-driven via `DATABASE_*` variables with no implicit SQLite fallback in base settings.
- Root URL configuration has a single web entry point at `/` (with API mounted at `/api/`).
- `src/studio/models.py` re-exports domain models for Django app compatibility.
- API URL config includes current endpoints plus legacy-compatible UI route aliases.

## Architectural Direction

- Keep new business logic in `application/services` and `application/workflows`.
- Keep domain rules in `domain/policies`.
- Use infrastructure modules for external integrations (scraping, vector store, storage).

## Presentation Classification Quick Check

When touching presentation code:

- API files (`src/studio/presentation/api/**`) should expose machine-facing JSON contracts.
- Web files (`src/studio/presentation/web/**`) should expose template/page contracts.
- If behavior must be shared, move it to `application/services` or `application/workflows` instead of cross-importing API/web views.
- See `docs/architecture/presentation-boundary-audit.md` for the current violation inventory and migration checklist.
