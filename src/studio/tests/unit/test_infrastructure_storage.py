from pathlib import Path

from src.studio.infrastructure.storage.exports import export_records_csv, export_records_json
from src.studio.infrastructure.storage.files import ensure_parent_dir, sanitize_filename, write_bytes, write_text


def test_sanitize_filename_replaces_unsafe_chars_and_falls_back():
    assert sanitize_filename(" My File (1).txt ") == "My_File_1_.txt"
    assert sanitize_filename("   ", fallback="fallback") == "fallback"


def test_ensure_parent_dir_and_write_helpers(tmp_path: Path):
    text_path = tmp_path / "nested" / "notes.txt"
    bytes_path = tmp_path / "nested" / "blob.bin"

    ensure_parent_dir(text_path)
    assert text_path.parent.exists()

    write_text(text_path, "hello")
    write_bytes(bytes_path, b"\x00\x01")

    assert text_path.read_text(encoding="utf-8") == "hello"
    assert bytes_path.read_bytes() == b"\x00\x01"


def test_export_records_json_and_csv_shape():
    records = [
        {"question": "q1", "answer": "a1"},
        {"answer": "a2", "source": "doc2"},
    ]

    json_payload = export_records_json(records)
    assert '"question": "q1"' in json_payload

    csv_payload = export_records_csv(records)
    lines = [line for line in csv_payload.splitlines() if line.strip()]

    assert lines[0] == "answer,question,source"
    assert "a1,q1," in lines[1]
    assert "a2,,doc2" in lines[2]


def test_export_records_csv_empty_returns_empty_string():
    assert export_records_csv([]) == ""
