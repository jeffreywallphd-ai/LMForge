"""Default training execution/persistence collaborators.

These adapters provide lightweight seams for local execution and storage in
presentation handlers while keeping orchestration in ``ModelTrainingWorkflow``.
"""

from __future__ import annotations

from studio.application.services.training_service import TrainingExecutionResult


class LocalTrainingExecutor:
    """Infrastructure seam for local runtime training execution."""

    def execute(self, *, config, precision: str, target_modules: list[str]) -> TrainingExecutionResult:
        return TrainingExecutionResult(
            ok=True,
            status="accepted",
            detail="Training execution was accepted by the local executor.",
            metadata={
                "model_name": config.model_name,
                "dataset_name": config.dataset_name,
                "precision": precision,
                "target_modules": target_modules,
            },
        )


class InMemoryTrainingResultStore:
    """Explicit persistence seam for training outcomes."""

    def save(self, **kwargs):
        execution = kwargs["execution"]
        return {
            "status": execution.status,
            "ok": execution.ok,
            "failure_kind": kwargs.get("failure_kind"),
            "model_name": kwargs["config"].model_name,
        }
