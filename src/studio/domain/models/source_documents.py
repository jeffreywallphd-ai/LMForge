"""Domain models for externally sourced documents and ingestion metadata."""

from __future__ import annotations

from django.db import models


class SourceDocument(models.Model):
    """Raw source payload captured from scraping/upload endpoints."""

    url = models.URLField(max_length=500)
    file_type = models.CharField(max_length=50)
    content = models.TextField(null=True, blank=True)
    binary_content = models.BinaryField(null=True, blank=True)
    pdf_file = models.FileField(upload_to="uploads/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=100)

    class Meta:
        db_table = "lmforge_core_scrapeddata"

    def __str__(self) -> str:
        return f"Scraped from {self.url} ({self.file_type})"


class SourceDocumentMetadata(models.Model):
    """Denormalized metadata kept for list views and previews."""

    source_document = models.OneToOneField(
        SourceDocument,
        on_delete=models.CASCADE,
        related_name="metadata",
        db_column="scraped_data_id",
    )
    url = models.URLField(max_length=500)
    file_type = models.CharField(max_length=50)
    pdf_file = models.FileField(upload_to="uploads/", null=True, blank=True)
    created_at = models.DateTimeField()
    content_preview = models.CharField(max_length=100, blank=True, null=True)
    title = models.CharField(max_length=100)

    class Meta:
        db_table = "lmforge_core_scrapeddatameta"

    def __str__(self) -> str:
        return f"Metadata for {self.url} ({self.file_type})"
