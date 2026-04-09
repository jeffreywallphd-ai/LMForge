"""Application workflow: dataset generation orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from studio.application.services.dataset_service import (
    DatasetGenerationFailure,
    DatasetGenerationRequest,
    DatasetService,
)
from studio.application.services.export_service import ExportService
from studio.domain.models import SourceDocument


@dataclass(slots=True)
class DatasetGenerationWorkflowRequest:
    """Workflow-layer contract for dataset generation orchestration."""

    document_ids: list[int]
    questions_per_chunk: int = 1
    chunk_limit: int = 1
    instruction_prompt: str = ""
    model_name: str = "gpt2"


@dataclass(slots=True)
class DatasetGenerationWorkflowResult:
    """Normalized workflow outcome consumable by presentation handlers."""

    ok: bool
    records: list[dict]
    json_text: str
    csv_text: str
    document_count: int
    chunk_limit: int
    chunk_count: int
    processed_chunk_count: int
    persisted_artifact: dict[str, Any] | None
    failure: DatasetGenerationFailure | None = None


class DatasetGenerationWorkflow:
    """End-to-end dataset generation flow from selected source documents."""

    def __init__(
        self,
        dataset_service: DatasetService | None = None,
        export_service: ExportService | None = None,
    ) -> None:
        self.dataset_service = dataset_service or DatasetService()
        self.export_service = export_service or ExportService()

    def list_documents(self, *, page: int = 1, page_size: int = 10):
        """Return latest source documents in a simple page-oriented format."""
        page = max(1, int(page))
        page_size = max(1, int(page_size))
        start = (page - 1) * page_size
        end = start + page_size

        queryset = SourceDocument.objects.all().order_by("-created_at")
        total = queryset.count()
        return {
            "items": list(queryset[start:end]),
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        }

    def run(
        self,
        request: DatasetGenerationWorkflowRequest,
        *,
        persist_artifact: Callable[[list[dict[str, str]], DatasetGenerationRequest], dict[str, Any] | None] | None = None,
    ) -> DatasetGenerationWorkflowResult:
        """Run dataset generation as an explicit orchestration workflow."""

        service_request = DatasetGenerationRequest(
            document_ids=request.document_ids,
            questions_per_chunk=request.questions_per_chunk,
            chunk_limit=request.chunk_limit,
            instruction_prompt=request.instruction_prompt,
        )
        service_result = self.dataset_service.generate_dataset(
            service_request,
            model_name=request.model_name,
            persist_artifact=persist_artifact,
        )

        if not service_result.ok:
            return DatasetGenerationWorkflowResult(
                ok=False,
                records=[],
                json_text="[]",
                csv_text="",
                document_count=0,
                chunk_limit=max(1, int(request.chunk_limit)),
                chunk_count=0,
                processed_chunk_count=0,
                persisted_artifact=None,
                failure=service_result.failure,
            )

        return DatasetGenerationWorkflowResult(
            ok=True,
            records=service_result.records,
            json_text=self.export_service.as_json_text(service_result.records),
            csv_text=self.export_service.as_csv_text(service_result.records),
            document_count=len(service_result.normalized_request.document_ids),
            chunk_limit=service_result.normalized_request.chunk_limit,
            chunk_count=service_result.chunk_count,
            processed_chunk_count=service_result.processed_chunk_count,
            persisted_artifact=service_result.persisted_artifact,
            failure=None,
        )

    def generate(
        self,
        *,
        document_ids: list[int],
        questions_per_chunk: int = 1,
        chunk_limit: int = 1,
        instruction_prompt: str = "",
        model_name: str = "gpt2",
        persist_artifact: Callable[[list[dict[str, str]], DatasetGenerationRequest], dict[str, Any] | None] | None = None,
    ) -> DatasetGenerationWorkflowResult:
        """Backward-compatible convenience wrapper around :meth:`run`."""

        result = self.run(
            DatasetGenerationWorkflowRequest(
                document_ids=document_ids,
                questions_per_chunk=questions_per_chunk,
                chunk_limit=chunk_limit,
                instruction_prompt=instruction_prompt,
                model_name=model_name,
            ),
            persist_artifact=persist_artifact,
        )

        if not result.ok:
            message = result.failure.message if result.failure else "Dataset generation failed"
            raise ValueError(message)
        return result
