# Service Layer Audit and Extraction Plan (Stories 3.1.1–3.1.3)

## Purpose

This document inventories business logic that still lives in presentation handlers and defines concrete service/workflow candidates for extraction.

It also defines service-layer conventions so future extraction work lands in a consistent package structure.

## Scope Reviewed

Presentation handlers reviewed:

- `src/studio/presentation/api/views/chat.py`
- `src/studio/presentation/api/views/scraping.py`
- `src/studio/presentation/api/views/datasets.py`
- `src/studio/presentation/api/views/training.py`
- `src/studio/presentation/api/views/evaluation.py`
- `src/studio/presentation/web/views/scraping.py`
- `src/studio/presentation/web/views/training.py`
- `src/studio/presentation/web/views/datasets.py`

## Boundary Rules (Views vs Services vs Workflows)

### Keep in views (presentation only)

- Parse HTTP request/query/body/files into simple primitives.
- Bind forms/serializers and map validation failures to response contracts.
- Render templates (web) or JSON envelopes (api).
- Convert service/workflow results into user-facing response shapes.

### Move to services (reusable business behavior)

- Business validation beyond basic request schema checks.
- Configuration assembly and normalization.
- Selection logic (model/session/source strategy).
- Persistence coordination for a single slice.
- Result normalization to domain-friendly outputs.

### Move to workflows (multi-step orchestrations)

- Long-running or cross-service use-cases (dataset + vector + training/eval flows).
- Steps that coordinate multiple services plus infrastructure dependencies.
- Retry/compensation logic, progress updates, and async handoff seams.

## Inventory of Embedded Business Logic in Views

### 1) Chat flow

Current hotspots:

- Request parameter coercion and generation bounds validation.
- Model loading/generation orchestration and cache access.
- Conversation persistence of user and bot messages.

Status after Story 3.1.3:

- `ChatbotGenerateResponseView` now delegates generation and message persistence to `ChatService`.
- Session creation/listing and conversation history retrieval now use `ChatService` helpers.

Candidate boundaries:

- `ChatService` (implemented): session id creation, session listing/history, generation config validation, model invocation, message persistence.
- Potential future `ChatWorkflow`: async queue-based generation and streaming completion events.

### 2) Scraping flow

Current hotspots still in views:

- PDF upload conversion (file decoding, format conversion, persistence).
- Manual text persistence for ad hoc local sources.

Current service-backed path:

- URL scraping is already routed through `ScrapingService` and `DocumentService`.

Candidate boundaries:

- `ScrapingService` (existing): URL/source validation + normalized scrape results.
- `DocumentIngestionWorkflow` (existing candidate): unify URL, PDF, and manual text ingest contracts.
- Potential `DocumentConversionService`: format conversion (`text/html/json`) for uploaded PDFs.

### 3) Dataset generation flow

Current hotspots in API dataset view:

- HuggingFace token/login handling.
- Tokenizer/model bootstrap and chunking/token counting.
- Qdrant collection and embedding orchestration.
- Collection lifecycle checks and chunk persistence branching.

Candidate boundaries:

- `DatasetService` (existing): Q/A generation logic and extraction.
- `VectorStoreService` (existing): collection metadata and embedding persistence.
- `EmbeddingStorageWorkflow` (existing): document selection → chunking → vector-store operations.
- `DatasetGenerationWorkflow` (existing): document selection → generation → export.

### 4) Training flow

Current hotspots in API training view:

- Training config parsing and policy checks (QLoRA/model-size gating, precision resolution).
- Dataset split/prep and tokenizer formatting.
- HuggingFace/W&B auth and side effects.
- Full training runtime orchestration, model push, cleanup.

Candidate boundaries:

- `TrainingService` (existing): training config normalization + validation policy.
- `ModelTrainingWorkflow` (existing): orchestration of dataset prep, trainer setup, execution plan.
- Future infrastructure adapters: `infrastructure.llm` trainer/fine-tune provider wrappers.

### 5) Evaluation flow

Current hotspots in API evaluation view:

- Dataset source loading and tabular normalization.
- Input/output column inference and sampling strategy.
- Per-model per-question execution loop and aggregate metric folding.
- Inline model loading + metric tool execution.

Candidate boundaries:

- `EvaluationService` (existing): model generation + metric computations.
- `ModelEvaluationWorkflow` (existing): dataset loading/sampling and aggregate scoring orchestration.

