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

## Core Facts

- `TrainingRun` is a dataclass-based config object used in service/workflow layers.
- `TrainingService` assembles normalized training configs, resolves model size/precision/modules, orchestrates execution handoff, and coordinates explicit persistence handoff.
- `ModelTrainingWorkflow` provides plan-oriented helpers (`prepare_training`) and normalized workflow outcomes (`prepare_training_outcome`) for presentation adapters.
- Training API/web views are thin adapters: they parse request inputs, invoke service/workflow contracts, and map normalized outcomes to JSON/template contracts.
- Policy validation enforces safe parameter ranges and feature constraints based on model size.

## Important Constraints

- Respect precision compatibility toggles (`use_qlora`, `fp16`, `bf16`).
- Keep low-memory pathways available for large models.

- Training lifecycle boundary: config assembly -> execution collaborator -> persistence collaborator.
