"""Application workflow: model training orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from studio.application.services.training_service import (
    TrainingConfig,
    TrainingExecutionResult,
    TrainingResultStore,
    TrainingService,
)


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


@dataclass(slots=True)
class TrainingWorkflowExecutionResult:
    """Normalized execution outcome for presentation adapters."""

    ok: bool
    config: TrainingConfig
    model_size: int
    resolved_precision: str
    target_modules: list[str]
    execution: TrainingExecutionResult
    persisted_record: dict[str, Any] | None
    failure_kind: str | None = None


class ModelTrainingWorkflow:
    """Coordinates model training setup, execution, and persistence."""

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

    def execute_training(
        self,
        payload: dict[str, Any],
        *,
        executor,
        result_store: TrainingResultStore | None = None,
        hf_token: str = "",
    ) -> TrainingWorkflowExecutionResult:
        """Run lifecycle: config assembly -> prepare -> execute -> persist."""

        config = self.build_config(payload)

        failure_kind: str | None = None
        try:
            model_size, resolved_precision, target_modules = self.training_service.prepare_training(config, hf_token=hf_token)
        except ValueError as exc:
            model_size = 0
            resolved_precision = "unknown"
            target_modules = []
            execution = TrainingExecutionResult(
                ok=False,
                status="invalid_config",
                detail=str(exc),
                metadata={},
            )
            failure_kind = "validation_error"
        else:
            try:
                execution = executor.execute(
                    config=config,
                    precision=resolved_precision,
                    target_modules=target_modules,
                )
                if not execution.ok:
                    failure_kind = "execution_error"
            except Exception as exc:  # pragma: no cover
                execution = TrainingExecutionResult(
                    ok=False,
                    status="failed",
                    detail=str(exc),
                    metadata={},
                )
                failure_kind = "execution_exception"

        persisted_record: dict[str, Any] | None = None
        if result_store is not None:
            persisted_record = result_store.save(
                config=config,
                model_size=model_size,
                precision=resolved_precision,
                target_modules=target_modules,
                execution=execution,
                failure_kind=failure_kind,
            )

        return TrainingWorkflowExecutionResult(
            ok=execution.ok,
            config=config,
            model_size=model_size,
            resolved_precision=resolved_precision,
            target_modules=target_modules,
            execution=execution,
            persisted_record=persisted_record,
            failure_kind=failure_kind,
        )
