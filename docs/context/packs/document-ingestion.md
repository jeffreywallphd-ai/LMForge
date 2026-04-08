# Context Pack: Document Ingestion

## Use When

- Handling scrape/upload/manual text ingestion.
- Editing extraction, normalization, or source document persistence.

## Primary Files

- `src/studio/presentation/api/views/scraping.py`
- `src/studio/infrastructure/scraping/generic_web.py`
- `src/studio/infrastructure/scraping/content_extractor.py`
- `src/studio/infrastructure/scraping/pdfs.py`
- `src/studio/infrastructure/scraping/reddit.py`
- `src/studio/application/services/document_service.py`
- `src/studio/application/workflows/document_ingestion.py`
- `src/studio/domain/models/source_documents.py`

## Core Facts

- `DocumentService` standardizes scrape and chunk-oriented preprocessing, including emoji removal and title normalization.
- Workflow wrapper (`DocumentIngestionWorkflow`) supports scrape-only and scrape-and-persist paths.
- Domain persistence uses `SourceDocument` and optional metadata projection table.
- Infrastructure includes specialized content extraction heuristics for web pages and utilities for PDF text extraction.

## Important Constraints

- Preserve compatibility with `SourceDocument` table names and field limits.
- Keep content cleanup deterministic and side-effect free.