## Service Package Structure and Conventions

Service-layer home:

- `src/studio/application/services/`

Conventions:

1. **Naming**
   - Use `<Feature>Service` for reusable business behavior (`ChatService`, `TrainingService`).
   - Use `<Feature>Workflow` for multi-step orchestration across services.

2. **Inputs/Outputs**
   - Prefer typed dataclasses for request/config payloads.
   - Return typed result objects or domain models, not `HttpRequest`/`Response`.
   - Keep service contracts framework-light and surface-agnostic.

3. **Error handling**
   - Use domain-meaningful `ValueError`/service exceptions for invalid business inputs.
   - Views translate service exceptions into HTTP contracts.

4. **Dependency boundaries**
   - Services may depend on domain + infrastructure modules.
   - Services must not import presentation modules.
   - Workflows orchestrate multiple services and infrastructure adapters.

5. **Observability**
   - Services can log business milestones and decision points.
   - Views log request/response metadata and contract failures.

## Migration Checklist (Incremental)

- [x] Chat API handlers delegate business logic to `ChatService`.
- [x] Chat model/session loading centralized behind `ChatModelSessionProvider` and reused via a single service access path.
- [x] Chat validation/error categories centralized in service layer with typed outcomes mapped by views.
- [ ] Extract PDF/manual text save behavior from scraping API views into service/workflow contracts.
- [ ] Route dataset collection/chunk orchestration through `EmbeddingStorageWorkflow` from views.
- [x] Move training orchestration out of API view into `TrainingService`/`ModelTrainingWorkflow` contracts with explicit config->execution->persistence boundaries.
- [ ] Route evaluation endpoint through `ModelEvaluationWorkflow` and keep view as response adapter.
- [ ] Add unit tests per extracted service contract and integration tests per endpoint contract.

## Testing Guidance for Safe Refactoring

Before extraction in each slice:

- Add/keep endpoint contract tests that assert request/response behavior.
- Add service unit tests for validation and normalization rules.
- Mock heavyweight model/vector dependencies at service boundaries.

After extraction in each slice:

- Verify endpoint tests remain green without payload shape regressions.
- Add one integration test that executes the service/workflow path with lightweight doubles.


## Story 3.3 Dataset Service Boundary (Generation + Form Separation + Persistence Handoff)

The dataset vertical slice now follows an explicit service contract:

- `DatasetGenerationRequest`: framework-agnostic input payload (`document_ids`, `questions_per_chunk`, `chunk_limit`, `instruction_prompt`).
- `DatasetService.generate_dataset(...)`: normalizes request values, validates business rules, orchestrates chunk generation + model parsing, and returns a structured outcome.
- `DatasetGenerationResult`: stable success/failure envelope for both web and API adapters, including:
  - `ok`
  - `records`
  - `normalized_request`
  - `chunk_count` and `processed_chunk_count`
  - `failure` with normalized code/message when validation fails
  - `persisted_artifact` metadata when callers provide persistence handoff callbacks.

Form and view responsibilities remain presentation-only:

- Forms (`presentation/web/forms/*`) own field-level shape and request-bound validation (for example trimming `instruction_prompt`).
- Views/workflows map cleaned form values to `DatasetGenerationRequest` and consume service outcomes.
- Business orchestration (chunk selection, model output parsing, record normalization) lives in `DatasetService`, not forms.

Persistence handoff is explicit:

- `DatasetService.generate_dataset(..., persist_artifact=...)` accepts an optional callback.
- Callers decide whether persistence occurs and how artifacts are saved.
- The callback return metadata is surfaced as `persisted_artifact` in the service and workflow result contracts.


## Story 3.4 Training Boundary Updates

The training slice now uses a dedicated application service orchestration boundary:

- `TrainingService.assemble_config(...)` handles request-agnostic normalization into `TrainingRun`.
- `TrainingService.prepare_training(...)` handles model-size lookup, policy validation, precision resolution, and target-module selection.
- `TrainingService.orchestrate_training(...)` performs explicit handoff to:
  - `TrainingExecutor` for runtime execution
  - `TrainingResultStore` for persistence of execution outcomes

This separates three previously entangled concerns:
1. input/config construction
2. runtime training execution
3. execution-result persistence

Presentation views now call service/workflow contracts and map HTTP responses only.
