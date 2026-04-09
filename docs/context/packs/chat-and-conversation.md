# Context Pack: Chat and Conversation

## Use When

- Working on chatbot response generation.
- Session management or conversation persistence changes.

## Primary Files

- `src/studio/presentation/api/views/chat.py`
- `src/studio/presentation/api/serializers/conversations.py`
- `src/studio/domain/models/conversations.py`
- `src/studio/application/services/chat_service.py`
- `docs/context/service-testing-conventions.md`

## Core Facts

- API exposes session create/list, message list/create, and generate-response endpoints.
- Conversation persistence uses Django model `Conversation` with `session_id`, message body, and user/bot flag.
- `ChatService` is the single boundary for chat turn validation, model/session acquisition, generation, and conversation persistence.
- `ChatModelSessionProvider` owns model/tokenizer loading and in-memory reuse by `model_name`, so API views no longer instantiate/loading models directly.
- API chat views map typed service outcomes (`invalid_input`, `model_session_unavailable`, `execution_failure`, `internal_failure`) to HTTP status codes without duplicating business validation.

## Important Constraints

- Parameter validation for message payload and generation bounds is centralized in `ChatService.parse_turn_request(...)` / `ChatGenerationConfig.validate()`.
- Model/session lifecycle:
  - Created on first request per `model_name` inside `ChatModelSessionProvider.get_model_session(...)`.
  - Reused from provider cache for subsequent requests in the same process.
  - Loader failures raise `ModelSessionUnavailableError`; generation-time failures raise `ChatExecutionError`.
