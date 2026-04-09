from __future__ import annotations

from pathlib import Path


def test_initial_studio_migration_exists() -> None:
    migration = Path(__file__).resolve().parents[2] / "migrations" / "0001_initial.py"
    assert migration.exists(), "Expected src/studio/migrations/0001_initial.py to exist."


def test_initial_studio_migration_contains_legacy_table_names() -> None:
    migration = Path(__file__).resolve().parents[2] / "migrations" / "0001_initial.py"
    text = migration.read_text(encoding="utf-8")
    assert "lmforge_core_scrapeddata" in text
    assert "lmforge_core_scrapeddatameta" in text
