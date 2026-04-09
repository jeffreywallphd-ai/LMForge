# Domain Model Stabilization Guide (Stories 4.1.1–4.1.4)

## Purpose

This document is the working inventory and migration guide for domain-model placement, import-path, naming, and migration consistency in the `src/studio` architecture.

## Canonical Structure (Target)

- **Domain model ownership:** `src/studio/domain/models/*`
- **Canonical import path for domain models and related types (outside model modules):**
  - `from studio.domain.models import <TypeName>`
- **Django model registry compatibility module:** `src/studio/models.py`
  - Keep this file as a compatibility export surface for Django app model discovery.
  - Do **not** use it as a primary import path in application/presentation/tests/policies.

## Current Inconsistency Inventory

### 1) Multiple import paths for the same model (resolved in this pass)

Previously, domain Django models were imported through both:

- `studio.models` (compatibility registry module), and
- `studio.domain.models.<module>`

This created ambiguity over ownership and encouraged layering shortcuts.

### 2) Naming drift in usage sites (resolved in this pass)

Legacy aliases such as `ScrapedData` / `ScrapedDataMeta` were used for `SourceDocument` and `SourceDocumentMetadata`.
These names leak old terminology and obscure domain meaning.

### 3) Mixed import granularity (resolved in this pass)

Code referenced both:

- `from studio.domain.models.<module> import ...` and
- `from studio.domain.models import ...`

The mixed pattern made search/refactoring harder and increased circular-import risk when modules moved.

### 4) Migration-state mismatch (identified and addressed)

- `src/studio/migrations/` previously had only `__init__.py`.
- Running `makemigrations` produced a non-empty initial migration (`0001_initial.py`), proving model state was not represented in migration history.
- `makemigrations --check --dry-run` now reports no pending changes after adding the initial migration.
- In this environment, Django emits a database-history warning when MySQL is unavailable; treat this as an environment caveat, not migration drift.

## Migration Rules for Imports and Naming

1. **In application/presentation/tests/domain-policies**, import domain models via:
   - `from studio.domain.models import ...`
2. **Do not introduce new `from studio.models import ...` usages** outside `src/studio/models.py`.
3. Use architecture-aligned names in code:
   - `SourceDocument` (not `ScrapedData`)
   - `SourceDocumentMetadata` (not `ScrapedDataMeta`)
4. Keep domain types in `studio.domain.models` even when they are value objects/dataclasses.

## Naming Conventions (Normalized)

- **Entities:** singular PascalCase nouns (`SourceDocument`, `ModelStats`, `DatasetArtifact`).
- **Value-like domain support types:** singular PascalCase nouns (`TrainingRun`, `EvaluationRun`, `VectorCollection`).
- **Avoid persistence-era abbreviations** in variable names unless mapping a legacy DB column/table.
- **Allow legacy DB table/column names** only at ORM mapping boundaries (`db_table`, `db_column`).

## Lightweight Checklist for Future Changes

- [ ] Is each domain concept implemented under `src/studio/domain/models`?
- [ ] Are imports using `from studio.domain.models import ...`?
- [ ] Are legacy aliases like `ScrapedData*` avoided?
- [ ] Are names singular, role-clear, and architecture-aligned?
- [ ] If ORM mappings require legacy names, are they isolated to model field metadata?
- [ ] Did migration checks run (`makemigrations --check --dry-run`)?

## Validation/Scaffolding Added

- Import-contract and naming guard tests were added to catch regressions:
  - `src/studio/tests/unit/test_domain_model_import_contracts.py`
