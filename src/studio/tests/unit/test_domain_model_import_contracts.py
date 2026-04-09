from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
STUDIO_ROOT = REPO_ROOT / "src" / "studio"
THIS_FILE = Path(__file__).resolve()


def _python_files() -> list[Path]:
    return sorted(path for path in STUDIO_ROOT.rglob("*.py") if path.name != "__pycache__")


def test_non_registry_modules_do_not_import_from_studio_models() -> None:
    violations: list[str] = []
    allowed = {
        Path("src/studio/models.py"),
    }

    for path in _python_files():
        if path == THIS_FILE:
            continue
        rel = path.relative_to(REPO_ROOT)
        if rel in allowed:
            continue

        text = path.read_text(encoding="utf-8")
        if "from studio.models import" in text:
            violations.append(str(rel))

    assert not violations, f"Use studio.domain.models imports outside studio/models.py: {violations}"


def test_application_presentation_tests_use_domain_model_barrel_imports() -> None:
    scopes = [
        STUDIO_ROOT / "application",
        STUDIO_ROOT / "presentation",
        STUDIO_ROOT / "tests",
        STUDIO_ROOT / "domain" / "policies",
    ]
    violations: list[str] = []

    for scope in scopes:
        for path in sorted(scope.rglob("*.py")):
            if path == THIS_FILE:
                continue
            rel = path.relative_to(REPO_ROOT)
            text = path.read_text(encoding="utf-8")
            if "from studio.domain.models." in text:
                violations.append(str(rel))

    assert not violations, f"Prefer `from studio.domain.models import ...` barrel imports: {violations}"


def test_legacy_scraped_data_aliases_removed_from_runtime_and_tests() -> None:
    checked_scopes = [
        STUDIO_ROOT / "application",
        STUDIO_ROOT / "presentation",
        STUDIO_ROOT / "tests",
    ]
    violations: list[str] = []

    for scope in checked_scopes:
        for path in sorted(scope.rglob("*.py")):
            if path == THIS_FILE:
                continue
            rel = path.relative_to(REPO_ROOT)
            text = path.read_text(encoding="utf-8")
            if "ScrapedData" in text or "ScrapedDataMeta" in text:
                violations.append(str(rel))

    assert not violations, f"Use SourceDocument/SourceDocumentMetadata names: {violations}"
