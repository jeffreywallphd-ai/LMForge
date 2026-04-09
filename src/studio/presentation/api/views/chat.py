from __future__ import annotations

from rest_framework import status
from rest_framework.views import APIView

from studio.application.services.chat_service import ChatGenerationConfig, ChatService
from studio.presentation.api.response_contracts import error_response, success_response, validation_error_response
from studio.presentation.api.serializers.conversations import ConversationSerializer


class SessionCreateView(APIView):
    """Handle POST requests to create a new chat session."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat_service = ChatService()

    def post(self, request):
        session_id = self.chat_service.create_session_id()
        return success_response({'session_id': session_id}, status_code=status.HTTP_201_CREATED)


class SessionListView(APIView):
    """Handle GET requests to list all existing session IDs."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat_service = ChatService()

    def get(self, request):
        sessions = self.chat_service.list_sessions()
        return success_response({'sessions': sessions})


class ConversationListView(APIView):
    """Handle GET requests to retrieve conversation history."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat_service = ChatService()

    def get(self, request, session_id):
        conversations = self.chat_service.get_session_messages(session_id)
        serializer = ConversationSerializer(conversations, many=True)
        return success_response(serializer.data)


class ConversationCreateView(APIView):
    """Handle POST requests to add a new message to the conversation."""

    def post(self, request, session_id):
        data = request.data
        data['session_id'] = session_id
        serializer = ConversationSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return success_response({'session_id': session_id, **serializer.data}, status_code=status.HTTP_201_CREATED)
        return validation_error_response('Conversation payload is invalid.', serializer.errors)


class ChatbotGenerateResponseView(APIView):
    """Generate chatbot response and persist both user/bot messages."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat_service = ChatService()

    def get(self, request):
        return error_response('This endpoint only supports POST.', status_code=status.HTTP_405_METHOD_NOT_ALLOWED, code='method_not_allowed')

    @staticmethod
    def _parse_generation_config(payload) -> ChatGenerationConfig:
        try:
            return ChatGenerationConfig(
                model_name=str(payload.get('model_name', '')),
                max_length=int(payload.get('max_length', 200)),
                min_length=int(payload.get('min_length', 100)),
                top_k=int(payload.get('top_k', 50)),
                top_p=float(payload.get('top_p', 0.95)),
                no_repeat_ngram_size=int(payload.get('no_repeat_ngram_size', 0)),
                max_new_tokens=int(payload.get('max_new_tokens', 300)),
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                'Invalid parameters. Ensure max_length, min_length, and top_k are integers, and top_p is a float.'
            ) from exc

    def post(self, request, session_id):
        user_message = request.data.get('message')
        if not user_message:
            return validation_error_response('Both "message" and "model_name" are required.')

        try:
            generation_config = self._parse_generation_config(request.data)
            generation_config.validate()
        except ValueError as exc:
            message = str(exc)
            if message == 'model_name is required':
                return validation_error_response('Both "message" and "model_name" are required.')
            return validation_error_response(message)

        try:
            bot_response = self.chat_service.generate_response(user_message, generation_config)
        except Exception as exc:  # noqa: BLE001
            return error_response(
                f'Error during response generation: {str(exc)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                code='generation_error',
            )

        self.chat_service.save_message(session_id=session_id, message=user_message, is_user=True)
        self.chat_service.save_message(session_id=session_id, message=bot_response, is_user=False)

        return success_response(
            {
                'user_message': user_message,
                'bot_response': bot_response,
                'generation_params': {
                    'model_name': generation_config.model_name,
                    'max_length': generation_config.max_length,
                    'min_length': generation_config.min_length,
                    'top_k': generation_config.top_k,
                    'top_p': generation_config.top_p,
                    'no_repeat_ngram_size': generation_config.no_repeat_ngram_size,
                    'max_new_tokens': generation_config.max_new_tokens,
                },
            }
        )
