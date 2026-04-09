from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from rest_framework.test import APIRequestFactory

from studio.presentation.api.views import chat as chat_views
from studio.presentation.api.views import evaluation as evaluation_views


def test_session_create_view_generates_uuid(monkeypatch) -> None:
    monkeypatch.setattr(chat_views.uuid, "uuid4", lambda: "fixed-session")
    request = APIRequestFactory().post("/api/chatbot/", data={})

    response = chat_views.SessionCreateView.as_view()(request)

    assert response.status_code == 201
    assert response.data["status"] == "success"
    assert response.data["data"]["session_id"] == "fixed-session"


def test_session_and_conversation_list_views_use_conversation_manager(monkeypatch) -> None:
    manager = Mock()
    manager.values_list.return_value.distinct.return_value = ["s1", "s2"]
    manager.filter.return_value.order_by.return_value = [SimpleNamespace(message="Hi", is_user=True)]
    monkeypatch.setattr(chat_views.Conversation, "objects", manager)

    serializer_class = Mock()
    serializer_class.return_value.data = [{"message": "Hi", "is_user": True}]
    monkeypatch.setattr(chat_views, "ConversationSerializer", serializer_class)

    factory = APIRequestFactory()

    sessions_response = chat_views.SessionListView.as_view()(factory.get("/api/chatbot/sessions/"))
    assert sessions_response.status_code == 200
    assert sessions_response.data == {"status": "success", "data": {"sessions": ["s1", "s2"]}}

    history_response = chat_views.ConversationListView.as_view()(factory.get("/api/chatbot/s1/"), session_id="s1")
    assert history_response.status_code == 200
    assert history_response.data == {"status": "success", "data": [{"message": "Hi", "is_user": True}]}


def test_conversation_create_view_returns_201_when_serializer_valid(monkeypatch) -> None:
    serializer = Mock()
    serializer.is_valid.return_value = True
    serializer.data = {"message": "Hello", "is_user": True}

    serializer_class = Mock(return_value=serializer)
    monkeypatch.setattr(chat_views, "ConversationSerializer", serializer_class)

    request = APIRequestFactory().post("/api/chatbot/s1/add/", {"message": "Hello", "is_user": True}, format="json")
    response = chat_views.ConversationCreateView.as_view()(request, session_id="s1")

    assert response.status_code == 201
    assert response.data["status"] == "success"
    assert response.data["data"]["session_id"] == "s1"
    serializer.save.assert_called_once()


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
    monkeypatch.setattr(chat_views, "generate_response", lambda *_args, **_kwargs: "Stubbed reply")

    saved = []

    class StubSerializer:
        def __init__(self, data):
            self._data = data
            self.data = data

        def is_valid(self):
            return True

        def save(self):
            saved.append(self._data)

    monkeypatch.setattr(chat_views, "ConversationSerializer", StubSerializer)

    request = APIRequestFactory().post(
        "/api/chatbot/s1/response/",
        {"message": "How are you?", "model_name": "gpt2"},
        format="json",
    )
    response = chat_views.ChatbotGenerateResponseView.as_view()(request, session_id="s1")

    assert response.status_code == 200
    assert response.data["status"] == "success"
    assert response.data["data"]["bot_response"] == "Stubbed reply"
    assert len(saved) == 2
    assert saved[0]["is_user"] is True
    assert saved[1]["is_user"] is False


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
