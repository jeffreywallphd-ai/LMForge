"""Application service: model evaluation and scoring."""

from __future__ import annotations

from studio.domain.models.evaluation_runs import EvaluationRun
from studio.domain.policies.evaluation_rules import validate_evaluation_run


EvaluationConfig = EvaluationRun


class EvaluationService:
    """Evaluation logic migrated from `lmforge_core.views.model_statistics`."""

    def validate_constraints(self, config: EvaluationConfig) -> None:
        validate_evaluation_run(config)

    def cal_sts_score(self, input1: str, input2: str):
        from sentence_transformers import CrossEncoder

        if not isinstance(input1, str) or not isinstance(input2, str):
            return "nan"
        model = CrossEncoder("cross-encoder/stsb-distilroberta-base")
        return round(model.predict([[input1, input2]])[0], 4)

    def model_stats(self, prompt: str, references: list[str], config: EvaluationConfig) -> dict:
        self.validate_constraints(config)

        import torch
        from evaluate import load
        from transformers import AutoModelForCausalLM, AutoTokenizer

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if any(token in config.model_name.lower() for token in ("llama", "meta", "openelm")):
            tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-hf", use_fast=False, trust_remote_code=True)
            tokenizer.add_bos_token = True
            model = AutoModelForCausalLM.from_pretrained(config.model_name, trust_remote_code=True)
        else:
            tokenizer = AutoTokenizer.from_pretrained(config.model_name, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(config.model_name, trust_remote_code=True)

        tokenizer.pad_token = tokenizer.eos_token
        model.resize_token_embeddings(len(tokenizer))
        model.to(device)

        inputs = tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=128).to(device)
        outputs = model.generate(
            inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            do_sample=True,
            top_k=config.top_k,
            top_p=config.top_p,
            num_return_sequences=1,
            max_new_tokens=config.max_new_tokens,
            no_repeat_ngram_size=config.no_repeat_ngrams,
            pad_token_id=tokenizer.pad_token_id,
        )

        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        predictions = [str(response)]
        rouge_scores = load("rouge", trusted_remote_code=True).compute(predictions=predictions, references=references)
        bertscore_scores = load("bertscore", trusted_remote_code=True).compute(
            predictions=predictions,
            references=references,
            lang="en",
            device=device,
        )
        sts_score = self.cal_sts_score(response, references[0])

        return {
            "ROUGE1": rouge_scores.get("rouge1", 0),
            "ROUGE2": rouge_scores.get("rouge2", 0),
            "ROUGEL": rouge_scores.get("rougeL", 0),
            "ROUGELSUM": rouge_scores.get("rougeLsum", 0),
            "BERTScoreF1": bertscore_scores["f1"][0],
            "BERTScorePrecision": bertscore_scores["precision"][0],
            "BERTScoreRecall": bertscore_scores["recall"][0],
            "STSScore": sts_score,
        }
