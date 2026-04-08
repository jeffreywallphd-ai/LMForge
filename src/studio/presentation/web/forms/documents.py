"""Web forms for document ingestion and dataset preparation."""

from __future__ import annotations

from django import forms
from django.db.models import TextChoices

from src.studio.domain.models.source_documents import SourceDocument


class SourceDocumentForm(forms.ModelForm):
    """Capture uploaded files or raw text into the source-document model.

    This form modernizes the legacy ``DocumentForm`` behavior from ``lmforge`` by
    targeting the domain model used by the Studio app and by supporting both
    file and text ingestion paths.
    """

    class Meta:
        model = SourceDocument
        fields = ["title", "url", "file_type", "pdf_file", "content"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "maxlength": 100}),
            "url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://example.com"}),
            "file_type": forms.TextInput(attrs={"class": "form-control", "placeholder": "pdf, text, html"}),
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 8,
                    "placeholder": "Paste plain text content here when not uploading a PDF.",
                }
            ),
        }

    def clean(self) -> dict[str, object]:
        cleaned_data = super().clean()
        pdf_file = cleaned_data.get("pdf_file")
        content = (cleaned_data.get("content") or "").strip()

        if not pdf_file and not content:
            raise forms.ValidationError("Provide either a PDF file or document text.")

        if content:
            cleaned_data["content"] = content

        return cleaned_data


class DocumentProcessingForm(forms.Form):
    """Configure synthetic dataset generation from processed document text."""

    class TestType(TextChoices):
        REAL = "real", "Real Test"
        MOCKUP = "mockup", "Mock-up Test"

    test_type = forms.ChoiceField(
        choices=TestType.choices,
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Test Type",
    )

    instruction_prompt = forms.CharField(
        label="Instruction Prompt",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 5,
                "cols": 35,
                "placeholder": "Add an instruction prompt to explain how the language model should behave",
            }
        ),
    )

    num_paragraphs = forms.IntegerField(
        label="Number of Paragraphs",
        min_value=1,
        max_value=200,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    num_questions = forms.IntegerField(
        label="Number of Questions",
        min_value=1,
        max_value=500,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    def clean_instruction_prompt(self) -> str:
        return (self.cleaned_data.get("instruction_prompt") or "").strip()


# Backward-compatible alias for legacy naming used in lmforge.
DocumentForm = SourceDocumentForm
