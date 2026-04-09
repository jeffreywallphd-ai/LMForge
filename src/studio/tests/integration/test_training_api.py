from __future__ import annotations

import json
from types import SimpleNamespace

from django.test import RequestFactory

from studio.application.services.training_service import TrainingExecutionResult
from studio.presentation.api.views import training as api_training_views
from studio.presentation.web.views import training as web_training_views


class _FakeTrainingService:
    def __init__(self, result) -> None:
        self.result = result
        self.received_payload = None

    def orchestrate_training(self, payload, *, executor, result_store):
        self.received_payload = payload
        assert executor is not None
        assert result_store is not None
        return self.result


def _orchestration_result(*, ok: bool, detail: str, failure_kind: str | None = None):
    return SimpleNamespace(
        ok=ok,
        model_size=8_000_000_000,
        resolved_precision="4bit-qlora",
        target_modules=["q_proj", "v_proj"],
        execution=TrainingExecutionResult(ok=ok, status="accepted" if ok else "invalid_config", detail=detail, metadata={}),
        persisted_record={"id": "tr-1", "ok": ok},
        failure_kind=failure_kind,
    )


def _json(response):
    return json.loads(response.content.decode())


def test_train_model_api_maps_success_service_outcome(monkeypatch) -> None:
    fake_service = _FakeTrainingService(_orchestration_result(ok=True, detail="queued"))
    monkeypatch.setattr(api_training_views, "get_training_service", lambda: fake_service)

    request = RequestFactory().post("/api/train_model/", data={"model_name": "gpt2", "train_test_split_ratio": "0.1"})
    response = api_training_views.train_model_view(request)

    body = _json(response)
    assert response.status_code == 200
    assert body["status"] == "success"
    assert body["message"] == "queued"
    assert body["training"]["resolved_precision"] == "4bit-qlora"
    assert fake_service.received_payload["model_name"] == "gpt2"


def test_train_model_api_maps_validation_failure_to_bad_request(monkeypatch) -> None:
    fake_service = _FakeTrainingService(
        _orchestration_result(
            ok=False,
            detail="train_test_split_ratio must be in range (0, 1)",
            failure_kind="validation_error",
        )
    )
    monkeypatch.setattr(api_training_views, "get_training_service", lambda: fake_service)

    request = RequestFactory().post("/api/train_model/", data={"train_test_split_ratio": "5"})
    response = api_training_views.train_model_view(request)

    body = _json(response)
    assert response.status_code == 400
    assert body["status"] == "error"
    assert body["training"]["failure_kind"] == "validation_error"


def test_train_model_workflow_maps_normalized_workflow_error(monkeypatch) -> None:
    class _FakeWorkflow:
        def prepare_training_outcome(self, _payload):
            return SimpleNamespace(ok=False, failure_kind="validation_error", error_message="invalid training payload")

    monkeypatch.setattr(api_training_views, "ModelTrainingWorkflow", _FakeWorkflow)

    request = RequestFactory().post("/api/train_model_workflow/", data={"model_name": "gpt2"})
    response = api_training_views.train_model_workflow(request)

    body = _json(response)
    assert response.status_code == 400
    assert body["failure_kind"] == "validation_error"
    assert body["message"] == "invalid training payload"


def test_training_web_view_acts_as_service_adapter(monkeypatch) -> None:
    fake_service = _FakeTrainingService(_orchestration_result(ok=True, detail="Training accepted"))
    monkeypatch.setattr(web_training_views, "TrainingService", lambda: fake_service)

    request = RequestFactory().post("/training/", data={"model_name": "gpt2", "train_test_split_ratio": "0.1"})
    response = web_training_views.train_model_view(request)

    assert response.status_code == 200
    body = response.content.decode()
    assert "Training accepted" in body
    assert fake_service.received_payload["model_name"] == "gpt2"
