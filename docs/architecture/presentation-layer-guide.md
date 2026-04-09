# Presentation Layer Guide (Feature 2 Final)

This document defines the final placement and naming rules for presentation-layer code in the `src/` architecture.

## 1) Responsibilities

- `presentation/web/*`: browser-first HTML pages, template context mapping, and form handling.
- `presentation/api/*`: JSON-first contracts, serializer usage, and status-code mapping.
- Shared behavior should flow through `application/services` and `application/workflows` instead of cross-importing API/web views.

## 2) Route Organization

- Root URL split remains:
  - `/` -> `studio.presentation.web.urls`
  - `/api/` -> `studio.presentation.api.urls`
- Web route names should end with `-view` and avoid reusing API names.
- API route names should describe machine contracts and remain template-free.

## 3) Template Organization Standard

Template root: `src/studio/presentation/web/templates/web/`

- `layouts/`: shared shell templates (e.g., `layouts/base.html`)
- `pages/<feature>/`: page-level templates rendered directly by views
- `partials/<feature>/`: include-only snippets used by page templates

### Naming rules

- Renderable page templates must live under `web/pages/...`.
- Shared fragments should use noun-based names (`document_list.html`, `menu.html`) under `web/partials/...`.
- Avoid ambiguous duplicates (example removed during audit: `processor_reddit.html` duplicated URL input behavior).
- Always reference templates with full namespaced paths in `render(...)`, `{% extends %}`, and `{% include %}`.

## 4) Static Asset Organization Standard

Static root: `src/studio/presentation/web/static/web/`

- `css/`: shared page styles for server-rendered web flows.

Current normalized CSS paths:

- `web/css/backend.css`
- `web/css/base_ui.css`
- `web/css/chunks.css`

### Static reference rules

- Use `{% load static %}` and `{% static 'web/...` %}` paths only.
- Do not reference project-level static files without the `web/` namespace prefix.
- Keep static references stable across dev/test/prod by relying on Django static settings, not hardcoded `/static/...` URLs.

## 5) Scraping Vertical Slice Separation

- API scraping endpoint (`/api/scrape/`) must return JSON envelopes.
- Web scraping view (`/scraping/`) must render `web/pages/scraping/scrape.html` and map service outcomes to user-facing context.
- Both surfaces consume `ScrapingService` contracts; they must not call each other.

## 6) Anti-patterns to Avoid

- API views returning templates or redirects intended for browsers.
- Web views importing API view handlers directly.
- Templates in flat roots without feature/layout/partial structure.
- Static references that bypass `{% static %}`.
- Reusing one template for unrelated concerns when separate page/partial templates improve intent.

## 7) Migration Rules for Contributors

When adding/changing presentation code:

1. Place endpoint in correct surface (`web` vs `api`).
2. If HTML is needed, add template under `web/pages/<feature>/` and render via full namespaced path.
3. If reusable, extract to `web/partials/<feature>/`.
4. Keep business logic in services/workflows.
   - Forms should perform request-bound validation and field cleanup only; dataset processing/orchestration belongs in `DatasetService`.
5. Add or update tests for:
   - API JSON contract expectations
   - Web template rendering expectations
   - template/static path conventions when structure changes

## 8) Examples

### Add a new web page

1. Add route in `presentation/web/urls.py`.
2. Add view in `presentation/web/views/<feature>.py` that returns `render(request, 'web/pages/<feature>/<page>.html', context)`.
3. Create `web/pages/<feature>/<page>.html` extending `web/layouts/base.html`.

### Add a new API endpoint

1. Add DRF view in `presentation/api/views/<feature>.py`.
2. Add route in `presentation/api/urls.py`.
3. Return standardized JSON success/error envelopes.

### Add a feature exposed in both web and API

1. Add/extend service or workflow in `application/` first.
2. Map service output to JSON in API view.
3. Map the same output to template context in web view.
4. Add regression tests proving the two surfaces remain contract-distinct.
