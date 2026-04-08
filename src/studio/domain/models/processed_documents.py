"""Domain models for source cataloging and processed document lineage."""

from __future__ import annotations

from django.db import models


class ValidityLevel(models.IntegerChoices):
    RANDOM_UNVERIFIED = 1, "Random/Unverified"
    SOURCED = 2, "Sourced"
    PUBLISHED_AUDITED_GOVDATA = 3, "Published/audited/GovData"


class License(models.Model):
    license_id = models.IntegerField(primary_key=True, db_column="License_ID")
    license_name = models.CharField(max_length=255, db_column="License_Name")
    license_valid = models.BooleanField(db_column="License_Valid")
    validity_level = models.IntegerField(
        choices=ValidityLevel.choices,
        default=ValidityLevel.RANDOM_UNVERIFIED,
        db_column="LicenseValid",
    )

    class Meta:
        db_table = "lmforge_core_license"

    def __str__(self) -> str:
        return f"License {self.license_id} - {self.license_name} (Status: {self.get_validity_level_display()})"


class Source(models.Model):
    source_id = models.CharField(max_length=255, primary_key=True, db_column="SourceID")
    source_name = models.CharField(max_length=255, db_column="SourceName")
    license = models.ForeignKey(License, on_delete=models.CASCADE, db_column="License_ID")
    source_description = models.CharField(max_length=255, db_column="SourceDescription")
    source_link = models.CharField(max_length=255, db_column="SourceLink")
    validity_level = models.IntegerField(
        choices=ValidityLevel.choices,
        default=ValidityLevel.RANDOM_UNVERIFIED,
        db_column="SourceValid",
    )

    class Meta:
        db_table = "lmforge_core_source"

    def __str__(self) -> str:
        return (
            f"Source {self.source_id} - {self.source_name} - License: {self.license_id} - "
            f"{self.source_description} - {self.source_link} (Status: {self.get_validity_level_display()})"
        )


class ProcessedDocument(models.Model):
    doc_id = models.CharField(max_length=255, primary_key=True, db_column="DocID")
    description = models.CharField(max_length=255, db_column="DocDescription")
    link = models.CharField(max_length=255, db_column="DocLink")
    last_date_scraped = models.DateField(db_column="LastDateScraped")
    name = models.CharField(max_length=255, db_column="DocName")
    source = models.ForeignKey(Source, on_delete=models.CASCADE, db_column="Source_ID")
    license = models.ForeignKey(License, on_delete=models.CASCADE, db_column="License_ID")
    requires_attribution = models.BooleanField(db_column="RequiresAttribution")
    validity_level = models.IntegerField(
        choices=ValidityLevel.choices,
        default=ValidityLevel.RANDOM_UNVERIFIED,
        db_column="DocValid",
    )

    class Meta:
        db_table = "lmforge_core_document"

    def __str__(self) -> str:
        return (
            f"Document {self.doc_id} - {self.description} - Link: {self.link} - "
            f"Scraped: {self.last_date_scraped} - Name: {self.name} - "
            f"Source: {self.source_id} - License: {self.license_id} - "
            f"Attribution Required: {self.requires_attribution} "
            f"(Status: {self.get_validity_level_display()})"
        )
