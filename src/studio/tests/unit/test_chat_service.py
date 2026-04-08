import pytest

from src.studio.application.services.chat_service import ChatGenerationConfig


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
    with pytest.raises(ValueError, match=message):
        cfg.validate()
