# Service Unit-Testing Conventions

## Purpose

Provide a reusable unit-testing pattern for application services that orchestrate validation, collaborator calls, and normalized outcomes.

## Scope

Use this for service-layer tests in `src/studio/tests/unit/` (especially `application/services` and extraction-oriented infrastructure where external dependencies are heavy).

## Pattern

1. **Prefer behavior contracts over internals**
   - Assert observable outputs (`ok`, `failure.code`, normalized records, persisted artifacts) and side effects (saved messages), not private implementation details.
2. **Isolate infrastructure-heavy collaborators with test doubles**
   - Use fakes/mocks for model sessions, LLM calls, persistence callbacks, and scraping/extraction sources.
3. **Cover both happy-path and failure-path semantics**
   - Include validation failures, collaborator acquisition failures, execution failures, and persistence handoff failures where relevant.
4. **Assert no unintended side effects on failures**
   - Example: chat turn failures should not persist user/bot messages.
5. **Keep fixtures lightweight and local**
   - Use small inline fake classes in each test module unless shared behavior clearly warrants a common fixture.

## Current Reference Examples

- `src/studio/tests/unit/test_chat_service.py`
- `src/studio/tests/unit/test_dataset_service.py`
- `src/studio/tests/unit/test_content_extractor.py`

These tests demonstrate reusable patterns for service-level contracts and extractor normalization behavior without relying on live model or network dependencies.
