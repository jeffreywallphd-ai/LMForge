from __future__ import annotations

from django.shortcuts import render

from studio.application.workflows.model_training import ModelTrainingWorkflow
from studio.application.workflows.training_adapters import InMemoryTrainingResultStore, LocalTrainingExecutor


def train_model_view(request):
    context: dict[str, object] = {
        "training_result": None,
        "training_error": None,
    }

    if request.method == "POST":
        result = ModelTrainingWorkflow().execute_training(
            request.POST.dict(),
            executor=LocalTrainingExecutor(),
            result_store=InMemoryTrainingResultStore(),
        )

        if result.ok:
            context["training_result"] = {
                "detail": result.execution.detail,
                "model_size": result.model_size,
                "resolved_precision": result.resolved_precision,
                "target_modules": result.target_modules,
            }
        else:
            context["training_error"] = result.execution.detail

    return render(request, "web/pages/training/model_training.html", context)
