"""Application workflow: model evaluation."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from datasets import Dataset, load_dataset

from src.studio.application.services.evaluation_service import EvaluationConfig, EvaluationService


@dataclass(slots=True)
class ModelEvaluationWorkflowRequest:
    models: list[str]
    dataset_url: str | None = None
    dataset_file_path: str | None = None
    num_questions: int = 10
    max_length: int = 200
    min_length: int = 100
    top_k: int = 50
    top_p: float = 0.95
    max_new_tokens: int = 300
    no_repeat_ngrams: int = 0


class ModelEvaluationWorkflow:
    """Loads evaluation data and computes aggregate metrics per model."""

    def __init__(self, evaluation_service: EvaluationService | None = None) -> None:
        self.evaluation_service = evaluation_service or EvaluationService()

    def _load_dataframe(self, request: ModelEvaluationWorkflowRequest) -> pd.DataFrame:
        if request.dataset_url:
            dataset = load_dataset(request.dataset_url)
            df = pd.DataFrame(dataset["train"])
        elif request.dataset_file_path:
            df = pd.read_csv(request.dataset_file_path)
            dataset = Dataset.from_pandas(df)
            df = pd.DataFrame(dataset)
        else:
            raise ValueError("Provide either dataset_url or dataset_file_path")

        possible_input_names = {"input", "Input", "question", "Question"}
        possible_output_names = {"output", "Output", "answer", "Answer"}

        input_col = next((col for col in df.columns if col in possible_input_names), None)
        output_col = next((col for col in df.columns if col in possible_output_names), None)

        if not input_col or not output_col:
            raise ValueError("Dataset must contain Input/Output or Question/Answer columns")

        df = df.dropna(subset=[input_col, output_col])
        if df.empty:
            raise ValueError("Dataset is empty after filtering")

        question_count = min(request.num_questions, len(df))
        sampled = df.sample(n=question_count, random_state=42)
        return sampled[[input_col, output_col]].rename(columns={input_col: "question", output_col: "reference"})

    def evaluate_models(self, request: ModelEvaluationWorkflowRequest) -> dict[str, dict]:
        if not request.models:
            raise ValueError("At least one model is required")

        sampled_df = self._load_dataframe(request)
        questions = sampled_df["question"].tolist()
        references = sampled_df["reference"].tolist()

        all_results: dict[str, dict] = {}

        for model_name in request.models:
            config = EvaluationConfig(
                model_name=model_name,
                max_length=request.max_length,
                min_length=request.min_length,
                top_k=request.top_k,
                top_p=request.top_p,
                max_new_tokens=request.max_new_tokens,
                no_repeat_ngrams=request.no_repeat_ngrams,
            )

            totals = {
                "ROUGE1": 0.0,
                "ROUGE2": 0.0,
                "ROUGEL": 0.0,
                "ROUGELSUM": 0.0,
                "BERTScoreF1": 0.0,
                "BERTScorePrecision": 0.0,
                "BERTScoreRecall": 0.0,
                "STSScore": 0.0,
            }

            for question, reference in zip(questions, references):
                scores = self.evaluation_service.model_stats(question, [reference], config)
                for key in totals:
                    totals[key] += float(scores[key])

            sample_size = max(1, len(questions))
            all_results[model_name] = {k: v / sample_size for k, v in totals.items()}

        return all_results
