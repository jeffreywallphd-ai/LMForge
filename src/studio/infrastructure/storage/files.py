"""File storage helpers for SourceDocument payloads."""

from __future__ import annotations

from pathlib import Path
import re


def sanitize_filename(filename: str, fallback: str = "document") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (filename or "").strip())
    return cleaned or fallback


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str, *, encoding: str = "utf-8") -> Path:
    ensure_parent_dir(path)
    path.write_text(content or "", encoding=encoding)
    return path


def write_bytes(path: Path, content: bytes) -> Path:
    ensure_parent_dir(path)
    path.write_bytes(content)
    return path
