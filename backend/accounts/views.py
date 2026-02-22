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

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
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

    @extend_schema(
        summary="Register new user",
        description=(
            "Public endpoint. Creates a new user account with the default "
            "'Base User' role. No authentication required."
        ),
        request=RegisterRequestSerializer,
        responses={
            201: OpenApiResponse(response=UserDetailSerializer, description="User created successfully."),
            400: OpenApiResponse(description="Validation error (duplicate username/email, password mismatch, etc.)."),
        },
        tags=["Auth"],
    )
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

    @extend_schema(
        summary="Login and obtain JWT tokens",
        description=(
            "Public endpoint. Authenticates a user using any unique identifier "
            "(username, national ID, phone number, or email) plus password. "
            "Returns JWT access/refresh tokens and user profile."
        ),
        request=LoginRequestSerializer,
        responses={
            200: OpenApiResponse(response=TokenResponseSerializer, description="Authentication successful. Returns JWT tokens and user info."),
            400: OpenApiResponse(description="Invalid credentials or disabled account."),
        },
        tags=["Auth"],
    )
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

    @extend_schema(
        summary="Get current user profile",
        description=(
            "Returns the authenticated user's full profile including role "
            "details and a flat permissions list. Requires authentication."
        ),
        responses={
            200: OpenApiResponse(response=UserDetailSerializer, description="Current user profile."),
            401: OpenApiResponse(description="Authentication credentials not provided."),
        },
        tags=["Auth"],
    )
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
        user = CurrentUserService.get_profile(request.user)
        serializer = UserDetailSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update current user profile",
        description=(
            "Partially update the authenticated user's own profile fields "
            "(email, phone_number, first_name, last_name). Requires authentication."
        ),
        request=MeUpdateSerializer,
        responses={
            200: OpenApiResponse(response=UserDetailSerializer, description="Profile updated successfully."),
            400: OpenApiResponse(description="Validation error (duplicate email/phone, invalid format)."),
            401: OpenApiResponse(description="Authentication credentials not provided."),
        },
        tags=["Auth"],
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
        serializer = MeUpdateSerializer(
            instance=request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        updated_user = CurrentUserService.update_profile(
            request.user, serializer.validated_data
        )
        return Response(
            UserDetailSerializer(updated_user).data,
            status=status.HTTP_200_OK,
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

    @extend_schema(
        summary="List all users",
        description=(
            "List all users with optional query-param filters. "
            "Requires authentication. Typically used by System Admin or high-ranking officers."
        ),
        parameters=[
            OpenApiParameter(name="role", type=int, location=OpenApiParameter.QUERY, description="Filter by Role PK."),
            OpenApiParameter(name="hierarchy_level", type=int, location=OpenApiParameter.QUERY, description="Filter by hierarchy level."),
            OpenApiParameter(name="is_active", type=bool, location=OpenApiParameter.QUERY, description="Filter by active status."),
            OpenApiParameter(name="search", type=str, location=OpenApiParameter.QUERY, description="Partial match on name, email, username, national ID."),
        ],
        responses={
            200: OpenApiResponse(response=UserListSerializer(many=True), description="List of users."),
            401: OpenApiResponse(description="Authentication credentials not provided."),
        },
        tags=["Users"],
    )
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
        filters = {}
        role = request.query_params.get("role")
        if role is not None:
            filters["role_id"] = int(role)
        hierarchy_level = request.query_params.get("hierarchy_level")
        if hierarchy_level is not None:
            filters["hierarchy_level"] = int(hierarchy_level)
        is_active = request.query_params.get("is_active")
        if is_active is not None:
            filters["is_active"] = is_active.lower() in ("true", "1", "yes")
        search = request.query_params.get("search")
        if search:
            filters["search"] = search

        qs = UserManagementService.list_users(**filters)
        serializer = UserListSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Retrieve user details",
        description=(
            "Get a single user's full details by ID. Requires authentication."
        ),
        responses={
            200: OpenApiResponse(response=UserDetailSerializer, description="User detail."),
            401: OpenApiResponse(description="Authentication credentials not provided."),
            404: OpenApiResponse(description="User not found."),
        },
        tags=["Users"],
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
        user = UserManagementService.get_user(int(pk))
        serializer = UserDetailSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ── Custom actions ───────────────────────────────────────────

    @action(detail=True, methods=["patch"], url_path="assign-role")
    @extend_schema(
        summary="Assign role to user",
        description=(
            "Assign a role to a user by providing a role_id. "
            "Requires System Admin or higher hierarchy than the target user."
        ),
        request=AssignRoleSerializer,
        responses={
            200: OpenApiResponse(response=UserDetailSerializer, description="Role assigned successfully."),
            400: OpenApiResponse(description="Validation error (invalid role_id)."),
            403: OpenApiResponse(description="Permission denied. Requires System Admin or higher hierarchy."),
            404: OpenApiResponse(description="User or Role not found."),
        },
        tags=["Users"],
    )
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
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = UserManagementService.assign_role(
            user_id=int(pk),
            role_id=serializer.validated_data["role_id"],
            performed_by=request.user,
        )
        return Response(
            UserDetailSerializer(user).data, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["patch"], url_path="activate")
    @extend_schema(
        summary="Activate a user",
        description=(
            "Re-activate a deactivated user account. "
            "Requires System Admin or higher hierarchy level."
        ),
        request=None,
        responses={
            200: OpenApiResponse(response=UserDetailSerializer, description="User activated."),
            403: OpenApiResponse(description="Permission denied."),
            404: OpenApiResponse(description="User not found."),
        },
        tags=["Users"],
    )
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
        user = UserManagementService.activate_user(
            int(pk), performed_by=request.user
        )
        return Response(
            UserDetailSerializer(user).data, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["patch"], url_path="deactivate")
    @extend_schema(
        summary="Deactivate a user",
        description=(
            "Deactivate an active user account. "
            "Requires System Admin or higher hierarchy level."
        ),
        request=None,
        responses={
            200: OpenApiResponse(response=UserDetailSerializer, description="User deactivated."),
            403: OpenApiResponse(description="Permission denied."),
            404: OpenApiResponse(description="User not found."),
        },
        tags=["Users"],
    )
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
        user = UserManagementService.deactivate_user(
            int(pk), performed_by=request.user
        )
        return Response(
            UserDetailSerializer(user).data, status=status.HTTP_200_OK
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

    @extend_schema(
        summary="List all roles",
        description=(
            "List all roles ordered by hierarchy level. "
            "Requires authentication. Typically restricted to System Admin."
        ),
        responses={
            200: OpenApiResponse(response=RoleListSerializer(many=True), description="List of roles."),
            401: OpenApiResponse(description="Authentication credentials not provided."),
        },
        tags=["Roles"],
    )
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
        roles = RoleManagementService.list_roles()
        serializer = RoleListSerializer(roles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Create a new role",
        description=(
            "Create a new dynamic role with a name, description, and hierarchy level. "
            "Requires System Admin role."
        ),
        request=RoleDetailSerializer,
        responses={
            201: OpenApiResponse(response=RoleDetailSerializer, description="Role created."),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Permission denied. Requires System Admin."),
        },
        tags=["Roles"],
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
        serializer = RoleDetailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = RoleManagementService.create_role(serializer.validated_data)
        return Response(
            RoleDetailSerializer(role).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(
        summary="Retrieve role details",
        description=(
            "Get a single role with full permission details. Requires authentication."
        ),
        responses={
            200: OpenApiResponse(response=RoleDetailSerializer, description="Role detail with permissions."),
            404: OpenApiResponse(description="Role not found."),
        },
        tags=["Roles"],
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
        role = RoleManagementService.get_role(int(pk))
        serializer = RoleDetailSerializer(role)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Full update of a role",
        description=(
            "Replace all fields of an existing role. Requires System Admin role."
        ),
        request=RoleDetailSerializer,
        responses={
            200: OpenApiResponse(response=RoleDetailSerializer, description="Role updated."),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Permission denied."),
            404: OpenApiResponse(description="Role not found."),
        },
        tags=["Roles"],
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
        serializer = RoleDetailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = RoleManagementService.update_role(int(pk), serializer.validated_data)
        return Response(
            RoleDetailSerializer(role).data, status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Partial update of a role",
        description=(
            "Update selected fields of an existing role. Requires System Admin role."
        ),
        request=RoleDetailSerializer,
        responses={
            200: OpenApiResponse(response=RoleDetailSerializer, description="Role partially updated."),
            400: OpenApiResponse(description="Validation error."),
            404: OpenApiResponse(description="Role not found."),
        },
        tags=["Roles"],
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
        serializer = RoleDetailSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        role = RoleManagementService.update_role(int(pk), serializer.validated_data)
        return Response(
            RoleDetailSerializer(role).data, status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Delete a role",
        description=(
            "Delete a role if no users are assigned to it. Requires System Admin role."
        ),
        responses={
            204: OpenApiResponse(description="Role deleted."),
            400: OpenApiResponse(description="Cannot delete: users are still assigned to this role."),
            404: OpenApiResponse(description="Role not found."),
        },
        tags=["Roles"],
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
        RoleManagementService.delete_role(int(pk))
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── Custom action ────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="assign-permissions")
    @extend_schema(
        summary="Assign permissions to role",
        description=(
            "Replace the role's permission set with the given Permission IDs. "
            "Requires System Admin role."
        ),
        request=RoleAssignPermissionsSerializer,
        responses={
            200: OpenApiResponse(response=RoleDetailSerializer, description="Permissions assigned."),
            400: OpenApiResponse(description="Invalid permission IDs."),
            404: OpenApiResponse(description="Role not found."),
        },
        tags=["Roles"],
    )
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
        serializer = RoleAssignPermissionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = RoleManagementService.assign_permissions_to_role(
            role_id=int(pk),
            permission_ids=serializer.validated_data["permission_ids"],
        )
        return Response(
            RoleDetailSerializer(role).data, status=status.HTTP_200_OK
        )


# ═══════════════════════════════════════════════════════════════════
#  Permission List View (Utility)
# ═══════════════════════════════════════════════════════════════════


@extend_schema(
    summary="List all permissions",
    description=(
        "Lists all available Django permissions (PK, name, codename). "
        "Used by the admin UI for building role permission pickers. "
        "Requires authentication."
    ),
    responses={
        200: OpenApiResponse(response=PermissionSerializer(many=True), description="List of permissions."),
    },
    tags=["Roles"],
)
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
        return list_all_permissions()
