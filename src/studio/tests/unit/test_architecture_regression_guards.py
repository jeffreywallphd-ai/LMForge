from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_ROOT = REPO_ROOT / "src" / "studio"


def _imports_for(relative_path: str) -> set[str]:
    module_path = SRC_ROOT / relative_path
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)

    return imports


def test_orchestration_heavy_api_paths_depend_on_workflows() -> None:
    """Guardrail: orchestration-heavy API handlers should depend on workflow boundaries."""

    training_imports = _imports_for("presentation/api/views/training.py")
    dataset_imports = _imports_for("presentation/api/views/datasets.py")

    assert "studio.application.workflows.model_training" in training_imports
    assert "studio.application.workflows.embedding_storage" in dataset_imports


def test_scraping_and_chat_api_paths_remain_service_backed() -> None:
    """Guardrail: chat/scraping remain thin service adapters instead of ad-hoc orchestration."""

    scraping_imports = _imports_for("presentation/api/views/scraping.py")
    chat_imports = _imports_for("presentation/api/views/chat.py")

    assert "studio.application.services.scraping_service" in scraping_imports
    assert "studio.application.services.chat_service" in chat_imports


def test_api_contract_integration_tests_exist_for_core_slices() -> None:
    """Guardrail: keep API contract coverage in place for core machine-facing slices."""

    expected = [
        REPO_ROOT / "src/studio/tests/integration/test_scraping_api.py",
        REPO_ROOT / "src/studio/tests/integration/test_presentation_api_chat_and_eval.py",
        REPO_ROOT / "src/studio/tests/integration/test_dataset_api.py",
        REPO_ROOT / "src/studio/tests/integration/test_training_api.py",
    ]

    missing = [str(path.relative_to(REPO_ROOT)) for path in expected if not path.exists()]
    assert not missing, f"Missing API contract integration tests: {missing}"
