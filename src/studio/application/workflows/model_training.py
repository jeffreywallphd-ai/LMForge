"""Application workflow: model training."""

from __future__ import annotations

from dataclasses import dataclass

from studio.application.services.training_service import TrainingConfig, TrainingService


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
        return self.training_service.assemble_config(payload)

    def prepare_training(self, payload: dict, *, hf_token: str = "") -> TrainingWorkflowPlan:
        config = self.build_config(payload)
        model_size, precision_name, target_modules = self.training_service.prepare_training(config, hf_token=hf_token)

        return TrainingWorkflowPlan(
            config=config,
            model_size=model_size,
            resolved_precision=precision_name,
            target_modules=target_modules,
        )
