# Presentation Boundary Audit (Stories 2.1.1–2.1.3)

## Purpose

This audit documents where LMForge currently mixes web presentation concerns and API presentation concerns in `src/studio/presentation/`.

The goal is to make the migration plan explicit before doing deeper behavior changes.

## Current State Summary

LMForge already has a top-level split between:

- Web views/routes under `src/studio/presentation/web/`
- API views/routes under `src/studio/presentation/api/`
- Root URL delegation via `src/config/urls_web.py` and `src/config/urls_api.py`

However, several modules still violate the intended boundary.

## Inventory of Boundary Violations

### A) API modules rendering HTML templates

These modules are in `presentation/api`, but still call `render(...)` and return template responses.

- `src/studio/presentation/api/views/chat.py`
  - `chatbot_view` renders `chatbot.html`
- `src/studio/presentation/api/views/datasets.py`
  - `database_workflow` renders `database_chunks.html`
- `src/studio/presentation/api/views/training.py`
  - template responses for training pages
- `src/studio/presentation/api/views/evaluation.py`
  - template response for model statistics page
- `src/studio/presentation/api/views/scraping.py`
  - template response for scrape UI

**Classification:** API package contains web/template endpoints.

### B) Web modules importing API view handlers directly

These modules are in `presentation/web/views`, but simply import view functions from API modules.

- `src/studio/presentation/web/views/chat.py` imports `studio.presentation.api.views.chat.chatbot_view`
- `src/studio/presentation/web/views/scraping.py` imports `studio.presentation.api.views.scraping.scrape_view`

**Classification:** web routes are backed by API module implementation.

### C) Web modules returning machine-oriented responses

Web modules that return JSON/SSE responses directly should be evaluated for contract intent.

- `src/studio/presentation/web/views/home.py` returns `JsonResponse` for collection deletion.
- `src/studio/presentation/web/views/training.py` exposes JSON status responses and streaming output.

**Classification:** web endpoints include machine-oriented contracts; migrate to API where possible, or explicitly document as web-only AJAX contracts.

### D) Scraping/inference/training orchestration still in presentation handlers

Heavy runtime orchestration currently lives in presentation views instead of thin HTTP adapters over application workflows.

- `src/studio/presentation/api/views/scraping.py`
- `src/studio/presentation/api/views/datasets.py`
- `src/studio/presentation/api/views/training.py`
- `src/studio/presentation/web/views/training.py`

**Classification:** presentation layer still owns non-trivial application/infrastructure work.

## Target Destination Structure

Keep the existing package split and enforce intent:

- `src/studio/presentation/web/`
  - template/page views
  - web forms
  - HTML route modules only
- `src/studio/presentation/api/`
  - DRF/classic JSON endpoints
  - serializers
  - API route modules only

Required contract:

1. API modules MUST NOT call `render(...)` or return template responses.
2. Web modules MUST NOT import view handlers from API modules.
3. Any shared behavior should be delegated to `application/services` or `application/workflows`.
4. Scraping/training/evaluation orchestration should move out of presentation handlers into application/infrastructure boundaries.

## Migration Rules (Contributor Checklist)

Use this checklist during refactor and review:

- [ ] File location matches contract (`presentation/web` for HTML, `presentation/api` for JSON).
- [ ] No API view imports from `django.shortcuts.render`.
- [ ] No web view imports from `studio.presentation.api.views.*`.
- [ ] New endpoint logic delegates business steps to `application/services` or `application/workflows`.
- [ ] URL registration remains split between web and API modules.
- [ ] Route names indicate surface intent (e.g., `api-*` for API contracts where practical).

## Route Topology (Current + Intended)

Current topology is structurally correct and should be preserved:

- `src/config/urls.py` composes:
  - `src/config/urls_api.py` mounted at `/api/`
  - `src/config/urls_web.py` mounted at `/`

Follow-up refactor work should focus on moving misclassified handlers without collapsing this routing split.

## Test Strategy for Upcoming Refactor

- Keep runtime behavior unchanged in this audit step.
- Add/maintain route contract tests that verify web and API URL mounting.
- Add boundary-audit placeholder tests that mark known violations as expected failures until migration is complete.


## Story 2.1.4/2.1.5 Update

Recent refactor changes align active handlers to clearer presentation contracts:

- API views were updated to remove template rendering calls and return JSON payloads.
- Web views no longer import API view handlers directly.
- Web handlers were reduced to browser-oriented template rendering flows.
- Standard API response envelope guidance now lives in `docs/architecture/api-response-contracts.md`.

## Story 2.2 Scraping Slice Update

- URL scraping business logic now routes through `ScrapingService` in the application layer.
- `presentation/api/views/scraping.py` exposes a dedicated JSON-only scrape endpoint contract.
- `presentation/web/views/scraping.py` provides a browser-oriented template flow that maps service outcomes to user-facing context.
- Scraping contracts are now explicit (`ScrapeRequest`, `ScrapeResult`) instead of ad hoc dictionaries in view handlers.

## Story 2.3 Update: Template/Static Normalization + Regression Coverage

Completed hardening work for the presentation split now includes:

- Namespaced web template paths under `web/layouts`, `web/pages`, and `web/partials`.
- Namespaced static assets under `web/css/*` with normalized `{% static 'web/...` %}` references.
- Removal of ambiguous duplicate partial usage (`processor_reddit.html`) in favor of shared `input_url.html` partial behavior.
- Regression tests that guard:
  - API scraping surface remains JSON-oriented.
  - Web scraping surface remains template-oriented.
  - Web page templates stay under `web/pages/*` and extend `web/layouts/base.html`.

Refer to `docs/architecture/presentation-layer-guide.md` for forward-looking contributor rules.
