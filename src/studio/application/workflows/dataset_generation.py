"""Application workflow: dataset generation."""

from __future__ import annotations

from dataclasses import dataclass

from src.studio.application.services.dataset_service import DatasetGenerationRequest, DatasetService
from src.studio.application.services.export_service import ExportService
from src.studio.domain.models.source_documents import SourceDocument


@dataclass(slots=True)
class DatasetGenerationWorkflowResult:
    records: list[dict]
    json_text: str
    csv_text: str
    document_count: int
    chunk_limit: int


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

    def generate(
        self,
        *,
        document_ids: list[int],
        questions_per_chunk: int = 1,
        chunk_limit: int = 1,
        instruction_prompt: str = "",
        model_name: str = "gpt2",
    ) -> DatasetGenerationWorkflowResult:
        if not document_ids:
            raise ValueError("At least one document must be selected")

        request = DatasetGenerationRequest(
            document_ids=document_ids,
            questions_per_chunk=max(1, int(questions_per_chunk)),
            chunk_limit=max(1, int(chunk_limit)),
            instruction_prompt=instruction_prompt,
        )

        records = self.dataset_service.generate_qa_pairs(request, model_name=model_name)
        json_text = self.export_service.as_json_text(records)
        csv_text = self.export_service.as_csv_text(records)

        return DatasetGenerationWorkflowResult(
            records=records,
            json_text=json_text,
            csv_text=csv_text,
            document_count=len(document_ids),
            chunk_limit=request.chunk_limit,
        )
