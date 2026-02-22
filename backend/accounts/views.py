"""
Accounts app views.

All views follow the **Thin View** pattern: validate input via
serializers, delegate to the service layer, and return the result
wrapped in a DRF ``Response``.  **No business logic** resides here.

View Map
--------
- ``RegisterView``       — POST /auth/register/
- ``LoginView``          — POST /auth/login/
- ``MeView``             — GET / PATCH /me/
- ``UserViewSet``        — /users/  (list, retrieve, assign-role,
                           activate, deactivate)
- ``RoleViewSet``        — /roles/  (full CRUD + assign-permissions)
- ``PermissionListView`` — GET /permissions/
"""

from __future__ import annotations

from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Role, User
from .serializers import (
    AssignRoleSerializer,
    CustomTokenObtainPairSerializer,
    LoginRequestSerializer,
    MeUpdateSerializer,
    PermissionSerializer,
    RegisterRequestSerializer,
    RoleAssignPermissionsSerializer,
    RoleDetailSerializer,
    RoleListSerializer,
    TokenResponseSerializer,
    UserDetailSerializer,
    UserListSerializer,
)
from .services import (
    AuthenticationService,
    CurrentUserService,
    RoleManagementService,
    UserManagementService,
    UserRegistrationService,
    list_all_permissions,
)


# ═══════════════════════════════════════════════════════════════════
#  Authentication Views
# ═══════════════════════════════════════════════════════════════════


