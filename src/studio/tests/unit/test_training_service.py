import types

from src.studio.application.services.training_service import TrainingService
from src.studio.domain.models.training_runs import TrainingRun


def test_get_model_size_uses_manual_map():
    service = TrainingService()
    assert service.get_model_size("meta-llama/Llama-3-8B") == 8_000_000_000


def test_get_model_size_returns_zero_when_hf_fails(monkeypatch):
    service = TrainingService()

    def _boom(*_args, **_kwargs):
        raise RuntimeError("down")

    monkeypatch.setattr("huggingface_hub.hf_hub_download", _boom)
    assert service.get_model_size("custom/model") == 0


def test_get_model_size_reads_num_parameters(monkeypatch):
    service = TrainingService()

    monkeypatch.setattr("huggingface_hub.hf_hub_download", lambda *a, **k: "/tmp/config.json")

    class _Cfg:
        def num_parameters(self):
            return 123

    monkeypatch.setattr("transformers.AutoConfig.from_pretrained", lambda *_a, **_k: _Cfg())
    assert service.get_model_size("custom/model") == 123


def test_get_target_modules_variants():
    service = TrainingService()
    assert service.get_target_modules("mistral-7b") == ["q_proj", "v_proj"]
    assert service.get_target_modules("falcon-7b") == ["query_key_value", "dense"]
    assert service.get_target_modules("bloom-560m") == ["query_key_value"]
    assert service.get_target_modules("gpt2") == ["c_attn"]


def test_validate_training_config_delegates(monkeypatch):
    service = TrainingService()
    seen = {}

    def _validate(config, *, model_size):
        seen["model_size"] = model_size
        seen["name"] = config.model_name

    monkeypatch.setattr("src.studio.application.services.training_service.validate_training_run", _validate)
    cfg = TrainingRun(model_name="gpt2")
    service.validate_training_config(cfg, model_size=10)
    assert seen == {"model_size": 10, "name": "gpt2"}


def test_resolve_precision_qlora_disables_fp16_bf16(monkeypatch):
    service = TrainingService()
    config = TrainingRun(model_name="gpt2", use_qlora=True, fp16=True, bf16=True)

    dtype = service.resolve_precision(config)

    assert dtype is None
    assert config.fp16 is False
    assert config.bf16 is False


def test_resolve_precision_prefers_fp16_then_bf16():
    service = TrainingService()

    fp16_cfg = TrainingRun(model_name="gpt2", fp16=True, bf16=True)
    fp16_dtype = service.resolve_precision(fp16_cfg)
    assert str(fp16_dtype).endswith("float16")
    assert fp16_cfg.bf16 is False

    bf16_cfg = TrainingRun(model_name="gpt2", fp16=False, bf16=True)
    bf16_dtype = service.resolve_precision(bf16_cfg)
    assert str(bf16_dtype).endswith("bfloat16")
