"""
Core app URL configuration.

Provides cross-app aggregation endpoints that serve the frontend dashboard,
a global search interface, and system-wide constants/enums.

URL prefix (registered in ``backend/urls.py``)::

    path('api/core/', include('core.urls'))

Endpoint summary
----------------
GET /api/core/dashboard/     — Aggregated dashboard statistics (role-aware).
GET /api/core/search/        — Global search across Cases, Suspects, Evidence.
GET /api/core/constants/     — System choice enumerations for frontend dropdowns.
"""

from django.urls import path

from . import views

app_name = "core"

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
]
