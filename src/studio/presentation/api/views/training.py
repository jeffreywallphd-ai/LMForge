"""API training views.

Thin presentation adapters that delegate training lifecycle orchestration to the
application service/workflow layer.
"""

from __future__ import annotations

from dataclasses import asdict

from django.http import JsonResponse, StreamingHttpResponse

from studio.application.services.training_service import TrainingExecutionResult, TrainingService
from studio.application.workflows.model_training import ModelTrainingWorkflow


class LocalTrainingExecutor:
    """Infrastructure seam for local runtime training execution.

    This implementation is intentionally lightweight in tests/development and can
    be replaced by a queue-backed worker executor.
    """

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
    """Explicit persistence boundary for training outcomes.

    Replace with a DB-backed repository once training-run persistence model is finalized.
    """

    def save(self, **kwargs):
        execution = kwargs["execution"]
        return {
            "status": execution.status,
            "ok": execution.ok,
            "failure_kind": kwargs.get("failure_kind"),
            "model_name": kwargs["config"].model_name,
        }


def stream_training_output(_request):
    def event_stream():
        yield "data: training stream endpoint is available\n\n"

    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")


def stream_training_workflow_output(_request):
    def event_stream():
        yield "data: training workflow stream endpoint is available\n\n"

    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")


def train_model_view(request):
    if request.method != "POST":
        return JsonResponse({"status": "success", "data": {"message": "Training page is web-only.", "next": "/training/"}})

    service = TrainingService()
    result = service.orchestrate_training(
        request.POST.dict(),
        executor=LocalTrainingExecutor(),
        result_store=InMemoryTrainingResultStore(),
    )

    status_code = 200 if result.ok else 400
    return JsonResponse(
        {
            "status": "success" if result.ok else "error",
            "message": result.execution.detail,
            "training": {
                "model_size": result.model_size,
                "resolved_precision": result.resolved_precision,
                "target_modules": result.target_modules,
                "execution": asdict(result.execution),
                "persisted": result.persisted_record,
            },
        },
        status=status_code,
    )


def train_model_workflow(request):
    if request.method != "POST":
        return JsonResponse({"status": "success", "data": {"message": "Training workflow page is web-only.", "next": "/training/"}})

    workflow = ModelTrainingWorkflow()
    try:
        plan = workflow.prepare_training(request.POST.dict())
    except ValueError as exc:
        return JsonResponse({"status": "error", "message": str(exc)}, status=400)

    return JsonResponse(
        {
            "status": "success",
            "plan": {
                "config": asdict(plan.config),
                "model_size": plan.model_size,
                "resolved_precision": plan.resolved_precision,
                "target_modules": plan.target_modules,
            },
        }
    )


def train_encoder_view(_request):
    return JsonResponse({"status": "success", "data": {"message": "Encoder training is not yet extracted into a service."}})


def get_model_stats(_request):
    return JsonResponse({"status": "success", "data": {"message": "Model stats endpoint remains available via /api/model_statistics/."}})
