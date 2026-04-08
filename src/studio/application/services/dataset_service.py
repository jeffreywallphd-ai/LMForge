"""Application service: dataset preparation and Q/A generation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from studio.application.services.document_service import DocumentService
from studio.domain.models.source_documents import SourceDocument


@dataclass(slots=True)
class DatasetGenerationRequest:
    document_ids: list[int]
    questions_per_chunk: int = 1
    chunk_limit: int = 1
    instruction_prompt: str = ""


class DatasetService:
    """Migrates logic from `generate_q_and_a.py` and dataset workflow views."""

    def __init__(self, document_service: DocumentService | None = None) -> None:
        self.document_service = document_service or DocumentService()

    def get_documents_text(self, document_ids: list[int]) -> str:
        documents = SourceDocument.objects.filter(id__in=document_ids)
        return "\n\n".join([doc.content for doc in documents])

    def build_prompt(self, chunk: str, questions_num: int, instruction_prompt: str = "") -> str:
        instruction_field = ""
        if instruction_prompt:
            instruction_field = f', "instruction": "{instruction_prompt.strip()}"'

        return (
            "You are a system that generates question-answer pairs in valid JSON only.\n\n"
            f"Instructions:\n- Generate exactly {questions_num} question-answer pairs.\n"
            "- Each answer must be 200 words or less\n"
            "- Output only a valid JSON array of objects.\n"
            "- No extra text, no comments, no markdown.\n\n"
            f"Input Text:\n\"\"\"{chunk}\"\"\"\n\n"
            "Output format:\n[\n"
            f'  {{"question": "What is ...?", "answer": "The answer is ..."{instruction_field}}}\n'
            "]\n\nRespond with only valid JSON."
        )

    def _model_chat(self, prompt: str, max_tokens: int = 256, model_name: str = "gpt2") -> str:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True).to(device)

        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        with torch.no_grad():
            output_tokens = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                pad_token_id=tokenizer.eos_token_id,
            )
        generated_tokens = output_tokens[0][len(inputs["input_ids"][0]) :]
        return tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()

    def generate_qa_pairs(self, request: DatasetGenerationRequest, *, model_name: str = "gpt2") -> list[dict]:
        text = self.get_documents_text(request.document_ids)
        chunks = self.document_service.split_text(text=text, max_tokens=256)
        results: list[dict] = []

        for chunk in chunks[: request.chunk_limit]:
            output = self._model_chat(
                self.build_prompt(chunk, request.questions_per_chunk, request.instruction_prompt),
                model_name=model_name,
            )
            match = re.search(r"\[\s*\{.*?\}\s*\]", output, re.DOTALL)
            if not match:
                continue
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, list):
                results.extend(parsed)
        return results
