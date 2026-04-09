from __future__ import annotations

from types import SimpleNamespace

from rest_framework.test import APIRequestFactory

from studio.presentation.api.views import chat as chat_views
from studio.presentation.api.views import evaluation as evaluation_views


class _FakeChatService:
    def __init__(self) -> None:
        self.saved_messages: list[tuple[str, str, bool]] = []

    def create_session_id(self) -> str:
        return "fixed-session"

    def list_sessions(self) -> list[str]:
        return ["s1", "s2"]

    def get_session_messages(self, session_id: str):
        assert session_id == "s1"
        return [SimpleNamespace(message="Hi", is_user=True)]

    def generate_response(self, _prompt: str, _cfg) -> str:
        return "Stubbed reply"

    def save_message(self, *, session_id: str, message: str, is_user: bool):
        self.saved_messages.append((session_id, message, is_user))


def test_session_create_view_generates_uuid_via_chat_service(monkeypatch) -> None:
    monkeypatch.setattr(chat_views, "ChatService", _FakeChatService)
    request = APIRequestFactory().post("/api/chatbot/", data={})

    response = chat_views.SessionCreateView.as_view()(request)

    assert response.status_code == 201
    assert response.data["status"] == "success"
    assert response.data["data"]["session_id"] == "fixed-session"


def test_session_and_conversation_list_views_use_chat_service(monkeypatch) -> None:
    monkeypatch.setattr(chat_views, "ChatService", _FakeChatService)

    class _Serializer:
        def __init__(self, _conversations, many: bool):
            assert many is True
            self.data = [{"message": "Hi", "is_user": True}]

    monkeypatch.setattr(chat_views, "ConversationSerializer", _Serializer)

    factory = APIRequestFactory()

    sessions_response = chat_views.SessionListView.as_view()(factory.get("/api/chatbot/sessions/"))
    assert sessions_response.status_code == 200
    assert sessions_response.data == {"status": "success", "data": {"sessions": ["s1", "s2"]}}

    history_response = chat_views.ConversationListView.as_view()(factory.get("/api/chatbot/s1/"), session_id="s1")
    assert history_response.status_code == 200
    assert history_response.data == {"status": "success", "data": [{"message": "Hi", "is_user": True}]}


def test_conversation_create_view_returns_201_when_serializer_valid(monkeypatch) -> None:
    class _Serializer:
        def __init__(self, data):
            self.data = {"message": data["message"], "is_user": data["is_user"]}

        def is_valid(self):
            return True

        def save(self):
            return None

    monkeypatch.setattr(chat_views, "ConversationSerializer", _Serializer)

    request = APIRequestFactory().post("/api/chatbot/s1/add/", {"message": "Hello", "is_user": True}, format="json")
    response = chat_views.ConversationCreateView.as_view()(request, session_id="s1")

    assert response.status_code == 201
    assert response.data["status"] == "success"
    assert response.data["data"]["session_id"] == "s1"


def test_chatbot_generate_response_rejects_invalid_generation_bounds() -> None:
    request = APIRequestFactory().post(
        "/api/chatbot/s1/response/",
        {"message": "Hi", "model_name": "gpt2", "min_length": 250, "max_length": 100},
        format="json",
    )

    response = chat_views.ChatbotGenerateResponseView.as_view()(request, session_id="s1")

    assert response.status_code == 400
    assert "min_length must be <= max_length" in response.data["error"]["message"]


def test_chatbot_generate_response_saves_user_and_bot_messages(monkeypatch) -> None:
    fake_service = _FakeChatService()
    monkeypatch.setattr(chat_views, "ChatService", lambda: fake_service)

    request = APIRequestFactory().post(
        "/api/chatbot/s1/response/",
        {"message": "How are you?", "model_name": "gpt2"},
        format="json",
    )
    response = chat_views.ChatbotGenerateResponseView.as_view()(request, session_id="s1")

    assert response.status_code == 200
    assert response.data["status"] == "success"
    assert response.data["data"]["bot_response"] == "Stubbed reply"
    assert len(fake_service.saved_messages) == 2
    assert fake_service.saved_messages[0][2] is True
    assert fake_service.saved_messages[1][2] is False


def test_model_statistics_view_requires_models_parameter() -> None:
    request = APIRequestFactory().post("/api/model_statistics/", {}, format="json")

    response = evaluation_views.ModelStatisticsView.as_view()(request)

    assert response.status_code == 400
    assert response.data["error"] == "At least one model name is required"


def test_model_statistics_view_rejects_missing_dataset() -> None:
    request = APIRequestFactory().post("/api/model_statistics/", {"models": "gpt2"}, format="json")

    response = evaluation_views.ModelStatisticsView.as_view()(request)

    assert response.status_code == 400
    assert response.data["error"] == "Provide either dataset URL or file."


def test_cal_sts_score_handles_non_string_inputs(monkeypatch) -> None:
    class StubCrossEncoder:
        def __init__(self, _name: str) -> None:
            pass

        def predict(self, _pairs):
            return [0.98765]

    monkeypatch.setattr(evaluation_views, "CrossEncoder", StubCrossEncoder)

    assert evaluation_views.cal_sts_score(123, "answer") == "nan"
    assert evaluation_views.cal_sts_score("prompt", "answer") == 0.9877
