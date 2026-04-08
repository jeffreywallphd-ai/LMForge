"""PDF ingestion and conversion adapter."""

from __future__ import annotations

import json

import markdown
import pdfplumber


def extract_pdf_text(pdf_file) -> str:
    text_parts: list[str] = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
    return "\n\n".join([part for part in text_parts if part])


def convert_pdf_text(text: str, output_format: str = "text") -> tuple[str, str]:
    normalized = (output_format or "text").strip().lower()
    if normalized == "html":
        return markdown.markdown(text), "html"
    if normalized == "json":
        return json.dumps({"text": text}, indent=2), "json"
    return text, "text"
