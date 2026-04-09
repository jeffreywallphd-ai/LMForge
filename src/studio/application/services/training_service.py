"""Application service: training configuration, orchestration, and persistence boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from studio.domain.models.training_runs import TrainingRun
from studio.domain.policies.training_rules import validate_training_run


TrainingConfig = TrainingRun


@dataclass(slots=True)
class TrainingExecutionResult:
    ok: bool
    status: str
    detail: str = ""
    metadata: dict[str, Any] | None = None


@dataclass(slots=True)
class TrainingOrchestrationResult:
    ok: bool
    config: TrainingConfig
    model_size: int
    resolved_precision: str
    target_modules: list[str]
    execution: TrainingExecutionResult
    persisted_record: dict[str, Any] | None
    failure_kind: str | None = None


class TrainingExecutor(Protocol):
    def execute(self, *, config: TrainingConfig, precision: str, target_modules: list[str]) -> TrainingExecutionResult: ...


class TrainingResultStore(Protocol):
    def save(
        self,
        *,
        config: TrainingConfig,
        model_size: int,
        precision: str,
        target_modules: list[str],
        execution: TrainingExecutionResult,
        failure_kind: str | None,
    ) -> dict[str, Any]: ...


class TrainingService:
    """Core training utilities and orchestration boundary."""

    _manual_model_sizes = {
        "meta-llama/Llama-3-3B": 3_000_000_000,
        "meta-llama/Llama-3.2-3B-Instruct": 3_000_000_000,
        "meta-llama/Llama-2-7b-hf": 7_000_000_000,
        "meta-llama/Llama-3-8B": 8_000_000_000,
        "meta-llama/Llama-2-13b-hf": 13_000_000_000,
        "google/gemma-2-2b-it": 2_000_000_000,
    }

    def assemble_config(self, payload: dict[str, Any]) -> TrainingConfig:
        """Normalize request-style payload into a training config value object."""

        truthy = {True, "on", "true", "1", 1}
        return TrainingConfig(
            model_name=payload.get("model_name", "gpt2"),
            learning_rate=float(payload.get("learning_rate", 2e-5)),
            num_epochs=int(payload.get("num_epochs", 3)),
            batch_size=int(payload.get("batch_size", 1)),
            project_name=payload.get("project_name", "lmforge"),
            gradient_checkpointing=payload.get("gradient_checkpointing") in truthy,
            max_grad_norm=float(payload.get("max_grad_norm", 1.0)),
            use_lora=payload.get("use_lora") in truthy,
            use_qlora=payload.get("use_qlora") in truthy,
            fp16=payload.get("fp16") in truthy,
            bf16=payload.get("bf16") in truthy,
            weight_decay=float(payload.get("weight_decay", 0.01)),
            model_repo=payload.get("model_repo", "OpenFinAL/your-model-name"),
            dataset_name=payload.get("dataset_name", "FinGPT/fingpt-fiqa_qa"),
            train_test_split_ratio=float(payload.get("train_test_split_ratio", 0.1)),
        )

    def get_model_size(self, model_name: str, hf_token: str = "") -> int:
        from huggingface_hub import hf_hub_download
        from transformers import AutoConfig

        model_name_clean = model_name.lower()
        for key, size in self._manual_model_sizes.items():
            if key.lower() in model_name_clean:
                return size

        try:
            model_info = hf_hub_download(model_name, repo_type="model", filename="config.json", token=hf_token)
            model_config = AutoConfig.from_pretrained(model_info)
            if hasattr(model_config, "num_parameters"):
                return model_config.num_parameters()
        except Exception:
            return 0
        return 0

    def get_target_modules(self, model_name: str) -> list[str]:
        name = model_name.lower()
        if "llama" in name or "mistral" in name:
            return ["q_proj", "v_proj"]
        if "falcon" in name:
            return ["query_key_value", "dense"]
        if "bloom" in name:
            return ["query_key_value"]
        if "gpt" in name:
            return ["c_attn"]
        return ["q_proj", "v_proj"]

    def validate_training_config(self, config: TrainingConfig, model_size: int) -> None:
        validate_training_run(config, model_size=model_size)

    def resolve_precision(self, config: TrainingConfig):
        import torch

        if config.use_qlora:
            config.fp16 = False
            config.bf16 = False
            return None
        if config.fp16:
            config.bf16 = False
            return torch.float16
        if config.bf16:
            config.fp16 = False
            return torch.bfloat16
        return torch.float32

    def prepare_training(self, config: TrainingConfig, *, hf_token: str = "") -> tuple[int, str, list[str]]:
        """Resolve normalized config + validation into an executable plan tuple."""

        model_size = self.get_model_size(config.model_name, hf_token=hf_token)
        self.validate_training_config(config, model_size=model_size)
        dtype = self.resolve_precision(config)
        precision_name = "fp32" if dtype is None else str(dtype).replace("torch.", "")
        if config.use_qlora:
            precision_name = "4bit-qlora"
        return model_size, precision_name, self.get_target_modules(config.model_name)

    def orchestrate_training(
        self,
        payload: dict[str, Any],
        *,
        executor: TrainingExecutor,
        result_store: TrainingResultStore | None = None,
        hf_token: str = "",
    ) -> TrainingOrchestrationResult:
        """Run explicit lifecycle: assemble config -> prepare/validate -> execute -> persist."""

        config = self.assemble_config(payload)
        model_size, resolved_precision, target_modules = self.prepare_training(config, hf_token=hf_token)

        failure_kind: str | None = None
        try:
            execution = executor.execute(
                config=config,
                precision=resolved_precision,
                target_modules=target_modules,
            )
            if not execution.ok:
                failure_kind = "execution_error"
        except Exception as exc:  # pragma: no cover - classification path tested by assertion on returned result
            execution = TrainingExecutionResult(
                ok=False,
                status="failed",
                detail=str(exc),
                metadata={},
            )
            failure_kind = "execution_exception"

        persisted_record: dict[str, Any] | None = None
        if result_store is not None:
            persisted_record = result_store.save(
                config=config,
                model_size=model_size,
                precision=resolved_precision,
                target_modules=target_modules,
                execution=execution,
                failure_kind=failure_kind,
            )

        return TrainingOrchestrationResult(
            ok=execution.ok,
            config=config,
            model_size=model_size,
            resolved_precision=resolved_precision,
            target_modules=target_modules,
            execution=execution,
            persisted_record=persisted_record,
            failure_kind=failure_kind,
        )
