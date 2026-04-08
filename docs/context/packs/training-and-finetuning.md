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
- `TrainingService` resolves model size, target modules, and precision mode (fp16/bf16/QLoRA).
- Policy validation enforces safe parameter ranges and feature constraints based on model size.
- Training views currently remain large and procedural, but workflow abstraction exists for cleaner orchestration.

## Important Constraints

- Respect precision compatibility toggles (`use_qlora`, `fp16`, `bf16`).
- Keep low-memory pathways available for large models.
