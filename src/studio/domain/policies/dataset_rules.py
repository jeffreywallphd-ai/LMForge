"""Domain policy: dataset generation safeguards."""

from __future__ import annotations


def validate_dataset_request(*, document_ids: list[int], questions_per_chunk: int, chunk_limit: int) -> None:
    if not document_ids:
        raise ValueError("At least one source document is required")
    if questions_per_chunk <= 0:
        raise ValueError("questions_per_chunk must be greater than 0")
    if chunk_limit <= 0:
        raise ValueError("chunk_limit must be greater than 0")
