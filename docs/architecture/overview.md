# LMForge Architecture (Current src-based System)

## 1) Scope of this Architecture Document

This architecture describes the **active implementation under `src/`** and root runtime files that directly configure it.

Excluded from architecture decisions here:

- `Sandbox/`
- `AIAgent/` prototype
- `lmforge/` legacy codebase
- `README.md` and `documentation/` as non-canonical references

## 2) Runtime Stack

- **Framework:** Django + Django REST Framework
- **Primary app:** `src.studio`
- **Entrypoint:** `manage.py` with default settings module `src.config.settings.development`
- **URL roots:**
  - Web routes mounted at `/` via `src/studio/presentation/web/urls.py`
  - API routes mounted at `/api/` via `src/studio/presentation/api/urls.py`
- **Storage:** MySQL by default; SQLite fallback for local debug when DB env values are missing during runserver/migrate flows

## 3) Layered Structure

```text
presentation (api + web)
  -> application (services + workflows)
      -> domain (models + policies)
      -> infrastructure (scraping, vectorstores, storage, llm adapters)
```

### Presentation Layer

Handles HTTP concerns, serializers, and templates.

- API surface: chat, scraping, dataset workflow, training, evaluation endpoints.
- Web surface: home/settings/chat/scraping/datasets/training/evaluation pages.
- Current state: several large view modules still contain orchestration and infrastructure-level logic.

### Application Layer

Defines reusable use-case logic.

- Services encapsulate focused operations (chat generation, dataset generation, training/eval validation, export, vector store operations, document processing).
- Workflows orchestrate end-to-end operations (document ingestion, dataset generation, embedding storage, training prep, evaluation runs).
- Current state: abstractions exist but are only partially adopted by presentation views.

### Domain Layer

Contains core business models and validation policies.

- Persistent models (Django): conversations, source docs, processed docs, dataset artifacts, model stats.
- Value objects (dataclasses): `TrainingRun`, `EvaluationRun`, `VectorCollection`.
- Policies: dataset/training/evaluation validation rules.

### Infrastructure Layer

Adapters for external systems and utilities.

- Scraping/content extraction (generic web, Reddit, PDF, content heuristics).
- Vector store access (Qdrant integration).
- Export/file helpers.
- Observability and jobs modules are scaffolded but minimal.

## 4) Architectural Characteristics

- **Compatibility-oriented:** model table names and route aliases preserve historical behavior.
- **Incremental refactor in progress:** service/workflow architecture coexists with legacy-style view code.
- **ML-heavy execution path:** direct runtime loading of tokenizer/model/metrics in request flows.
- **Resilience strategy:** graceful fallback when optional dependencies (e.g., Qdrant) are missing.

## 5) Key Design Constraints

1. Preserve current database schema compatibility (`db_table` mappings).
2. Avoid coupling new logic to excluded legacy/prototype folders.
3. Prefer moving new business logic into application services/workflows rather than expanding monolithic views.
4. Keep API and web behavior stable unless a breaking-change migration is intentionally planned.

## 6) Suggested Near-Term Improvements

1. Route all API view business logic through application workflows.
2. Isolate model loading/inference behind infrastructure adapters with lifecycle-aware caching.
3. Consolidate duplicate utility logic currently repeated across views/services.
4. Add job-queue-backed execution for long-running training/evaluation tasks.
5. Expand unit/integration coverage around workflows and domain policies.
