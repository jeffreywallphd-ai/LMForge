"""Application-level forms for training workflows."""

from __future__ import annotations

from django import forms


class TrainingRunForm(forms.Form):
    """Collect high-level model-training settings from a web request."""

    model_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-control"}))
    dataset_artifact_id = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={"class": "form-control"}))
    epochs = forms.IntegerField(min_value=1, max_value=100, initial=3, widget=forms.NumberInput(attrs={"class": "form-control"}))
    batch_size = forms.IntegerField(min_value=1, max_value=1024, initial=16, widget=forms.NumberInput(attrs={"class": "form-control"}))
    learning_rate = forms.FloatField(min_value=0.0, initial=5e-5, widget=forms.NumberInput(attrs={"class": "form-control", "step": "any"}))

    def clean_model_name(self) -> str:
        return self.cleaned_data["model_name"].strip()
