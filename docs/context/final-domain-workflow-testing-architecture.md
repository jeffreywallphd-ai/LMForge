# Final Domain, Workflow, and Testing Architecture (Feature 4)

## Purpose

This is the durable reference for where Feature 4 logic lives, how layers collaborate, and how changes are protected with tests.

## Layer Placement Rules

## 1) Domain Layer

**Path:** `src/studio/domain/models/` and `src/studio/domain/policies/`

- Domain models are canonicalized under `studio.domain.models`.
- Use barrel imports outside model modules:
  - `from studio.domain.models import <Type>`
- `src/studio/models.py` exists only as a Django model registry compatibility surface.

### Anti-patterns

- Importing domain types via `from studio.models import ...` in application/presentation/tests.
- Reintroducing legacy aliases like `ScrapedData`.

## 2) Workflow Layer

**Path:** `src/studio/application/workflows/`

Workflows own multi-step orchestration and normalized outcomes.

- Training orchestration: `model_training.py`
- Embedding/database orchestration: `embedding_storage.py`
- Document ingestion orchestration: `document_ingestion.py`
- Dataset generation orchestration: `dataset_generation.py`
- Model evaluation orchestration: `model_evaluation.py`

### Workflow responsibilities

- Sequence multiple operations and collaborators.
- Normalize outcomes for presentation callers.
- Keep HTTP concerns out of workflow modules.

### Anti-patterns

- Putting API/web request parsing in workflows.
- Duplicating workflow branching logic in presentation views.

## 3) Service Layer

**Path:** `src/studio/application/services/`

Services provide focused behavior for single bounded capabilities.

- `chat_service.py` handles turn validation/model execution/persistence semantics.
- `scraping_service.py` handles scrape request normalization and scrape failure typing.
- `document_service.py` handles lower-level content normalization/persistence helpers.

### Service/workflow collaboration

- Use workflows for orchestration-heavy slices (training, dataset/embedding).
- Use services directly for thin, single-operation API slices (chat turns, scraping).

## 4) Presentation Layer

**Paths:**

- API: `src/studio/presentation/api/**`
- Web: `src/studio/presentation/web/**`

### API contract conventions

- Success envelope: `{ "status": "success", "data": ... }`
- Error envelope: `{ "status": "error", "error": { "code", "message", ... } }`
- Status code mapping comes from typed service/workflow outcomes.

### Anti-patterns

- API views importing template helpers.
- Web views importing API view modules.
- Presentation modules directly importing runtime-heavy model libraries for orchestration.

## Testing Baseline

## Unit Tests

- Domain import/naming guardrails:
  - `src/studio/tests/unit/test_domain_model_import_contracts.py`
- Presentation boundary guardrails:
  - `src/studio/tests/unit/test_presentation_boundary_audit.py`
- Architecture regression guardrails:
  - `src/studio/tests/unit/test_architecture_regression_guards.py`
- Service/workflow behavior contracts:
  - `src/studio/tests/unit/test_chat_service.py`
  - `src/studio/tests/unit/test_dataset_service.py`
  - `src/studio/tests/unit/test_other_workflows.py`

## Integration Tests

- Scraping API contract:
  - `src/studio/tests/integration/test_scraping_api.py`
- Chat API contract (plus evaluation API checks):
  - `src/studio/tests/integration/test_presentation_api_chat_and_eval.py`
- Dataset API contract:
  - `src/studio/tests/integration/test_dataset_api.py`
- Training API contract:
  - `src/studio/tests/integration/test_training_api.py`

## What Is Protected by Regression Checks

- Canonical domain model imports and naming.
- Correct placement of orchestration-heavy behavior in workflows.
- Service-backed chat/scraping API adapter boundaries.
- Presence of contract integration coverage for the core API slices.

## Contributor Quick Start

When adding a feature:

1. Place persistent domain concepts in `studio.domain.models`.
2. If the path requires multi-step orchestration, add/extend a workflow.
3. Keep presentation handlers thin and contract-oriented.
4. Add or update:
   - unit tests for behavior contracts,
   - integration tests for API response/status contract,
   - architecture guard tests when introducing a new long-lived boundary.
