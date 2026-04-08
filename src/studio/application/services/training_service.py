"""Application service: model training configuration and execution helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TrainingConfig:
    model_name: str
    learning_rate: float = 2e-5
    num_epochs: int = 3
    batch_size: int = 1
    project_name: str = "lmforge"
    gradient_checkpointing: bool = False
    max_grad_norm: float = 1.0
    use_lora: bool = False
    use_qlora: bool = False
    fp16: bool = False
    bf16: bool = False
    weight_decay: float = 0.01
    model_repo: str = "OpenFinAL/your-model-name"
    dataset_name: str = "FinGPT/fingpt-fiqa_qa"
    train_test_split_ratio: float = 0.1


class TrainingService:
    """Core training utilities migrated from `model_training.py`."""

    _manual_model_sizes = {
        "meta-llama/Llama-3-3B": 3_000_000_000,
        "meta-llama/Llama-3.2-3B-Instruct": 3_000_000_000,
        "meta-llama/Llama-2-7b-hf": 7_000_000_000,
        "meta-llama/Llama-3-8B": 8_000_000_000,
        "meta-llama/Llama-2-13b-hf": 13_000_000_000,
        "google/gemma-2-2b-it": 2_000_000_000,
    }

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
        if config.use_qlora and model_size < 1_300_000_000:
            raise ValueError("QLoRA can only be applied to models with 1.3B parameters or more")
        if not (0 < config.train_test_split_ratio < 1):
            raise ValueError("train_test_split_ratio must be in range (0, 1)")
        if config.batch_size <= 0:
            raise ValueError("batch_size must be greater than 0")

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
