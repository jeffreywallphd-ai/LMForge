"""API training views.

Thin presentation adapters that delegate training lifecycle orchestration to the
application service/workflow layer.
"""

from __future__ import annotations

from dataclasses import asdict

from django.http import JsonResponse, StreamingHttpResponse

from studio.application.workflows.model_training import ModelTrainingWorkflow
from studio.application.workflows.training_adapters import InMemoryTrainingResultStore, LocalTrainingExecutor


def get_training_workflow() -> ModelTrainingWorkflow:
    return ModelTrainingWorkflow()


def _status_for_orchestration(result) -> int:
    if result.ok:
        return 200
    if result.failure_kind == "validation_error":
        return 400
    return 502


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

    result = get_training_workflow().execute_training(
        request.POST.dict(),
        executor=LocalTrainingExecutor(),
        result_store=InMemoryTrainingResultStore(),
    )

    status_code = _status_for_orchestration(result)
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
                "failure_kind": result.failure_kind,
            },
        },
        status=status_code,
    )


def train_model_workflow(request):
    if request.method != "POST":
        return JsonResponse({"status": "success", "data": {"message": "Training workflow page is web-only.", "next": "/training/"}})

    plan = get_training_workflow().prepare_training_outcome(request.POST.dict())
    if not plan.ok:
        return JsonResponse(
            {
                "status": "error",
                "message": plan.error_message,
                "failure_kind": plan.failure_kind,
            },
            status=400,
        )

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
