"""Application workflow: model training."""

from __future__ import annotations

from dataclasses import dataclass

from src.studio.application.services.training_service import TrainingConfig, TrainingService


@dataclass(slots=True)
class TrainingWorkflowPlan:
    config: TrainingConfig
    model_size: int
    resolved_precision: str
    target_modules: list[str]


class ModelTrainingWorkflow:
    """Coordinates model training setup/validation before execution."""

    def __init__(self, training_service: TrainingService | None = None) -> None:
        self.training_service = training_service or TrainingService()

    def build_config(self, payload: dict) -> TrainingConfig:
        return TrainingConfig(
            model_name=payload.get("model_name", "gpt2"),
            learning_rate=float(payload.get("learning_rate", 2e-5)),
            num_epochs=int(payload.get("num_epochs", 3)),
            batch_size=int(payload.get("batch_size", 1)),
            project_name=payload.get("project_name", "lmforge"),
            gradient_checkpointing=payload.get("gradient_checkpointing") in {True, "on", "true", "1"},
            max_grad_norm=float(payload.get("max_grad_norm", 1.0)),
            use_lora=payload.get("use_lora") in {True, "on", "true", "1"},
            use_qlora=payload.get("use_qlora") in {True, "on", "true", "1"},
            fp16=payload.get("fp16") in {True, "on", "true", "1"},
            bf16=payload.get("bf16") in {True, "on", "true", "1"},
            weight_decay=float(payload.get("weight_decay", 0.01)),
            model_repo=payload.get("model_repo", "OpenFinAL/your-model-name"),
            dataset_name=payload.get("dataset_name", "FinGPT/fingpt-fiqa_qa"),
            train_test_split_ratio=float(payload.get("train_test_split_ratio", 0.1)),
        )

    def prepare_training(self, payload: dict, *, hf_token: str = "") -> TrainingWorkflowPlan:
        config = self.build_config(payload)
        model_size = self.training_service.get_model_size(config.model_name, hf_token=hf_token)
        self.training_service.validate_training_config(config, model_size)
        dtype = self.training_service.resolve_precision(config)
        target_modules = self.training_service.get_target_modules(config.model_name)

        precision_name = "fp32" if dtype is None else str(dtype).replace("torch.", "")
        if config.use_qlora:
            precision_name = "4bit-qlora"

        return TrainingWorkflowPlan(
            config=config,
            model_size=model_size,
            resolved_precision=precision_name,
            target_modules=target_modules,
        )
