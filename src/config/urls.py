from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .urls_api import urlpatterns as api_urlpatterns
from .urls_web import urlpatterns as web_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    *api_urlpatterns,
    *web_urlpatterns,
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
