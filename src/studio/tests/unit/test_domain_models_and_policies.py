from __future__ import annotations

from datetime import date, datetime

import pytest
from django.core.exceptions import ValidationError

from src.studio.domain.models.conversations import Conversation
from src.studio.domain.models.dataset_artifacts import (
    Answer,
    DatasetArtifact,
    Question,
    ReviewAnswer,
    Reviewer,
)
from src.studio.domain.models.evaluation_runs import EvaluationRun
from src.studio.domain.models.model_stats import ModelStats
from src.studio.domain.models.processed_documents import License, ProcessedDocument, Source, ValidityLevel
from src.studio.domain.models.source_documents import SourceDocument, SourceDocumentMetadata
from src.studio.domain.models.training_runs import TrainingRun
from src.studio.domain.models.vector_collections import VectorCollection
from src.studio.domain.policies.dataset_rules import validate_dataset_request
from src.studio.domain.policies.evaluation_rules import validate_evaluation_run
from src.studio.domain.policies.training_rules import validate_training_run


@pytest.mark.parametrize(
    ("file_type", "expected"),
    [
        ("html", "Scraped from https://example.com (html)"),
        ("pdf", "Scraped from https://example.com (pdf)"),
    ],
)
def test_source_document_str(file_type: str, expected: str):
    model = SourceDocument(url="https://example.com", file_type=file_type, title="Example")
    assert str(model) == expected


def test_source_document_metadata_str():
    src = SourceDocument(url="https://example.com", file_type="html", title="Example")
    model = SourceDocumentMetadata(source_document=src, url=src.url, file_type=src.file_type, created_at=datetime.now())

    assert str(model) == "Metadata for https://example.com (html)"


@pytest.mark.parametrize(
    ("is_user", "expected_role"),
    [
        (True, "User"),
        (False, "Chatbot"),
    ],
)
def test_conversation_str_formats_role(is_user: bool, expected_role: str):
    convo = Conversation(session_id="s1", message="hello", is_user=is_user)
    assert str(convo) == f"Session s1 - {expected_role}: hello"


def test_model_stats_str_includes_model_and_dataset():
    stats = ModelStats(model_name="m1", dataset="d1")
    assert str(stats) == "m1 - d1"


def test_validity_level_labels_are_stable():
    assert ValidityLevel.RANDOM_UNVERIFIED.label == "Random/Unverified"
    assert ValidityLevel.SOURCED.label == "Sourced"
    assert ValidityLevel.PUBLISHED_AUDITED_GOVDATA.label == "Published/audited/GovData"


def test_processed_document_related_model_strings():
    license_obj = License(license_id=10, license_name="CC BY", license_valid=True, validity_level=ValidityLevel.SOURCED)
    source_obj = Source(
        source_id="SRC-1",
        source_name="Treasury",
        license=license_obj,
        source_description="US treasury feed",
        source_link="https://home.treasury.gov",
        validity_level=ValidityLevel.SOURCED,
    )
    doc = ProcessedDocument(
        doc_id="DOC-1",
        description="Yield curve",
        link="https://home.treasury.gov/yield",
        last_date_scraped=date(2026, 4, 7),
        name="Daily yields",
        source=source_obj,
        license=license_obj,
        requires_attribution=True,
        validity_level=ValidityLevel.PUBLISHED_AUDITED_GOVDATA,
    )

    assert str(license_obj) == "License 10 - CC BY (Status: Sourced)"
    assert "Source SRC-1 - Treasury - License: 10" in str(source_obj)
    assert "Document DOC-1 - Yield curve" in str(doc)
    assert "Status: Published/audited/GovData" in str(doc)


def test_dataset_artifact_model_strings():
    license_obj = License(license_id=7, license_name="MIT", license_valid=True)
    source_obj = Source(
        source_id="SRC-2",
        source_name="SEC",
        license=license_obj,
        source_description="SEC filings",
        source_link="https://sec.gov",
    )
    doc = ProcessedDocument(
        doc_id="DOC-2",
        description="10-K",
        link="https://sec.gov/filing",
        last_date_scraped=date(2026, 4, 1),
        name="Annual filing",
        source=source_obj,
        license=license_obj,
        requires_attribution=False,
    )
    question = Question(question_id=100, text="What is revenue?")
    answer = Answer(
        answer_id=200,
        link="https://sec.gov/answer",
        page_num=3,
        text="Revenue is ...",
        last_day_scraped=date(2026, 4, 1),
        copyright_date=date(2025, 12, 31),
        document=doc,
        license=license_obj,
        question=question,
    )
    artifact = DatasetArtifact(question=question, answer=answer)
    reviewer = Reviewer(first_name="Ada", last_name="Lovelace")
    review = ReviewAnswer(score_scale=5, description="Accurate", question=question, reviewer=reviewer)

    assert str(question) == "Question: What is revenue?"
    assert "Answer 200 - Link: https://sec.gov/answer" in str(answer)
    assert str(artifact) == "Question: What is revenue? - Answer: Revenue is ..."
    assert str(reviewer) == "Ada Lovelace"
    assert "Score: 5" in str(review)


