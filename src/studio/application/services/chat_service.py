"""Application service: chat inference and conversation orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any
import uuid

from studio.domain.models import Conversation


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
            raise ChatInputValidationError("model_name is required")
        if not (1 <= self.min_length <= self.max_length <= 1024):
            raise ChatInputValidationError("min_length must be <= max_length and within valid range")
        if not (0 <= self.top_p <= 1):
            raise ChatInputValidationError("top_p must be between 0 and 1")
        if self.top_k < 0:
            raise ChatInputValidationError("top_k must be a non-negative integer")


class ChatErrorCode(str, Enum):
    INVALID_INPUT = "invalid_input"
    MODEL_SESSION_UNAVAILABLE = "model_session_unavailable"
    EXECUTION_FAILURE = "execution_failure"
    INTERNAL_FAILURE = "internal_failure"


class ChatServiceError(Exception):
    code: ChatErrorCode = ChatErrorCode.INTERNAL_FAILURE


class ChatInputValidationError(ChatServiceError, ValueError):
    code = ChatErrorCode.INVALID_INPUT


class ModelSessionUnavailableError(ChatServiceError):
    code = ChatErrorCode.MODEL_SESSION_UNAVAILABLE


class ChatExecutionError(ChatServiceError):
    code = ChatErrorCode.EXECUTION_FAILURE


@dataclass(frozen=True, slots=True)
class ChatModelSession:
    model: Any
    tokenizer: Any
    device: Any


class ChatModelSessionProvider:
    """Centralized model/session loading and in-memory reuse for chat."""

    def __init__(self) -> None:
        self._model_cache: dict[str, ChatModelSession] = {}

    def get_model_session(self, model_name: str) -> ChatModelSession:
        if model_name in self._model_cache:
            return self._model_cache[model_name]

        try:
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
        except Exception as exc:  # noqa: BLE001
            raise ModelSessionUnavailableError(f"Unable to load model session for '{model_name}': {exc}") from exc

        tokenizer.pad_token = tokenizer.eos_token
        model.resize_token_embeddings(len(tokenizer))
        model.to(device)
        session = ChatModelSession(model=model, tokenizer=tokenizer, device=device)
        self._model_cache[model_name] = session
        return session


@dataclass(frozen=True, slots=True)
class ChatTurnRequest:
    session_id: str
    message: str
    generation_config: ChatGenerationConfig


@dataclass(frozen=True, slots=True)
class ChatTurnResult:
    user_message: str
    bot_response: str
    generation_params: dict[str, Any]


class ChatService:
    """Service extracted from the legacy `lmforge_core.views.chatbot` module."""

    def __init__(self, *, model_session_provider: ChatModelSessionProvider | None = None) -> None:
        self._model_session_provider = model_session_provider or ChatModelSessionProvider()

    def create_session_id(self) -> str:
        return str(uuid.uuid4())

    def list_sessions(self) -> list[str]:
        return list(Conversation.objects.values_list("session_id", flat=True).distinct())

    def get_session_messages(self, session_id: str):
        return Conversation.objects.filter(session_id=session_id).order_by("timestamp")

    def save_message(self, *, session_id: str, message: str, is_user: bool) -> Conversation:
        return Conversation.objects.create(session_id=session_id, message=message, is_user=is_user)

    def parse_turn_request(self, session_id: str, payload: dict[str, Any]) -> ChatTurnRequest:
        message = str(payload.get("message", "")).strip()
        if not message:
            raise ChatInputValidationError('Both "message" and "model_name" are required.')

        generation_config = self._parse_generation_config(payload)
        generation_config.validate()
        return ChatTurnRequest(session_id=session_id, message=message, generation_config=generation_config)

    @staticmethod
    def _parse_generation_config(payload: dict[str, Any]) -> ChatGenerationConfig:
        try:
            return ChatGenerationConfig(
                model_name=str(payload.get("model_name", "")).strip(),
                max_length=int(payload.get("max_length", 200)),
                min_length=int(payload.get("min_length", 100)),
                top_k=int(payload.get("top_k", 50)),
                top_p=float(payload.get("top_p", 0.95)),
                no_repeat_ngram_size=int(payload.get("no_repeat_ngram_size", 0)),
                max_new_tokens=int(payload.get("max_new_tokens", 300)),
            )
        except (TypeError, ValueError) as exc:
            raise ChatInputValidationError(
                "Invalid parameters. Ensure max_length, min_length, and top_k are integers, and top_p is a float."
            ) from exc

    def generate_response(self, prompt: str, config: ChatGenerationConfig) -> str:
        config.validate()

        model_session = self._model_session_provider.get_model_session(config.model_name)
        try:
            inputs = model_session.tokenizer(
                prompt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=128,
            ).to(model_session.device)

            outputs = model_session.model.generate(
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
                pad_token_id=model_session.tokenizer.pad_token_id,
            )
            return model_session.tokenizer.decode(outputs[0], skip_special_tokens=True)
        except Exception as exc:  # noqa: BLE001
            raise ChatExecutionError(f"Error during response generation: {exc}") from exc

    def run_chat_turn(self, *, session_id: str, payload: dict[str, Any]) -> ChatTurnResult:
        request = self.parse_turn_request(session_id, payload)
        bot_response = self.generate_response(request.message, request.generation_config)
        self.save_message(session_id=session_id, message=request.message, is_user=True)
        self.save_message(session_id=session_id, message=bot_response, is_user=False)
        return ChatTurnResult(
            user_message=request.message,
            bot_response=bot_response,
            generation_params=asdict(request.generation_config),
        )