class RegisterView(generics.CreateAPIView):
    """
    POST /api/accounts/auth/register/

    Public endpoint.  Creates a new user with the default "Base User"
    role.

    Request body  → ``RegisterRequestSerializer``
    Response body → ``UserDetailSerializer`` (201 Created)

    Flow:
        1. Validate input via ``RegisterRequestSerializer``.
        2. Delegate to ``UserRegistrationService.register_user()``.
        3. Return the new user serialized with ``UserDetailSerializer``.
    """

    permission_classes = [AllowAny]
    serializer_class = RegisterRequestSerializer

    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        Handle user registration.

        1. Validate input via RegisterRequestSerializer.
        2. Delegate to UserRegistrationService.register_user().
        3. Serialize the returned user with UserDetailSerializer.
        4. Return Response(data, status=201).
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = UserRegistrationService.register_user(serializer.validated_data)
        response_serializer = UserDetailSerializer(user)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    POST /api/accounts/auth/login/

    Public endpoint.  Authenticates a user via any of the four
    unique identifiers (username, national_id, phone_number, email)
    plus password.

    Request body  → ``LoginRequestSerializer``
    Response body → ``TokenResponseSerializer`` (200 OK)

    Flow:
        1. Validate input via ``LoginRequestSerializer``.
        2. Delegate to ``AuthenticationService.authenticate()``.
        3. If authentication fails, return 401.
        4. Generate JWT tokens via ``AuthenticationService.generate_tokens()``.
        5. Return tokens + user info via ``TokenResponseSerializer``.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        """
        Handle multi-field login.

        Implementation Contract
        -----------------------
        1. Validate ``request.data`` with ``LoginRequestSerializer``.
        2. Call ``AuthenticationService.authenticate(
               identifier=data['identifier'],
               password=data['password'],
           )``.
        3. If ``None`` is returned → ``Response(
               {"detail": "Invalid credentials."}, status=401
           )``.
        4. Call ``AuthenticationService.generate_tokens(user)``.
        5. Build response payload:
           ``{"access": ..., "refresh": ..., "user": UserDetailSerializer(user).data}``.
        6. Return ``Response(payload, status=200)``.
        """
        serializer = CustomTokenObtainPairSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        payload = serializer.validated_data  # contains 'access' and 'refresh'
        payload["user"] = UserDetailSerializer(serializer.user).data

        return Response(payload, status=status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════════════════
#  Current User ("Me") View
# ═══════════════════════════════════════════════════════════════════


class MeView(APIView):
    """
    GET  /api/accounts/me/  → Retrieve current user profile.
    PATCH /api/accounts/me/ → Update own profile fields.

    Requires authentication.  Returns the user's full profile
    including role details and a flat permissions list for the
    Next.js frontend to render conditional UI modules.

    GET Response  → ``UserDetailSerializer``
    PATCH Request → ``MeUpdateSerializer``
    PATCH Response → ``UserDetailSerializer``
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        """
        Retrieve the authenticated user's profile.

        Implementation Contract
        -----------------------
        1. Call ``CurrentUserService.get_profile(request.user)``.
        2. Serialize with ``UserDetailSerializer``.
        3. Return ``Response(data, status=200)``.

        The response includes:
        - ``role_detail``: nested object with role name, description,
          hierarchy_level.
        - ``permissions``: a flat list of strings such as
          ``['cases.view_case', 'evidence.add_evidence']``.
        """
        raise NotImplementedError(
            "MeView.get: Return user profile with permissions."
        )

    def patch(self, request: Request) -> Response:
        """
        Partially update the authenticated user's own profile.

        Implementation Contract
        -----------------------
        1. Instantiate ``MeUpdateSerializer(instance=request.user,
               data=request.data, partial=True)``.
        2. Validate.
        3. Call ``CurrentUserService.update_profile(
               request.user, serializer.validated_data
           )``.
        4. Re-serialize with ``UserDetailSerializer`` and return 200.
        """
        raise NotImplementedError(
            "MeView.patch: Validate → service → response."
        )


# ═══════════════════════════════════════════════════════════════════
#  User Management ViewSet
# ═══════════════════════════════════════════════════════════════════


class UserViewSet(viewsets.ViewSet):
    """
    /api/accounts/users/

    Administrative user management (list, retrieve, assign-role,
    activate, deactivate).

    Access: System Admin or officers with hierarchy_level above
    the target user.

    All heavy lifting is delegated to ``UserManagementService``.
    """

    permission_classes = [IsAuthenticated]

    # ── Standard actions ─────────────────────────────────────────

    def list(self, request: Request) -> Response:
        """
        GET /api/accounts/users/

        List all users with optional query-param filters:
        - ``role``           (int — Role PK)
        - ``hierarchy_level`` (int)
        - ``is_active``      (bool)
        - ``search``         (str — partial match on name/email/etc.)

        Implementation Contract
        -----------------------
        1. Extract filter params from ``request.query_params``.
        2. Call ``UserManagementService.list_users(**filters)``.
        3. Paginate the queryset (use DRF's default paginator).
        4. Serialize with ``UserListSerializer(many=True)``.
        5. Return paginated response.
        """
        raise NotImplementedError(
            "UserViewSet.list: Extract filters → service → paginate → response."
        )

    def retrieve(self, request: Request, pk: str = None) -> Response:
        """
        GET /api/accounts/users/{id}/

        Retrieve a single user's full details.

        Implementation Contract
        -----------------------
        1. Call ``UserManagementService.get_user(int(pk))``.
        2. Serialize with ``UserDetailSerializer``.
        3. Return ``Response(data, status=200)``.
        """
        raise NotImplementedError(
            "UserViewSet.retrieve: Service → serializer → response."
        )

    # ── Custom actions ───────────────────────────────────────────

    @action(detail=True, methods=["patch"], url_path="assign-role")
    def assign_role(self, request: Request, pk: str = None) -> Response:
        """
        PATCH /api/accounts/users/{id}/assign-role/

        Assign a role to a user.

        Request body → ``AssignRoleSerializer``
        Response     → ``UserDetailSerializer`` (200 OK)

        Implementation Contract
        -----------------------
        1. Validate ``request.data`` with ``AssignRoleSerializer``.
        2. Call ``UserManagementService.assign_role(
               user_id=int(pk),
               role_id=data['role_id'],
               performed_by=request.user,
           )``.
        3. Serialize the updated user and return 200.
        4. On ``PermissionDenied`` → 403.
        5. On ``DoesNotExist`` → 404.
        """
        raise NotImplementedError(
            "UserViewSet.assign_role: Validate → service → response."
        )

    @action(detail=True, methods=["patch"], url_path="activate")
    def activate(self, request: Request, pk: str = None) -> Response:
        """
        PATCH /api/accounts/users/{id}/activate/

        Activate a deactivated user.

        Response → ``UserDetailSerializer`` (200 OK)

        Implementation Contract
        -----------------------
        1. Call ``UserManagementService.activate_user(
               int(pk), performed_by=request.user
           )``.
        2. Serialize and return 200.
        """
        raise NotImplementedError(
            "UserViewSet.activate: Service → response."
        )

    @action(detail=True, methods=["patch"], url_path="deactivate")
    def deactivate(self, request: Request, pk: str = None) -> Response:
        """
        PATCH /api/accounts/users/{id}/deactivate/

        Deactivate an active user.

        Response → ``UserDetailSerializer`` (200 OK)

        Implementation Contract
        -----------------------
        1. Call ``UserManagementService.deactivate_user(
               int(pk), performed_by=request.user
           )``.
        2. Serialize and return 200.
        """
        raise NotImplementedError(
            "UserViewSet.deactivate: Service → response."
        )


# ═══════════════════════════════════════════════════════════════════
#  Role Management ViewSet
# ═══════════════════════════════════════════════════════════════════


class RoleViewSet(viewsets.ViewSet):
    """
    /api/accounts/roles/

    Full CRUD for Roles + permission assignment.

    Access: System Administrator only.

    Roles are dynamic (project-doc §2.2): the system admin can
    create, modify, or delete roles at runtime without touching code.
    """

    permission_classes = [IsAuthenticated]

    # ── Standard CRUD ────────────────────────────────────────────

    def list(self, request: Request) -> Response:
        """
        GET /api/accounts/roles/

        List all roles ordered by hierarchy level.

        Implementation Contract
        -----------------------
        1. Call ``RoleManagementService.list_roles()``.
        2. Serialize with ``RoleListSerializer(many=True)``.
        3. Return ``Response(data, status=200)``.
        """
        raise NotImplementedError(
            "RoleViewSet.list: Service → serializer → response."
        )

    def create(self, request: Request) -> Response:
        """
        POST /api/accounts/roles/

        Create a new role.

        Request body → ``RoleDetailSerializer``
        Response     → ``RoleDetailSerializer`` (201 Created)

        Implementation Contract
        -----------------------
        1. Validate with ``RoleDetailSerializer(data=request.data)``.
        2. Call ``RoleManagementService.create_role(serializer.validated_data)``.
        3. Re-serialize and return 201.
        """
        raise NotImplementedError(
            "RoleViewSet.create: Validate → service → response."
        )

    def retrieve(self, request: Request, pk: str = None) -> Response:
        """
        GET /api/accounts/roles/{id}/

        Retrieve a single role with full permission details.

        Implementation Contract
        -----------------------
        1. Call ``RoleManagementService.get_role(int(pk))``.
        2. Serialize with ``RoleDetailSerializer``.
        3. Return ``Response(data, status=200)``.
        """
        raise NotImplementedError(
            "RoleViewSet.retrieve: Service → serializer → response."
        )

    def update(self, request: Request, pk: str = None) -> Response:
        """
        PUT /api/accounts/roles/{id}/

        Full update of a role.

        Implementation Contract
        -----------------------
        1. Validate with ``RoleDetailSerializer(data=request.data)``.
        2. Call ``RoleManagementService.update_role(int(pk), data)``.
        3. Re-serialize and return 200.
        """
        raise NotImplementedError(
            "RoleViewSet.update: Validate → service → response."
        )

    def partial_update(self, request: Request, pk: str = None) -> Response:
        """
        PATCH /api/accounts/roles/{id}/

        Partial update of a role.

        Implementation Contract
        -----------------------
        1. Validate with ``RoleDetailSerializer(
               data=request.data, partial=True
           )``.
        2. Call ``RoleManagementService.update_role(int(pk), data)``.
        3. Re-serialize and return 200.
        """
        raise NotImplementedError(
            "RoleViewSet.partial_update: Validate → service → response."
        )

    def destroy(self, request: Request, pk: str = None) -> Response:
        """
        DELETE /api/accounts/roles/{id}/

        Delete a role (if no users are assigned to it).

        Implementation Contract
        -----------------------
        1. Call ``RoleManagementService.delete_role(int(pk))``.
        2. Return ``Response(status=204)``.
        3. On ``ValidationError`` (users still assigned) → 400.
        """
        raise NotImplementedError(
            "RoleViewSet.destroy: Service → 204 response."
        )

    # ── Custom action ────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="assign-permissions")
    def assign_permissions(
        self, request: Request, pk: str = None
    ) -> Response:
        """
        POST /api/accounts/roles/{id}/assign-permissions/

        Replace the role's permissions set with the given Permission IDs.

        Request body → ``RoleAssignPermissionsSerializer``
        Response     → ``RoleDetailSerializer`` (200 OK)

        Implementation Contract
        -----------------------
        1. Validate with ``RoleAssignPermissionsSerializer``.
        2. Call ``RoleManagementService.assign_permissions_to_role(
               role_id=int(pk),
               permission_ids=data['permission_ids'],
           )``.
        3. Re-serialize the updated role and return 200.
        """
        raise NotImplementedError(
            "RoleViewSet.assign_permissions: Validate → service → response."
        )


# ═══════════════════════════════════════════════════════════════════
#  Permission List View (Utility)
# ═══════════════════════════════════════════════════════════════════


class PermissionListView(generics.ListAPIView):
    """
    GET /api/accounts/permissions/

    Lists all available Django permissions.

    Used by the admin UI when building the permission-picker for
    role management.  Returns each permission's PK, human-readable
    ``name``, ``codename``, and the full ``app_label.codename`` string.

    Access: Authenticated (in practice, restricted to System Admin
    via frontend guard; could add ``IsAdminUser`` permission class
    for extra safety).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PermissionSerializer

    def get_queryset(self):
        """
        Implementation Contract
        -----------------------
        1. Call ``list_all_permissions()`` from services.
        2. Return the queryset.
        """
        raise NotImplementedError(
            "PermissionListView.get_queryset: "
            "Delegate to list_all_permissions() service."
        )
