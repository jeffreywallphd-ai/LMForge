from django.urls import include, path

urlpatterns = [
    path('api/', include('studio.presentation.api.urls')),
]
