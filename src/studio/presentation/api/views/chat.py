from __future__ import annotations

from rest_framework import status
from rest_framework.views import APIView

from studio.application.services.chat_service import (
    ChatErrorCode,
    ChatExecutionError,
    ChatInputValidationError,
    ChatService,
    ChatServiceError,
    ModelSessionUnavailableError,
)
from studio.presentation.api.response_contracts import error_response, success_response, validation_error_response
from studio.presentation.api.serializers.conversations import ConversationSerializer


_CHAT_SERVICE = ChatService()


def get_chat_service() -> ChatService:
    return _CHAT_SERVICE


class SessionCreateView(APIView):
    """Handle POST requests to create a new chat session."""

    def post(self, request):
        session_id = get_chat_service().create_session_id()
        return success_response({'session_id': session_id}, status_code=status.HTTP_201_CREATED)


class SessionListView(APIView):
    """Handle GET requests to list all existing session IDs."""

    def get(self, request):
        sessions = get_chat_service().list_sessions()
        return success_response({'sessions': sessions})


class ConversationListView(APIView):
    """Handle GET requests to retrieve conversation history."""

    def get(self, request, session_id):
        conversations = get_chat_service().get_session_messages(session_id)
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

    def get(self, request):
        return error_response('This endpoint only supports POST.', status_code=status.HTTP_405_METHOD_NOT_ALLOWED, code='method_not_allowed')

    def post(self, request, session_id):
        try:
            turn_result = get_chat_service().run_chat_turn(session_id=session_id, payload=request.data)
            return success_response(
                {
                    'user_message': turn_result.user_message,
                    'bot_response': turn_result.bot_response,
                    'generation_params': turn_result.generation_params,
                }
            )
        except ChatInputValidationError as exc:
            message = str(exc)
            if message == 'model_name is required':
                return validation_error_response('Both "message" and "model_name" are required.')
            return validation_error_response(message)
        except ModelSessionUnavailableError as exc:
            return error_response(str(exc), status_code=status.HTTP_503_SERVICE_UNAVAILABLE, code=ChatErrorCode.MODEL_SESSION_UNAVAILABLE.value)
        except ChatExecutionError as exc:
            return error_response(str(exc), status_code=status.HTTP_502_BAD_GATEWAY, code=ChatErrorCode.EXECUTION_FAILURE.value)
        except ChatServiceError as exc:
            return error_response(str(exc), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, code=exc.code.value)
        except Exception as exc:  # noqa: BLE001
            return error_response(str(exc), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, code=ChatErrorCode.INTERNAL_FAILURE.value)