@pytest.mark.parametrize("score", [1, 5])
def test_review_answer_allows_boundary_scores(score: int):
    review = ReviewAnswer(score_scale=score, description="ok")
    review.full_clean(exclude=["question", "reviewer"])


@pytest.mark.parametrize("score", [0, 6])
def test_review_answer_rejects_out_of_range_scores(score: int):
    review = ReviewAnswer(score_scale=score, description="bad")
    with pytest.raises(ValidationError):
        review.full_clean(exclude=["question", "reviewer"])


def test_vector_collection_defaults_and_slots_behavior():
    vc = VectorCollection(name="market-data", embedding_model="text-embedding-3-large", vector_size=3072)

    assert vc.distance_metric == "cosine"
    assert vc.name == "market-data"
    with pytest.raises(AttributeError):
        vc.extra_field = "not-allowed"


def test_evaluation_run_defaults():
    run = EvaluationRun(model_name="m-eval")

    assert run.max_length == 200
    assert run.min_length == 100
    assert run.top_k == 50
    assert run.top_p == pytest.approx(0.95)


def test_training_run_defaults():
    run = TrainingRun(model_name="m-train")

    assert run.learning_rate == pytest.approx(2e-5)
    assert run.num_epochs == 3
    assert run.batch_size == 1
    assert run.project_name == "lmforge"
    assert run.use_lora is False
    assert run.use_qlora is False


@pytest.mark.parametrize(
    "config",
    [
        TrainingRun(model_name="m", batch_size=1, train_test_split_ratio=0.1, use_qlora=False),
        TrainingRun(model_name="m", batch_size=4, train_test_split_ratio=0.9, use_qlora=True),
    ],
)
def test_validate_training_run_accepts_valid_configs(config: TrainingRun):
    validate_training_run(config, model_size=2_000_000_000)


@pytest.mark.parametrize(
    ("config", "model_size", "message"),
    [
        (
            TrainingRun(model_name="m", use_qlora=True, train_test_split_ratio=0.1, batch_size=1),
            1_200_000_000,
            "QLoRA",
        ),
        (TrainingRun(model_name="m", train_test_split_ratio=1.0, batch_size=1), 2_000_000_000, r"range \(0, 1\)"),
        (
            TrainingRun(model_name="m", train_test_split_ratio=0.5, batch_size=0),
            2_000_000_000,
            "greater than 0",
        ),
    ],
)
def test_validate_training_run_rejects_invalid_configs(config: TrainingRun, model_size: int, message: str):
    with pytest.raises(ValueError, match=message):
        validate_training_run(config, model_size=model_size)


@pytest.mark.parametrize(
    "config",
    [
        EvaluationRun(model_name="m", min_length=1, max_length=1, top_p=0.0, top_k=0),
        EvaluationRun(model_name="m", min_length=100, max_length=1024, top_p=1.0, top_k=100),
    ],
)
def test_validate_evaluation_run_accepts_bounds(config: EvaluationRun):
    validate_evaluation_run(config)


@pytest.mark.parametrize(
    ("config", "message"),
    [
        (EvaluationRun(model_name="m", min_length=200, max_length=100), "min_length"),
        (EvaluationRun(model_name="m", min_length=0, max_length=100), "min_length"),
        (EvaluationRun(model_name="m", min_length=10, max_length=200, top_p=1.1), "top_p"),
        (EvaluationRun(model_name="m", min_length=10, max_length=200, top_k=-1), "top_k"),
    ],
)
def test_validate_evaluation_run_rejects_invalid_configs(config: EvaluationRun, message: str):
    with pytest.raises(ValueError, match=message):
        validate_evaluation_run(config)


@pytest.mark.parametrize(
    "payload",
    [
        {"document_ids": [1], "questions_per_chunk": 1, "chunk_limit": 1},
        {"document_ids": [1, 2, 3], "questions_per_chunk": 3, "chunk_limit": 100},
    ],
)
def test_validate_dataset_request_accepts_valid_inputs(payload: dict):
    validate_dataset_request(**payload)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"document_ids": [], "questions_per_chunk": 1, "chunk_limit": 1}, "At least one source document"),
        ({"document_ids": [1], "questions_per_chunk": 0, "chunk_limit": 1}, "questions_per_chunk"),
        ({"document_ids": [1], "questions_per_chunk": 1, "chunk_limit": 0}, "chunk_limit"),
    ],
)
def test_validate_dataset_request_rejects_invalid_inputs(payload: dict, message: str):
    with pytest.raises(ValueError, match=message):
        validate_dataset_request(**payload)
