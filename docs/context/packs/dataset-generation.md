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

## Core Facts

- Dataset generation pulls selected `SourceDocument` content, chunks text, prompts a language model, and parses JSON arrays of Q/A records.
- Validation of business limits is centralized in `validate_dataset_request` and applied through `DatasetService` request normalization.
- `DatasetService` returns a structured result contract (`ok`, normalized records, failure metadata, optional persistence handoff metadata).
- Workflow layer adapts service output into JSON/CSV renderings for presentation use.
- Legacy view still bundles tokenization, Qdrant interactions, and rendering in one module.

## Important Constraints

- Treat model outputs as untrusted; keep JSON extraction/parse guarded.
- Preserve predictable exports for downstream tooling.
