# Context Pack: Training and Fine-Tuning

## Use When

- Modifying model training setup, constraints, or workflow orchestration.

## Primary Files

- `src/studio/presentation/api/views/training.py`
- `src/studio/presentation/web/views/training.py`
- `src/studio/application/services/training_service.py`
- `src/studio/application/workflows/model_training.py`
- `src/studio/domain/models/training_runs.py`
- `src/studio/domain/policies/training_rules.py`
- `docs/context/workflow-conventions.md`

## Core Facts

- `TrainingRun` is a dataclass-based config object used in service/workflow layers.
- `TrainingService` owns focused operations: config assembly, model-size lookup, policy validation, precision/module resolution.
- `ModelTrainingWorkflow` owns cross-step orchestration (`execute_training`): configuration -> preparation -> execution collaborator -> persistence collaborator.
- `ModelTrainingWorkflow` also exposes plan-oriented helpers (`prepare_training`, `prepare_training_outcome`) for preview/validation flows.
- Training API/web views are thin adapters that call the workflow and map normalized outcomes to JSON/template contracts.
- Policy validation enforces safe parameter ranges and feature constraints based on model size.

## Important Constraints

- Respect precision compatibility toggles (`use_qlora`, `fp16`, `bf16`).
- Keep low-memory pathways available for large models.

- Training lifecycle boundary: config assembly -> execution collaborator -> persistence collaborator.

## Training Workflow Lifecycle

1. Presentation parses primitive request payload.
2. Workflow builds normalized config through `TrainingService`.
3. Workflow prepares/validates the plan (`model_size`, `resolved_precision`, `target_modules`).
4. Workflow calls execution collaborator (`TrainingExecutor`).
5. Workflow calls optional persistence collaborator (`TrainingResultStore`).
6. Workflow returns a normalized execution result with `ok`, `failure_kind`, execution detail, and persisted metadata.
