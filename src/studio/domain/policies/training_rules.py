"""Domain policy: training rules and invariants."""

from __future__ import annotations

from src.studio.domain.models.training_runs import TrainingRun


def validate_training_run(config: TrainingRun, *, model_size: int) -> None:
    if config.use_qlora and model_size < 1_300_000_000:
        raise ValueError("QLoRA can only be applied to models with 1.3B parameters or more")
    if not (0 < config.train_test_split_ratio < 1):
        raise ValueError("train_test_split_ratio must be in range (0, 1)")
    if config.batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")
