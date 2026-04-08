from django.urls import path

from .views.chat import chatbot_view
from .views.datasets import dataset_workflow_view
from .views.evaluation import model_statistics_view
from .views.home import home_view
from .views.scraping import scrape_view
from .views.settings import settings_view
from .views.training import train_model_view

urlpatterns = [
    path('home/', home_view, name='home-view'),
    path('settings/', settings_view, name='settings-view'),
    path('chat/', chatbot_view, name='chatbot-view'),
    path('scraping/', scrape_view, name='scrape-view'),
    path('datasets/', dataset_workflow_view, name='dataset-workflow'),
    path('training/', train_model_view, name='training-view'),
    path('evaluation/', model_statistics_view, name='model-statistics-view'),
]
