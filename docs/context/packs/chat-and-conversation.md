# Context Pack: Chat and Conversation

## Use When

- Working on chatbot response generation.
- Session management or conversation persistence changes.

## Primary Files

- `src/studio/presentation/api/views/chat.py`
- `src/studio/presentation/api/serializers/conversations.py`
- `src/studio/domain/models/conversations.py`
- `src/studio/application/services/chat_service.py`

## Core Facts

- API exposes session create/list, message list/create, and generate-response endpoints.
- Conversation persistence uses Django model `Conversation` with `session_id`, message body, and user/bot flag.
- `ChatService` mirrors much of view-level generation logic and introduces configurable generation object (`ChatGenerationConfig`).
- There is active coexistence of legacy-style direct view logic and newer service abstraction.

## Important Constraints

- Parameter validation must enforce bounds for min/max length, `top_p`, and `top_k`.
- Generation logic caches model/tokenizer in-memory per model name.
