# API Response Contracts

## Purpose

LMForge API handlers under `src/studio/presentation/api/views/` are JSON-only adapters.
They should not render templates or return browser-oriented redirects.

## Standard response envelopes

### Success

```json
{
  "status": "success",
  "data": {}
}
```

### Error

```json
{
  "status": "error",
  "error": {
    "code": "bad_request",
    "message": "Human readable error",
    "details": {}
  }
}
```

### Validation failure

Validation failures use the same error shape with `code = "validation_error"` and include field-level details when available.

## Presentation boundary

- API views: JSON contracts only.
- Web views: template rendering only.
- Shared business behavior should be delegated to application services/workflows.

## Scraping endpoint contract

### Endpoint

- `GET /api/scrape/` or `POST /api/scrape/`

### Request fields

- `url` (required string)
- `title` (optional string)
- `source_type` (optional; `generic` default, or `reddit`)

### Success shape

```json
{
  "status": "success",
  "data": {
    "document_id": 42,
    "url": "https://example.com",
    "title": "Example",
    "file_type": "html",
    "content": "..."
  }
}
```

### Failure shape

- Validation failures return HTTP `400` with `error.code = "validation_error"`.
- Scraper/infrastructure failures return HTTP `502` with `error.code = "scrape_failed"`.
