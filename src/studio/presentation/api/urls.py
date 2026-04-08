from django.urls import path

from .views.chat import ChatbotGenerateResponseView, ConversationCreateView, ConversationListView, SessionCreateView, SessionListView
from .views.datasets import database_workflow
from .views.evaluation import ModelStatisticsView
from .views.scraping import SaveManualTextView, ScrapeDataView, UploadPDFView
from .views.training import get_model_stats, stream_training_output, stream_training_workflow_output, train_encoder_view, train_model_view, train_model_workflow

urlpatterns = [
    path('chatbot/', SessionCreateView.as_view(), name='create-session'),
    path('chatbot/sessions/', SessionListView.as_view(), name='list-sessions'),
    path('chatbot/<str:session_id>/', ConversationListView.as_view(), name='get-conversation'),
    path('chatbot/<str:session_id>/add/', ConversationCreateView.as_view(), name='post-message'),
    path('chatbot/<str:session_id>/response/', ChatbotGenerateResponseView.as_view(), name='generate-response'),
    path('scrape/', ScrapeDataView.as_view(), name='scrape-data'),
    path('upload_pdf/', UploadPDFView.as_view(), name='upload-pdf'),
    path('save_manual_text/', SaveManualTextView.as_view(), name='save-manual-text'),
    path('database_workflow/', database_workflow, name='database-workflow'),
    path('train_model/', train_model_view, name='train-view'),
    path('train_encoder/', train_encoder_view, name='train-encoder'),
    path('stream-training/', stream_training_output, name='stream-training'),
    path('stream_training_workflow/', stream_training_workflow_output, name='stream-training-workflow'),
    path('train_model_workflow/', train_model_workflow, name='train-model-workflow'),
    path('model_stats/', get_model_stats, name='model-stats-workflow'),
    path('model_statistics/', ModelStatisticsView.as_view(), name='model-statistics'),
]
