"""Domain policy: evaluation rules and invariants."""

from __future__ import annotations

from src.studio.domain.models.evaluation_runs import EvaluationRun


def validate_evaluation_run(config: EvaluationRun) -> None:
    if not (1 <= config.min_length <= config.max_length <= 1024):
        raise ValueError("min_length must be <= max_length and within valid range")
    if not (0 <= config.top_p <= 1):
        raise ValueError("top_p must be between 0 and 1")
    if config.top_k < 0:
        raise ValueError("top_k must be a non-negative integer")
