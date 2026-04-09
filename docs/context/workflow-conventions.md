# Workflow Layer Conventions (`src/studio/application/workflows`)

## Purpose

Use workflows for **multi-step orchestration** across services/collaborators. Workflows are the application-layer home for use cases that coordinate sequencing, branching, and result-shape normalization.

## Placement

- Package: `src/studio/application/workflows/`
- Naming:
  - module: `<use_case>.py` (for example `dataset_generation.py`, `model_training.py`)
  - class: `<UseCase>Workflow`
  - request/result contracts: `<UseCase>WorkflowRequest`, `<UseCase>WorkflowResult`

## Boundary Rules

### What belongs in a workflow

- Sequencing of steps across one or more services.
- Cross-service collaboration (for example generation + export, or prepare + execute + persist).
- Mapping low-level service outputs into a **normalized caller contract** (`ok`, failure metadata, and workflow-level payload).
- Delegating execution/persistence seams through explicit collaborators.

### What does **not** belong in a workflow

- HTTP concerns (request objects, serializers, status code decisions, template rendering).
- Fine-grained business rules already represented in `domain/policies` or service internals.
- Infrastructure implementation details (SDK-specific request construction, model runtime setup, DB query formatting beyond collaborator contracts).

## Collaboration Pattern

Presentation handlers should:

1. parse input shape only,
2. call a workflow,
3. map workflow outcomes to API/web response contracts.

Workflows should call services for low-level operations and optionally call infrastructure-facing collaborators (executor/store callbacks) through narrow interfaces.

## Success/Failure Semantics

- Workflow results must expose `ok: bool`.
- Failures should include typed metadata (`failure_kind` and/or domain failure object with `code` + `message`).
- Workflows should avoid throwing for expected validation/execution failures; return normalized failure outcomes where practical.
- Legacy compatibility methods may still raise (for old callers) but should delegate to a normalized workflow method.

## Current Canonical Examples

- Dataset generation orchestration: `DatasetGenerationWorkflow.run(...)`
- Training pipeline orchestration: `ModelTrainingWorkflow.execute_training(...)`

Both are designed to keep orchestration out of views and out of low-level services.
