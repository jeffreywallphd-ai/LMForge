# Runtime Flows

## 1) Chat Generation Flow

```mermaid
sequenceDiagram
  participant U as Client
  participant API as API Chat View
  participant DB as Conversation Model
  participant LLM as Transformers Model

  U->>API: POST /api/chatbot/{session_id}/response/
  API->>DB: save user message
  API->>LLM: load/cache model + generate response
  API->>DB: save bot response
  API-->>U: response + generation params
```

Notes:
- Active endpoint logic is view-centric.
- Equivalent service abstraction exists in `ChatService`.

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
  API->>APP: validate + normalize request
  APP->>DOC: dispatch generic/reddit scrape path
  DOC->>INF: extract content + metadata
  APP->>DOC: persist normalized SourceDocument
  DOC->>DB: create SourceDocument
  API-->>U: JSON success/error envelope
```

Notes:
- `ScrapingService` is the application boundary for URL scraping concerns.
- API and web surfaces map the same service result into different contracts (JSON vs template context).

## 3) Dataset Generation Flow

```mermaid
sequenceDiagram
  participant U as Client
  participant API as Dataset View
  participant APP as DatasetService
  participant LLM as HF Model
  participant EXP as ExportService

  U->>API: select docs + generation params
  API->>APP: build prompt/chunk docs
  APP->>LLM: generate Q/A JSON-like output
  APP-->>API: parsed records
  API->>EXP: render JSON/CSV
  API-->>U: dataset artifacts
```

Notes:
- Flow currently appears in both legacy-style view logic and workflow/service modules.

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

## 5) Training Preparation Flow

```mermaid
sequenceDiagram
  participant U as Client
  participant API as Training View/Workflow
  participant APP as TrainingService
  participant HF as HuggingFace Hub

  U->>API: training config payload
  API->>APP: build config dataclass
  APP->>HF: resolve model size (best effort)
  APP->>APP: apply policy validation + precision resolution
  API-->>U: validated training plan
```

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
