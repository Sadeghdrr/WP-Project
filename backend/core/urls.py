"""
Core app URL configuration.

Provides cross-app aggregation endpoints that serve the frontend dashboard,
a global search interface, system-wide constants/enums, and notifications.

URL prefix (registered in ``backend/urls.py``)::

    path('api/core/', include('core.urls'))

Endpoint summary
----------------
GET  /api/core/dashboard/                  — Aggregated dashboard statistics (role-aware).
GET  /api/core/search/                     — Global search across Cases, Suspects, Evidence.
GET  /api/core/constants/                  — System choice enumerations for frontend dropdowns.
GET  /api/core/notifications/              — List notifications for the authenticated user.
POST /api/core/notifications/{id}/read/    — Mark a single notification as read.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "core"

# ── Router for ViewSet-based endpoints ───────────────────────────────
router = DefaultRouter()
router.register(
    prefix=r"notifications",
    viewset=views.NotificationViewSet,
    basename="notification",
)

urlpatterns = [
    # ── Dashboard ────────────────────────────────────────────────────
    path(
        "dashboard/",
        views.DashboardStatsView.as_view(),
        name="dashboard-stats",
    ),

    # ── Global Search ────────────────────────────────────────────────
    path(
        "search/",
        views.GlobalSearchView.as_view(),
        name="global-search",
    ),

    # ── System Constants / Enums ─────────────────────────────────────
    path(
        "constants/",
        views.SystemConstantsView.as_view(),
        name="system-constants",
    ),

    # ── Notifications (router-generated URLs) ────────────────────────
    path("", include(router.urls)),
]
