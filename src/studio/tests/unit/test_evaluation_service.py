import pytest

from studio.application.services.evaluation_service import EvaluationService
from studio.domain.models.evaluation_runs import EvaluationRun


def test_validate_constraints_delegates(monkeypatch):
    service = EvaluationService()
    called = {}

    def _validate(config):
        called["name"] = config.model_name

    monkeypatch.setattr("studio.application.services.evaluation_service.validate_evaluation_run", _validate)
    service.validate_constraints(EvaluationRun(model_name="gpt2"))
    assert called == {"name": "gpt2"}


def test_cal_sts_score_returns_nan_for_non_string_inputs():
    service = EvaluationService()
    assert service.cal_sts_score(1, "a") == "nan"


def test_model_stats_validates_config_first(monkeypatch):
    service = EvaluationService()

    def _fail(_cfg):
        raise ValueError("bad config")

    monkeypatch.setattr(service, "validate_constraints", _fail)
    with pytest.raises(ValueError, match="bad config"):
        service.model_stats("prompt", ["ref"], EvaluationRun(model_name="gpt2"))
