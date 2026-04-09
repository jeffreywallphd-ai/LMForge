# Service and API Testing Conventions

## Purpose

Provide reusable testing patterns for both:

- service-layer behavior contracts, and
- machine-facing API contract integration tests.

## Scope

Use these conventions for tests under `src/studio/tests/unit/` and `src/studio/tests/integration/`.

## Service Unit-Test Pattern

1. **Prefer behavior contracts over internals**
   - Assert observable outputs (`ok`, `failure.code`, normalized records, persisted artifacts) and side effects.
2. **Isolate infrastructure-heavy collaborators with test doubles**
   - Use fakes/mocks for model sessions, LLM calls, persistence callbacks, and scraping/extraction sources.
3. **Cover both happy-path and failure-path semantics**
   - Include validation failures, collaborator acquisition failures, execution failures, and persistence handoff failures.
4. **Assert no unintended side effects on failures**
   - Example: chat turn failures should not persist user/bot messages.
5. **Keep fixtures lightweight and local**
   - Use small inline fake classes in each test module unless shared behavior clearly warrants a common fixture.

## API Contract Integration-Test Pattern

1. **Test at the request/response boundary**
   - Build requests through request factories and assert status + JSON contract shape.
2. **Mock at stable seams only**
   - Fake workflow/service collaborators for deterministic tests.
   - Do not couple tests to internal helper methods.
3. **Assert stable failure mappings**
   - Validation -> `400` with `validation_error`.
   - Upstream/execution failures -> `502`/`503` where the API contract defines them.
   - Unexpected/internal failures -> `500` with explicit error codes.
4. **Assert response envelope shape**
   - Success responses use `{ "status": "success", "data": ... }`.
   - Error responses use `{ "status": "error", "error": { "code": ..., "message": ... } }`.
5. **Keep tests maintainable**
   - Assert externally meaningful fields only.
   - Avoid brittle assertions tied to internal object lifecycles.

## Architecture Regression Guards

Lightweight architectural tests should protect:

- canonical domain-model imports,
- workflow placement for orchestration-heavy API paths,
- existence of integration contract tests for core API slices.

Reference: `src/studio/tests/unit/test_domain_model_import_contracts.py` and `src/studio/tests/unit/test_architecture_regression_guards.py`.

## Current Reference Examples

- Service contracts: `src/studio/tests/unit/test_chat_service.py`, `src/studio/tests/unit/test_dataset_service.py`, `src/studio/tests/unit/test_content_extractor.py`
- API contracts: `src/studio/tests/integration/test_scraping_api.py`, `src/studio/tests/integration/test_presentation_api_chat_and_eval.py`, `src/studio/tests/integration/test_dataset_api.py`, `src/studio/tests/integration/test_training_api.py`
