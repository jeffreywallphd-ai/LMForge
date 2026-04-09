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


@dataclass(slots=True)
class TrainingWorkflowOutcome:
    ok: bool
    config: TrainingConfig | None = None
    model_size: int | None = None
    resolved_precision: str | None = None
    target_modules: list[str] | None = None
    failure_kind: str | None = None
    error_message: str | None = None


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

    def prepare_training_outcome(self, payload: dict, *, hf_token: str = "") -> TrainingWorkflowOutcome:
        try:
            plan = self.prepare_training(payload, hf_token=hf_token)
        except ValueError as exc:
            return TrainingWorkflowOutcome(
                ok=False,
                failure_kind="validation_error",
                error_message=str(exc),
            )

        return TrainingWorkflowOutcome(
            ok=True,
            config=plan.config,
            model_size=plan.model_size,
            resolved_precision=plan.resolved_precision,
            target_modules=plan.target_modules,
        )
