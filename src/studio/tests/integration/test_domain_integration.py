from studio.domain.models import EvaluationRun, TrainingRun
from studio.domain.models import __all__ as domain_model_exports
from studio.domain.policies.dataset_rules import validate_dataset_request
from studio.domain.policies.evaluation_rules import validate_evaluation_run
from studio.domain.policies.training_rules import validate_training_run


def test_domain_package_exports_expected_symbols():
    expected = {
        "Answer",
        "Conversation",
        "DatasetArtifact",
        "EvaluationRun",
        "License",
        "ModelStats",
        "ProcessedDocument",
        "Question",
        "ReviewAnswer",
        "Reviewer",
        "Source",
        "SourceDocument",
        "SourceDocumentMetadata",
        "TrainingRun",
        "VectorCollection",
    }
    assert set(domain_model_exports) == expected


def test_policy_integration_with_default_value_objects():
    training = TrainingRun(model_name="meta-llama/Llama-3-8B", use_qlora=False)
    evaluation = EvaluationRun(model_name="meta-llama/Llama-3-8B")

    validate_training_run(training, model_size=8_000_000_000)
    validate_evaluation_run(evaluation)
    validate_dataset_request(document_ids=[1, 2], questions_per_chunk=2, chunk_limit=10)


def test_policy_integration_rejects_invalid_end_to_end_configuration():
    training = TrainingRun(model_name="small-model", use_qlora=True, train_test_split_ratio=0.2)
    evaluation = EvaluationRun(model_name="small-model", min_length=300, max_length=100)

    training_error = None
    eval_error = None

    try:
        validate_training_run(training, model_size=700_000_000)
    except ValueError as exc:
        training_error = str(exc)

    try:
        validate_evaluation_run(evaluation)
    except ValueError as exc:
        eval_error = str(exc)

    assert training_error is not None and "QLoRA" in training_error
    assert eval_error is not None and "min_length" in eval_error
