from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile

from studio.presentation.web.forms.documents import DocumentProcessingForm, SourceDocumentForm
from studio.presentation.web.forms.evaluation import EvaluationRunForm
from studio.presentation.web.forms.training import TrainingRunForm


def test_source_document_form_requires_pdf_or_content() -> None:
    form = SourceDocumentForm(
        data={
            "title": "Doc",
            "url": "https://example.com",
            "file_type": "text",
            "content": "   ",
        }
    )

    assert not form.is_valid()
    assert "Provide either a PDF file or document text." in form.errors["__all__"]


def test_source_document_form_trims_content() -> None:
    form = SourceDocumentForm(
        data={
            "title": "Doc",
            "url": "https://example.com",
            "file_type": "text",
            "content": "  hello world  ",
        }
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["content"] == "hello world"


def test_source_document_form_accepts_pdf_without_content() -> None:
    upload = SimpleUploadedFile("doc.pdf", b"%PDF", content_type="application/pdf")
    form = SourceDocumentForm(
        data={
            "title": "Doc",
            "url": "https://example.com",
            "file_type": "pdf",
            "content": "",
        },
        files={"pdf_file": upload},
    )

    assert form.is_valid(), form.errors


def test_document_processing_form_trims_instruction_prompt() -> None:
    form = DocumentProcessingForm(
        data={
            "test_type": DocumentProcessingForm.TestType.REAL,
            "instruction_prompt": "  behave clearly  ",
            "num_paragraphs": 2,
            "num_questions": 4,
        }
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["instruction_prompt"] == "behave clearly"


def test_document_processing_form_enforces_ranges() -> None:
    form = DocumentProcessingForm(
        data={
            "test_type": DocumentProcessingForm.TestType.MOCKUP,
            "instruction_prompt": "",
            "num_paragraphs": 0,
            "num_questions": 600,
        }
    )

    assert not form.is_valid()
    assert "num_paragraphs" in form.errors
    assert "num_questions" in form.errors


def test_evaluation_run_form_trims_model_name() -> None:
    form = EvaluationRunForm(
        data={"model_name": "  model-x  ", "dataset_artifact_id": 1, "score_threshold": 0.7}
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["model_name"] == "model-x"


def test_training_run_form_trims_model_name() -> None:
    form = TrainingRunForm(
        data={
            "model_name": "  train-model  ",
            "dataset_artifact_id": 2,
            "epochs": 3,
            "batch_size": 8,
            "learning_rate": 0.001,
        }
    )

    assert form.is_valid(), form.errors
    assert form.cleaned_data["model_name"] == "train-model"
