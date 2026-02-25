"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── App routes ───────────────────────────────────────────────────
    path('api/accounts/', include('accounts.urls')),
    path('api/', include('evidence.urls')),
    path('api/', include('board.urls')),
    path('api/core/', include('core.urls')),
    path('api/', include('cases.urls')),
    path('api/', include('suspects.urls')),

    # ── Swagger / OpenAPI schema ─────────────────────────────────────
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# ── Serve media files in local development ───────────────────────────
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
