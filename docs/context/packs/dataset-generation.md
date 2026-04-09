# Context Pack: Dataset Generation

## Use When

- Building Q/A generation flows from source documents.
- Exporting generated records as JSON/CSV.

## Primary Files

- `src/studio/presentation/api/views/datasets.py`
- `src/studio/presentation/web/views/datasets.py`
- `src/studio/application/services/dataset_service.py`
- `src/studio/application/services/export_service.py`
- `src/studio/application/workflows/dataset_generation.py`
- `src/studio/domain/policies/dataset_rules.py`
- `src/studio/domain/models/dataset_artifacts.py`
- `src/studio/domain/models/source_documents.py`
- `docs/context/workflow-conventions.md`
- `docs/context/service-testing-conventions.md`

## Core Facts

- Dataset generation pulls selected `SourceDocument` content, chunks text, prompts a language model, and parses JSON arrays of Q/A records.
- Validation of business limits is centralized in `validate_dataset_request` and applied through `DatasetService` request normalization.
- `DatasetService` owns low-level generation mechanics (prompt assembly, model call, parse/normalize, request policy validation).
- `DatasetGenerationWorkflow` owns orchestration and caller contracts: `run(request)` returns normalized `ok/failure` result semantics and export renderings.
- `DatasetGenerationWorkflow.generate(...)` remains as a compatibility wrapper and delegates to `run(...)`.
- Embedding storage orchestration is handled separately by `EmbeddingStorageWorkflow`; dataset handlers should not inline Qdrant chunk-storage orchestration.

## Important Constraints

- Treat model outputs as untrusted; keep JSON extraction/parse guarded.
- Preserve predictable exports for downstream tooling.

## Dataset Workflow Lifecycle

1. Presentation parses request payload or form fields.
2. `DatasetGenerationWorkflow.run(...)` builds a `DatasetGenerationRequest` for service execution.
3. `DatasetService.generate_dataset(...)` runs generation/validation and returns normalized service result data.
4. Workflow renders JSON/CSV through `ExportService` and returns a single workflow outcome object (`ok`, records, failure metadata, persistence metadata).
