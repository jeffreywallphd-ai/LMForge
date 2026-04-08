# LMForge Prompt Routing Guide (src-focused)

This routing guide is for assistants/agents operating on the **current src-based implementation** only.

## Scope and Priority

1. **In scope:** `src/**`, `manage.py`, `requirements.txt`.
2. **Out of scope for implementation decisions:** `Sandbox/`, `AIAgent/`, `lmforge/` (legacy), `README.md`, `documentation/`.
3. Treat the architecture as a layered Django system where some endpoints are still legacy-style while service/workflow layers are being established.

## Router Decision Tree

Use this sequence for incoming tasks:

1. **Classify intent**
   - Chat/session behavior → `chat` pack.
   - Scraping/PDF/manual text ingest → `document-ingestion` pack.
   - Dataset Q/A generation/export → `dataset-generation` pack.
   - Qdrant/vector chunk operations → `embedding-and-vectorstore` pack.
   - Training pipeline or LoRA/QLoRA setup → `training-and-finetuning` pack.
   - Metric scoring/model benchmarking → `model-evaluation` pack.
   - Cross-cutting architecture or refactor planning → `system-overview` + relevant feature pack.

2. **Select context pack(s)**
   - Load one primary pack plus at most two supporting packs.
   - If task touches URL/view behavior, include the feature pack and `system-overview`.

3. **Choose implementation surface**
   - Prefer `application/services` + `application/workflows` for new business logic.
   - Keep `presentation/*/views` thin where practical.
   - Respect domain policies in `src/studio/domain/policies` when validating input.

4. **Guardrails**
   - Do not introduce dependencies on excluded legacy/prototype folders.
   - Keep DB compatibility with existing model table names.
   - Preserve dual-surface UX (web templates + API endpoints) unless explicitly asked to consolidate.

## Token Budgeting Guidance

When constructing LLM context for coding tasks:

- **Base include:**
  - `src/config/settings/base.py`
  - `src/config/urls.py`
  - `src/studio/presentation/api/urls.py`
  - `src/studio/presentation/web/urls.py`

- **Feature include:** only files listed in selected pack(s).

- **Exclude by default:**
  - large HTML templates unless task is UI-specific,
  - long scraping heuristics internals unless extraction quality is the task,
  - unrelated model files.

## Suggested Prompt Skeleton

```text
Objective:
<one-sentence goal>

Scope:
- Include: <pack file list>
- Exclude: Sandbox/, AIAgent/, lmforge/, README.md, documentation/

Constraints:
- Maintain src-layering (presentation -> application -> domain/infrastructure)
- Preserve existing DB table compatibility
- Keep API/web behavior backward-compatible unless requested

Deliverables:
- <code/docs/tests>
```

## Pack Index

- `packs/system-overview.md`
- `packs/chat-and-conversation.md`
- `packs/document-ingestion.md`
- `packs/dataset-generation.md`
- `packs/embedding-and-vectorstore.md`
- `packs/training-and-finetuning.md`
- `packs/model-evaluation.md`
