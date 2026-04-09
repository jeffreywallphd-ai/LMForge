from __future__ import annotations

import pytest

from studio.application.services.chat_service import (
    ChatExecutionError,
    ChatGenerationConfig,
    ChatInputValidationError,
    ChatModelSession,
    ChatModelSessionProvider,
    ChatService,
    ModelSessionUnavailableError,
)


class _FakeInputs(dict):
    def to(self, _device):
        return self


class _FakeTokenizer:
    eos_token = "<eos>"
    pad_token_id = 99

    def __len__(self):
        return 123

    def __call__(self, *_args, **_kwargs):
        return _FakeInputs({"input_ids": [1, 2], "attention_mask": [1, 1]})

    def decode(self, _output, skip_special_tokens=True):
        assert skip_special_tokens is True
        return "decoded"


class _FakeModel:
    def resize_token_embeddings(self, _length):
        return None

    def to(self, _device):
        return self

    def generate(self, *_args, **_kwargs):
        return [[7, 8]]



class _FakeAutoTokenizer:
    calls: list[tuple[str, dict]] = []

    @classmethod
    def from_pretrained(cls, model_name, **kwargs):
        cls.calls.append((model_name, kwargs))
        return _FakeTokenizer()


class _FakeAutoModel:
    calls: list[tuple[str, dict]] = []

    @classmethod
    def from_pretrained(cls, model_name, **kwargs):
        cls.calls.append((model_name, kwargs))
        return _FakeModel()


def test_chat_generation_config_validate_success():
    cfg = ChatGenerationConfig(model_name="gpt2", min_length=10, max_length=20, top_p=0.5, top_k=0)
    cfg.validate()


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"model_name": ""}, "model_name is required"),
        ({"model_name": "m", "min_length": 50, "max_length": 10}, "min_length"),
        ({"model_name": "m", "top_p": 1.2}, "top_p"),
        ({"model_name": "m", "top_k": -1}, "top_k"),
    ],
)
def test_chat_generation_config_validate_failures(kwargs, message):
    cfg = ChatGenerationConfig(**kwargs)
    with pytest.raises(ChatInputValidationError, match=message):
        cfg.validate()


def test_chat_model_session_provider_reuses_loaded_session(monkeypatch):
    provider = ChatModelSessionProvider()

    import sys

    fake_torch = type("Torch", (), {"cuda": type("Cuda", (), {"is_available": staticmethod(lambda: False)}), "device": staticmethod(lambda name: name)})
    fake_transformers = type(
        "Transformers",
        (),
        {"AutoTokenizer": _FakeAutoTokenizer, "AutoModelForCausalLM": _FakeAutoModel},
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)

    first = provider.get_model_session("gpt2")
    second = provider.get_model_session("gpt2")

    assert isinstance(first, ChatModelSession)
    assert first is second
    assert len(_FakeAutoTokenizer.calls) == 1
    assert len(_FakeAutoModel.calls) == 1


def test_chat_model_session_provider_wraps_loading_failures(monkeypatch):
    provider = ChatModelSessionProvider()

    import sys

    class _BrokenAutoTokenizer:
        @classmethod
        def from_pretrained(cls, *_args, **_kwargs):
            raise RuntimeError("boom")

    fake_torch = type("Torch", (), {"cuda": type("Cuda", (), {"is_available": staticmethod(lambda: False)}), "device": staticmethod(lambda name: name)})
    fake_transformers = type(
        "Transformers",
        (),
        {"AutoTokenizer": _BrokenAutoTokenizer, "AutoModelForCausalLM": _FakeAutoModel},
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)

    with pytest.raises(ModelSessionUnavailableError, match="Unable to load model session"):
        provider.get_model_session("gpt2")


def test_chat_service_run_chat_turn_saves_messages(monkeypatch):
    class _Provider:
        def get_model_session(self, _model_name):
            return ChatModelSession(model=_FakeModel(), tokenizer=_FakeTokenizer(), device="cpu")

    service = ChatService(model_session_provider=_Provider())

    saved_messages = []

    def _save_message(*, session_id: str, message: str, is_user: bool):
        saved_messages.append((session_id, message, is_user))
        return None

    monkeypatch.setattr(service, "save_message", _save_message)

    result = service.run_chat_turn(session_id="s1", payload={"message": "Hi", "model_name": "gpt2"})

    assert result.user_message == "Hi"
    assert result.bot_response == "decoded"
    assert len(saved_messages) == 2
    assert saved_messages[0] == ("s1", "Hi", True)
    assert saved_messages[1] == ("s1", "decoded", False)


def test_chat_service_parse_turn_request_validates_payload():
    service = ChatService(model_session_provider=object())

    with pytest.raises(ChatInputValidationError, match='Both "message" and "model_name" are required'):
        service.parse_turn_request("s1", {"message": "", "model_name": "gpt2"})

    with pytest.raises(ChatInputValidationError, match="Invalid parameters"):
        service.parse_turn_request("s1", {"message": "hi", "model_name": "gpt2", "max_length": "nope"})


def test_chat_service_generate_response_wraps_model_failures():
    class _BadModel:
        def generate(self, *_args, **_kwargs):
            raise RuntimeError("no generation")

    class _Provider:
        def get_model_session(self, _model_name):
            return ChatModelSession(model=_BadModel(), tokenizer=_FakeTokenizer(), device="cpu")

    service = ChatService(model_session_provider=_Provider())

    with pytest.raises(ChatExecutionError, match="Error during response generation"):
        service.generate_response("prompt", ChatGenerationConfig(model_name="gpt2"))
