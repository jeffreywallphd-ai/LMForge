# Context Pack: Model Evaluation

## Use When

- Evaluating model outputs against reference datasets.
- Adjusting metric aggregation, sampling, or validation.

## Primary Files

- `src/studio/presentation/api/views/evaluation.py`
- `src/studio/application/services/evaluation_service.py`
- `src/studio/application/workflows/model_evaluation.py`
- `src/studio/domain/models/evaluation_runs.py`
- `src/studio/domain/policies/evaluation_rules.py`
- `src/studio/domain/models/model_stats.py`

## Core Facts

- Evaluation supports ROUGE, BERTScore, and STS-based similarity scoring.
- Workflow loads dataset from Hugging Face URL or local CSV, normalizes question/reference columns, samples deterministically, and aggregates per-model averages.
- Validation is performed through `validate_evaluation_run`.

## Important Constraints

- Dataset must contain recognizable question/input and answer/output columns.
- Maintain deterministic sampling (`random_state=42`) for reproducibility.
