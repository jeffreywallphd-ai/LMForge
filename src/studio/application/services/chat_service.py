"""Application service: chat inference and conversation orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import uuid

from src.studio.domain.models.conversations import Conversation


@dataclass(slots=True)
class ChatGenerationConfig:
    """Model generation parameters aligned with the legacy chatbot endpoint."""

    model_name: str
    max_length: int = 200
    min_length: int = 100
    top_k: int = 50
    top_p: float = 0.95
    no_repeat_ngram_size: int = 0
    max_new_tokens: int = 300

    def validate(self) -> None:
        if not self.model_name:
            raise ValueError("model_name is required")
        if not (1 <= self.min_length <= self.max_length <= 1024):
            raise ValueError("min_length must be <= max_length and within valid range")
        if not (0 <= self.top_p <= 1):
            raise ValueError("top_p must be between 0 and 1")
        if self.top_k < 0:
            raise ValueError("top_k must be a non-negative integer")


class ChatService:
    """Service extracted from the legacy `lmforge_core.views.chatbot` module."""

    def __init__(self) -> None:
        self._model_cache: dict[str, tuple[Any, Any]] = {}

    def create_session_id(self) -> str:
        return str(uuid.uuid4())

    def list_sessions(self) -> list[str]:
        return list(Conversation.objects.values_list("session_id", flat=True).distinct())

    def get_session_messages(self, session_id: str):
        return Conversation.objects.filter(session_id=session_id).order_by("timestamp")

    def save_message(self, *, session_id: str, message: str, is_user: bool) -> Conversation:
        return Conversation.objects.create(session_id=session_id, message=message, is_user=is_user)

    def _load_model_and_tokenizer(self, model_name: str):
        if model_name in self._model_cache:
            return self._model_cache[model_name]

        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if any(token in model_name.lower() for token in ("llama", "meta", "openelm")):
            tokenizer = AutoTokenizer.from_pretrained(
                "meta-llama/Llama-2-7b-hf", use_fast=False, trust_remote_code=True
            )
            tokenizer.add_bos_token = True
            model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)
        else:
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)

        tokenizer.pad_token = tokenizer.eos_token
        model.resize_token_embeddings(len(tokenizer))
        model.to(device)
        self._model_cache[model_name] = (model, tokenizer)
        return model, tokenizer

    def generate_response(self, prompt: str, config: ChatGenerationConfig) -> str:
        config.validate()

        import torch

        model, tokenizer = self._load_model_and_tokenizer(config.model_name)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=128,
        ).to(device)

        outputs = model.generate(
            inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_length=config.max_length,
            min_length=config.min_length,
            do_sample=True,
            top_k=config.top_k,
            top_p=config.top_p,
            no_repeat_ngram_size=config.no_repeat_ngram_size,
            max_new_tokens=config.max_new_tokens,
            num_return_sequences=1,
            pad_token_id=tokenizer.pad_token_id,
        )
        return tokenizer.decode(outputs[0], skip_special_tokens=True)
