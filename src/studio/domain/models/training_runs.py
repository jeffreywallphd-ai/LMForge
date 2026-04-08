"""Domain value object for model training runs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TrainingRun:
    model_name: str
    learning_rate: float = 2e-5
    num_epochs: int = 3
    batch_size: int = 1
    project_name: str = "lmforge"
    gradient_checkpointing: bool = False
    max_grad_norm: float = 1.0
    use_lora: bool = False
    use_qlora: bool = False
    fp16: bool = False
    bf16: bool = False
    weight_decay: float = 0.01
    model_repo: str = "OpenFinAL/your-model-name"
    dataset_name: str = "FinGPT/fingpt-fiqa_qa"
    train_test_split_ratio: float = 0.1
