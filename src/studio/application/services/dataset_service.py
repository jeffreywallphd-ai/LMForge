"""Application service: dataset preparation, generation orchestration, and result normalization."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from studio.application.services.document_service import DocumentService
from studio.domain.models import SourceDocument
from studio.domain.policies.dataset_rules import validate_dataset_request


@dataclass(slots=True)
class DatasetGenerationRequest:
    """Framework-agnostic input contract for dataset generation."""

    document_ids: list[int]
    questions_per_chunk: int = 1
    chunk_limit: int = 1
    instruction_prompt: str = ""


@dataclass(slots=True)
class DatasetGenerationFailure:
    """Normalized business error returned by dataset generation service."""

    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DatasetGenerationResult:
    """Structured service outcome consumable by API and web presentation layers."""

    ok: bool
    records: list[dict[str, str]] = field(default_factory=list)
    normalized_request: DatasetGenerationRequest | None = None
    chunk_count: int = 0
    processed_chunk_count: int = 0
    persisted_artifact: dict[str, Any] | None = None
    failure: DatasetGenerationFailure | None = None


class DatasetService:
    """Business-layer dataset generator independent from HTTP forms or request objects."""

    _JSON_ARRAY_PATTERN = re.compile(r"\[\s*\{.*?\}\s*\]", re.DOTALL)

    def __init__(self, document_service: DocumentService | None = None) -> None:
        self.document_service = document_service or DocumentService()

    def get_documents_text(self, document_ids: list[int]) -> str:
        documents = SourceDocument.objects.filter(id__in=document_ids)
        return "\n\n".join([doc.content for doc in documents])

    def normalize_request(self, request: DatasetGenerationRequest) -> DatasetGenerationRequest:
        """Normalize primitive values from any caller before business execution."""
        normalized_document_ids = sorted({int(doc_id) for doc_id in request.document_ids if int(doc_id) > 0})
        return DatasetGenerationRequest(
            document_ids=normalized_document_ids,
            questions_per_chunk=max(1, int(request.questions_per_chunk)),
            chunk_limit=max(1, int(request.chunk_limit)),
            instruction_prompt=(request.instruction_prompt or "").strip(),
        )

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

    def _normalize_records(self, records: list[dict[str, Any]]) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []
        for row in records:
            question = str(row.get("question", "")).strip()
            answer = str(row.get("answer", "")).strip()
            if not question or not answer:
                continue
            cleaned = {"question": question, "answer": answer}
            if "instruction" in row:
                cleaned["instruction"] = str(row.get("instruction", "")).strip()
            normalized.append(cleaned)
        return normalized

    def generate_dataset(
        self,
        request: DatasetGenerationRequest,
        *,
        model_name: str = "gpt2",
        persist_artifact: Callable[[list[dict[str, str]], DatasetGenerationRequest], dict[str, Any] | None] | None = None,
    ) -> DatasetGenerationResult:
        """Generate dataset records using a framework-light contract and optional persistence handoff."""
        try:
            normalized_request = self.normalize_request(request)
            validate_dataset_request(
                document_ids=normalized_request.document_ids,
                questions_per_chunk=normalized_request.questions_per_chunk,
                chunk_limit=normalized_request.chunk_limit,
            )
        except (TypeError, ValueError) as exc:
            return DatasetGenerationResult(
                ok=False,
                failure=DatasetGenerationFailure(code="validation_error", message=str(exc)),
            )

        text = self.get_documents_text(normalized_request.document_ids)
        chunks = self.document_service.split_text(text=text, max_tokens=256)
        records: list[dict[str, Any]] = []
        processed_chunk_count = 0

        try:
            for chunk in chunks[: normalized_request.chunk_limit]:
                output = self._model_chat(
                    self.build_prompt(chunk, normalized_request.questions_per_chunk, normalized_request.instruction_prompt),
                    model_name=model_name,
                )
                match = self._JSON_ARRAY_PATTERN.search(output)
                if not match:
                    continue
                processed_chunk_count += 1
                try:
                    parsed = json.loads(match.group(0))
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, list):
                    records.extend(parsed)
        except Exception as exc:  # noqa: BLE001
            return DatasetGenerationResult(
                ok=False,
                failure=DatasetGenerationFailure(code="execution_error", message=str(exc)),
            )

        normalized_records = self._normalize_records(records)

        persisted_artifact = None
        if persist_artifact is not None:
            try:
                persisted_artifact = persist_artifact(normalized_records, normalized_request) or None
            except Exception as exc:  # noqa: BLE001
                return DatasetGenerationResult(
                    ok=False,
                    failure=DatasetGenerationFailure(code="persistence_error", message=str(exc)),
                )

        return DatasetGenerationResult(
            ok=True,
            records=normalized_records,
            normalized_request=normalized_request,
            chunk_count=len(chunks),
            processed_chunk_count=processed_chunk_count,
            persisted_artifact=persisted_artifact,
        )

    def generate_qa_pairs(self, request: DatasetGenerationRequest, *, model_name: str = "gpt2") -> list[dict]:
        """Backward-compatible shim that returns only generated records."""
        result = self.generate_dataset(request, model_name=model_name)
        if not result.ok:
            raise ValueError(result.failure.message if result.failure else "Dataset generation failed")
        return result.records
