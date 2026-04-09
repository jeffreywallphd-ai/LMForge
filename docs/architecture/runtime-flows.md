# Runtime Flows

## 1) Chat Generation Flow

```mermaid
sequenceDiagram
  participant U as Client
  participant API as API Chat View
  participant DB as Conversation Model
  participant LLM as Transformers Model

  U->>API: POST /api/chatbot/{session_id}/response/
  API->>APP: run_chat_turn(session_id, payload)
  APP->>APP: validate payload + normalize generation config
  APP->>LLM: get model session via ChatModelSessionProvider
  APP->>LLM: generate response
  APP->>DB: save user message
  APP->>DB: save bot response
  API-->>U: response + generation params
```

Notes:
- Chat endpoint delegates validation, model/session access, generation, and persistence to `ChatService`.
- `ChatModelSessionProvider` centralizes model/tokenizer loading and per-process reuse to avoid duplicated loader paths.
- API view remains responsible for HTTP contract mapping only (e.g., `invalid_input` -> 400, unavailable session -> 503, execution failure -> 502).

## 2) Scraping Vertical Slice (Service + API + Web)

```mermaid
sequenceDiagram
  participant U as Client
  participant API as Scraping API View
  participant APP as ScrapingService
  participant DOC as DocumentService
  participant INF as GenericWebScraper/RedditScraper
  participant DB as SourceDocument

  U->>API: POST/GET /api/scrape (url,title,source_type)
  API->>APP: adapt HTTP payload to ScrapeRequest
  APP->>APP: normalize + validate request (url/source_type rules)
  APP->>DOC: dispatch generic/reddit scrape path
  DOC->>INF: extract content + metadata
  APP->>DOC: persist normalized SourceDocument
  DOC->>DB: create SourceDocument
  API-->>U: JSON success/error envelope
```

Notes:
- `ScrapingService` is the application boundary for URL scraping concerns.
- API and web surfaces map the same service result into different contracts (JSON vs template context).
- API maps `validation_error -> 400`, `upstream_error -> 502`, and `unexpected_error -> 500` without re-implementing scrape orchestration in the view.

## 3) Dataset Generation Flow

```mermaid
sequenceDiagram
  participant U as Client
  participant P as Web/API Presentation Handler
  participant W as DatasetGenerationWorkflow
  participant APP as DatasetService
  participant LLM as HF Model
  participant EXP as ExportService
  participant DB as Persistence Callback (optional)

  U->>P: submit dataset params
  P->>P: validate form/serializer shape only
  P->>W: call generate(document_ids, questions_per_chunk, chunk_limit, instruction_prompt)
  W->>APP: generate_dataset(DatasetGenerationRequest, persist_artifact?)
  APP->>APP: normalize/validate business request
  APP->>LLM: generate + parse record candidates
  APP->>DB: optional persistence handoff callback
  APP-->>W: DatasetGenerationResult (ok/failure + metadata)
  W->>EXP: render JSON/CSV from records
  W-->>P: workflow result with records + contract metadata
  P-->>U: response mapped to HTML or JSON surface
```

Notes:
- Forms handle request-bound validation; business orchestration remains in `DatasetService`.
- Service contracts are framework-light and reusable across API/web adapters.
- Persistence is explicit via callback handoff metadata instead of hidden view-side side effects.

## 4) Embedding + Vector Storage Flow

```mermaid
sequenceDiagram
  participant U as Client
  participant APP as EmbeddingStorageWorkflow
  participant V as VectorStoreService
  participant Q as Qdrant

  U->>APP: store_document_embeddings(document_ids, collection)
  APP->>APP: chunk source text
  APP->>V: compute embeddings + ensure collection
  V->>Q: upsert points
  APP-->>U: stored status + chunk count
```

Notes:
- Missing Qdrant dependency or connectivity returns graceful no-op/empty outcomes.

## 5) Training Orchestration Flow

```mermaid
sequenceDiagram
  participant U as Client
  participant P as API/Web Training Handler
  participant APP as TrainingService
  participant EXE as TrainingExecutor (infra seam)
  participant REP as TrainingResultStore (repo/gateway)
  participant HF as HuggingFace Hub

  U->>P: training form/json payload
  P->>APP: orchestrate_training(payload)
  APP->>APP: assemble_config(payload)
  APP->>HF: resolve model size (best effort)
  APP->>APP: validate policy + resolve precision + target modules
  APP->>EXE: execute(config, precision, target_modules)
  EXE-->>APP: TrainingExecutionResult
  APP->>REP: save(config, plan, execution, failure_kind)
  REP-->>APP: persisted metadata
  APP-->>P: TrainingOrchestrationResult
  P-->>U: HTTP response mapping only
```

Notes:
- `TrainingService` now owns explicit lifecycle boundaries: config assembly, validation/preparation, execution handoff, and persistence handoff.
- Presentation handlers no longer coordinate runtime setup directly; they map request/response contracts.
- Execution and persistence are separate collaborators so long-running training and storage can evolve independently.

## 6) Evaluation Flow

```mermaid
sequenceDiagram
  participant U as Client
  participant APP as ModelEvaluationWorkflow
  participant DS as HF Dataset/CSV Loader
  participant ES as EvaluationService

  U->>APP: models + dataset source
  APP->>DS: load and sample Q/A pairs
  loop per model and question
    APP->>ES: generate response + score metrics
  end
  APP-->>U: averaged metrics per model
```

Notes:
- Evaluation is compute-intensive and currently synchronous.
- A queue-backed async pathway would improve reliability.
