from studio.application.services.training_service import (
    TrainingExecutionResult,
    TrainingService,
)
from studio.domain.models import TrainingRun


def test_assemble_config_normalizes_input_payload():
    service = TrainingService()

    config = service.assemble_config(
        {
            "model_name": "meta-llama/Llama-3-8B",
            "learning_rate": "1e-4",
            "num_epochs": "4",
            "batch_size": "2",
            "gradient_checkpointing": "on",
            "use_lora": "true",
            "use_qlora": "1",
            "fp16": "on",
            "bf16": "on",
            "train_test_split_ratio": "0.2",
        }
    )

    assert config.model_name == "meta-llama/Llama-3-8B"
    assert config.learning_rate == 1e-4
    assert config.num_epochs == 4
    assert config.batch_size == 2
    assert config.gradient_checkpointing is True
    assert config.use_lora is True
    assert config.use_qlora is True
    assert config.fp16 is True
    assert config.bf16 is True
    assert config.train_test_split_ratio == 0.2


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

    monkeypatch.setattr("studio.application.services.training_service.validate_training_run", _validate)
    cfg = TrainingRun(model_name="gpt2")
    service.validate_training_config(cfg, model_size=10)
    assert seen == {"model_size": 10, "name": "gpt2"}


def test_resolve_precision_qlora_disables_fp16_bf16():
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


def test_orchestrate_training_hands_normalized_config_to_executor_and_persists():
    service = TrainingService()

    class _Executor:
        def __init__(self):
            self.received = None

        def execute(self, *, config, precision, target_modules):
            self.received = (config, precision, target_modules)
            return TrainingExecutionResult(ok=True, status="completed", detail="ok", metadata={"job_id": "j-1"})

    class _Store:
        def __init__(self):
            self.saved = None

        def save(self, **kwargs):
            self.saved = kwargs
            return {"id": "tr-1", "status": kwargs["execution"].status}

    executor = _Executor()
    store = _Store()

    result = service.orchestrate_training(
        {
            "model_name": "meta-llama/Llama-3-8B",
            "train_test_split_ratio": "0.1",
            "use_qlora": "on",
            "fp16": "on",
            "bf16": "on",
        },
        executor=executor,
        result_store=store,
    )

    assert result.ok is True
    assert executor.received is not None
    cfg, precision, target_modules = executor.received
    assert cfg.model_name == "meta-llama/Llama-3-8B"
    assert cfg.fp16 is False
    assert cfg.bf16 is False
    assert precision == "4bit-qlora"
    assert target_modules == ["q_proj", "v_proj"]
    assert result.persisted_record == {"id": "tr-1", "status": "completed"}
    assert store.saved["failure_kind"] is None


def test_orchestrate_training_records_execution_failure_kind_when_executor_raises():
    service = TrainingService()

    class _Executor:
        def execute(self, **_kwargs):
            raise RuntimeError("trainer crashed")

    class _Store:
        def __init__(self):
            self.saved = None

        def save(self, **kwargs):
            self.saved = kwargs
            return {"id": "tr-2", "status": kwargs["execution"].status}

    store = _Store()
    result = service.orchestrate_training(
        {
            "model_name": "gpt2",
            "train_test_split_ratio": "0.1",
        },
        executor=_Executor(),
        result_store=store,
    )

    assert result.ok is False
    assert result.failure_kind == "execution_exception"
    assert result.execution.status == "failed"
    assert "trainer crashed" in result.execution.detail
    assert store.saved["failure_kind"] == "execution_exception"


def test_orchestrate_training_maps_prepare_validation_failures_without_raising():
    service = TrainingService()

    class _Executor:
        def execute(self, **_kwargs):  # pragma: no cover - should never execute on validation failure
            raise AssertionError("executor should not run when config is invalid")

    result = service.orchestrate_training(
        {
            "model_name": "gpt2",
            "train_test_split_ratio": "2",
        },
        executor=_Executor(),
    )

    assert result.ok is False
    assert result.failure_kind == "validation_error"
    assert result.execution.status == "invalid_config"
    assert "train_test_split_ratio" in result.execution.detail
