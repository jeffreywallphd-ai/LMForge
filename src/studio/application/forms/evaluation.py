"""Application-level forms for evaluation workflows."""

from __future__ import annotations

from django import forms


class EvaluationRunForm(forms.Form):
    """Collect basic evaluation configuration from a web request."""

    model_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-control"}))
    dataset_artifact_id = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={"class": "form-control"}))
    score_threshold = forms.FloatField(
        min_value=0.0,
        max_value=1.0,
        initial=0.5,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )

    def clean_model_name(self) -> str:
        return self.cleaned_data["model_name"].strip()
