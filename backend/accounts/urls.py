"""
Accounts app URL configuration.

All routes are namespaced under ``accounts`` and designed to be included
in the project-level ``urls.py`` as::

    path('api/accounts/', include('accounts.urls')),

Endpoint Map
------------
Authentication
    POST   /auth/register/              → RegisterView
    POST   /auth/login/                 → LoginView
    POST   /auth/token/refresh/         → TokenRefreshView (SimpleJWT)

Current User Profile ("Me")
    GET    /me/                         → MeView  (retrieve)
    PATCH  /me/                         → MeView  (partial update)

User Management (System Admin / high-ranking officers)
    GET    /users/                      → UserViewSet.list
    GET    /users/{id}/                 → UserViewSet.retrieve
    PATCH  /users/{id}/assign-role/     → UserViewSet.assign_role
    PATCH  /users/{id}/activate/        → UserViewSet.activate
    PATCH  /users/{id}/deactivate/      → UserViewSet.deactivate

Role Management (System Admin)
    GET    /roles/                      → RoleViewSet.list
    POST   /roles/                      → RoleViewSet.create
    GET    /roles/{id}/                 → RoleViewSet.retrieve
    PUT    /roles/{id}/                 → RoleViewSet.update
    PATCH  /roles/{id}/                 → RoleViewSet.partial_update
    DELETE /roles/{id}/                 → RoleViewSet.destroy
    POST   /roles/{id}/assign-permissions/ → RoleViewSet.assign_permissions

Utility
    GET    /permissions/                → PermissionListView
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LoginView,
    MeView,
    PermissionListView,
    RegisterView,
    RoleViewSet,
    UserViewSet,
)

app_name = "accounts"

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"roles", RoleViewSet, basename="role")

urlpatterns = [
    # ── Authentication ───────────────────────────────────────────────
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path(
        "auth/token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),

    # ── Current User (Me) ───────────────────────────────────────────
    path("me/", MeView.as_view(), name="me"),

    # ── Utility ──────────────────────────────────────────────────────
    path("permissions/", PermissionListView.as_view(), name="permission-list"),

    # ── Router-registered viewsets (users/, roles/) ──────────────────
    path("", include(router.urls)),
]
