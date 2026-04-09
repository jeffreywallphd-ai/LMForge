# Module Reference (src)

## Runtime and Configuration

- `manage.py` — sets default Django settings and dispatches management commands.
- `src/config/settings/base.py` — shared Django settings, installed apps, middleware, template/static/media config, DB strategy.
- `src/config/settings/{development,production,test}.py` — environment profiles.
- `src/config/urls.py` — top-level URL composition for admin/api/web.

## Studio App Composition

- `src/studio/apps.py` — Django app config.
- `src/studio/models.py` — model re-exports for Django model discovery compatibility.

## Presentation Modules

### API

- `src/studio/presentation/api/urls.py`
- `src/studio/presentation/api/views/chat.py`
- `src/studio/presentation/api/views/scraping.py`
- `src/studio/presentation/api/views/datasets.py`
- `src/studio/presentation/api/views/training.py`
- `src/studio/presentation/api/views/evaluation.py`
- `src/studio/presentation/api/serializers/*`

### Web

- `src/studio/presentation/web/urls.py`
- `src/studio/presentation/web/views/*`
- `src/studio/presentation/web/forms/*`
- `src/studio/presentation/web/templates/web/layouts/*`
- `src/studio/presentation/web/templates/web/pages/*`
- `src/studio/presentation/web/templates/web/partials/*`
- `src/studio/presentation/web/static/web/*`

## Application Modules

### Services

- `chat_service.py` — conversation/session operations and text generation config/validation.
- `document_service.py` — scraping normalization and source persistence helpers.
- `scraping_service.py` — scrape request/result contracts, input validation, and scraper orchestration shared by web/API views.
- `dataset_service.py` — framework-agnostic dataset request/result contracts, Q/A orchestration, output normalization, and optional persistence handoff metadata.
- `training_service.py` — model-size lookup, precision/module selection, policy validation.
- `evaluation_service.py` — metric computation pipeline and evaluation validation.
- `vector_store_service.py` — Qdrant client abstraction and embedding storage/retrieval.
- `export_service.py` — JSON/CSV export rendering.

### Workflows

- `document_ingestion.py` — scrape-only and scrape+persist orchestration.
- `dataset_generation.py` — document selection to exported dataset artifacts.
- `embedding_storage.py` — chunking to vector store operations.
- `model_training.py` — training config assembly and preparatory plan.
- `model_evaluation.py` — dataset loading/sampling and aggregate scoring per model.

## Domain Modules

### Models

- Conversation and source-document models for ingestion/chat persistence.
- Dataset artifact models for question/answer/review lineage.
- Processed document and license/source taxonomies.
- Model stats persistence.

### Value Objects

- `training_runs.py`
- `evaluation_runs.py`
- `vector_collections.py`

### Policies

- `dataset_rules.py`
- `training_rules.py`
- `evaluation_rules.py`

## Infrastructure Modules

- `scraping/` — generic web scraping, Reddit scraping, PDF text extraction, advanced content extraction.
- `vectorstores/qdrant.py` — typed Qdrant and embedding helper module.
- `storage/` — filesystem and export helpers.
- `llm/` — model-provider adapter scaffolding.
- `observability/` and `jobs/` — currently minimal/scaffold modules.

## Test Layout

- `src/studio/tests/unit/*`
- `src/studio/tests/integration/*`

Tests are present for selected services/infrastructure and endpoint-level workflows, with room to increase coverage around new application workflows.

## Presentation Boundary Contracts

- Web-only handlers belong in `src/studio/presentation/web/views/*` and can render templates/forms.
- API-only handlers belong in `src/studio/presentation/api/views/*` and should return JSON/DRF responses only.
- Root routing split is enforced by `src/config/urls_web.py` and `src/config/urls_api.py`.
- Known exceptions and migration targets are tracked in `docs/architecture/presentation-boundary-audit.md`.


## Service-Layer Guidance

- Service boundary inventory and migration checklist: `docs/architecture/service-layer-audit.md`.
- Presentation placement and endpoint surface rules: `docs/architecture/presentation-layer-guide.md`.
