"""Domain value object for evaluation runs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EvaluationRun:
    model_name: str
    max_length: int = 200
    min_length: int = 100
    top_k: int = 50
    top_p: float = 0.95
    max_new_tokens: int = 300
    no_repeat_ngrams: int = 0
