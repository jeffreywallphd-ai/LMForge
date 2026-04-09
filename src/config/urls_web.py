from django.urls import include, path

urlpatterns = [
    path('', include('studio.presentation.web.urls')),
]
