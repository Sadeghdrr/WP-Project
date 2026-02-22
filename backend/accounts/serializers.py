"""
Accounts app serializers.

Contains all Request and Response serializers for the accounts API.
Serializers handle field definitions, read/write constraints, and
basic validation.  **No business logic** lives here — all domain
rules are delegated to ``services.py``.
"""

from __future__ import annotations

import re
from typing import Any

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Permission
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Role

User = get_user_model()


# ═══════════════════════════════════════════════════════════════════
#  Authentication Serializers
# ═══════════════════════════════════════════════════════════════════


class RegisterRequestSerializer(serializers.ModelSerializer):
    """
    Validates new-user registration data.

    Required fields: username, password, email, phone_number,
    first_name, last_name, national_id.

    The ``password`` field is write-only and will be hashed by the
    service layer before persisting.  The response after a successful
    registration is handled by ``UserDetailSerializer``.
    """

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
        help_text="Minimum 8 characters.",
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        help_text="Must match 'password'.",
    )

    class Meta:
        model = User
        fields = [
            "username",
            "password",
            "password_confirm",
            "email",
            "phone_number",
            "first_name",
            "last_name",
            "national_id",
        ]
        extra_kwargs = {
            "email": {"required": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
            "national_id": {"required": True},
            "phone_number": {"required": True},
        }

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Cross-field validation:
        1. Ensure password and password_confirm match.
        2. Validate national_id format (exactly 10 digits).
        3. Validate phone_number format (Iranian mobile).
        """
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )

        national_id = attrs.get("national_id", "")
        if not national_id.isdigit() or len(national_id) != 10:
            raise serializers.ValidationError(
                {"national_id": "National ID must be exactly 10 digits."}
            )

        phone = attrs.get("phone_number", "")
        if not re.match(r"^(\+98|0)?9\d{9}$", phone):
            raise serializers.ValidationError(
                {"phone_number": "Phone number must be a valid Iranian mobile number (e.g. 09121234567)."}
            )

        # Remove password_confirm — not needed beyond validation
        attrs.pop("password_confirm")

        return attrs


class LoginRequestSerializer(serializers.Serializer):
    """
    Accepts multi-field login credentials.

    The client sends ``identifier`` (which may be a username,
    national_id, phone_number, or email) together with ``password``.
    The service layer resolves the user from the identifier.
    """

    identifier = serializers.CharField(
        help_text="Username, National ID, Phone Number, or Email.",
    )
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        help_text="User account password.",
    )


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom SimpleJWT serializer that:

    1. Accepts ``identifier`` + ``password`` instead of
       ``username`` + ``password``.
    2. Resolves the user via the ``MultiFieldAuthBackend``.
    3. Injects RBAC claims (``role``, ``hierarchy_level``,
       ``permissions_list``) into the JWT access token payload.
    4. Returns the token pair plus a nested ``user`` object in
       the response body.
    """

    # Override the default username field with our multi-field identifier
    username_field = "identifier"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the default 'username' field added by SimpleJWT
        # and replace with 'identifier'
        self.fields.pop(self.username_field, None)
        self.fields["identifier"] = serializers.CharField(
            help_text="Username, National ID, Phone Number, or Email.",
        )

    @classmethod
    def get_token(cls, user) -> Any:
        """
        Add custom RBAC claims to the JWT payload so the frontend
        can decode role info without a separate API call.
        """
        token = super().get_token(user)

        # Inject RBAC claims
        token["role"] = user.role.name if user.role else None
        token["hierarchy_level"] = user.hierarchy_level
        token["permissions_list"] = user.permissions_list

        return token

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Authenticate using the custom ``MultiFieldAuthBackend``.

        Returns a dict containing ``access``, ``refresh``, and
        ``user`` (serialized via ``UserDetailSerializer``).
        """
        identifier = attrs.get("identifier")
        password = attrs.get("password")

        # Authenticate via our custom backend
        user = authenticate(
            request=self.context.get("request"),
            identifier=identifier,
            password=password,
        )

        if user is None:
            raise serializers.ValidationError(
                {"detail": "Invalid credentials."},
                code="authentication",
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": "User account is disabled."},
                code="authentication",
            )

        # Generate tokens with custom claims
        refresh = self.get_token(user)
        data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

        # Attach user for the view to serialise in the response
        self.user = user

        return data


class TokenResponseSerializer(serializers.Serializer):
    """
    Serializes the JWT token pair returned after successful login.
    """

    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = serializers.SerializerMethodField()

    def get_user(self, obj: dict) -> dict:
        """
        Nest minimal user info alongside tokens.

        Future implementation MUST return the user representation
        using ``UserDetailSerializer``.
        """
        user = obj.get("user")
        if user:
            return UserDetailSerializer(user).data
        return None


# ═══════════════════════════════════════════════════════════════════
#  Role Serializers
# ═══════════════════════════════════════════════════════════════════


class RoleListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing roles (no permissions detail).
    """

    class Meta:
        model = Role
        fields = ["id", "name", "description", "hierarchy_level"]
        read_only_fields = ["id"]


class RoleDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for Role CRUD including nested permission IDs.

    ``permissions`` is a list of permission PKs (writable on
    create / update) and resolves to full codename strings on read.
    """

    permissions_display = serializers.SerializerMethodField(
        help_text="Flat list of 'app_label.codename' strings (read-only).",
    )

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "description",
            "hierarchy_level",
            "permissions",
            "permissions_display",
        ]
        read_only_fields = ["id", "permissions_display"]

    def get_permissions_display(self, obj: Role) -> list[str]:
        """
        Convert related Permission objects to ``['app_label.codename', ...]``.

        Future implementation MUST:
        1. Query ``obj.permissions`` with ``select_related('content_type')``.
        2. Return a flat list of ``f"{p.content_type.app_label}.{p.codename}"``.
        """
        perms = obj.permissions.select_related("content_type").all()
        return [f"{p.content_type.app_label}.{p.codename}" for p in perms]


class RoleAssignPermissionsSerializer(serializers.Serializer):
    """
    Accepts a list of Django Permission IDs to assign to a Role.
    Used by the ``assign-permissions`` action on ``RoleViewSet``.
    """

    permission_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of Django Permission PKs to assign to this Role.",
    )

    def validate_permission_ids(self, value: list[int]) -> list[int]:
        """
        Validate that all provided IDs correspond to existing Permission objects.

        Future implementation MUST:
        1. Query ``Permission.objects.filter(pk__in=value)``.
        2. Raise ``ValidationError`` if any IDs are invalid.
        """
        existing_ids = set(
            Permission.objects.filter(pk__in=value).values_list("pk", flat=True)
        )
        invalid_ids = set(value) - existing_ids
        if invalid_ids:
            raise serializers.ValidationError(
                f"The following permission IDs do not exist: {sorted(invalid_ids)}"
            )
        return value


# ═══════════════════════════════════════════════════════════════════
#  User Serializers
# ═══════════════════════════════════════════════════════════════════


class UserListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing users (admin views).
    Includes role name and hierarchy level for quick scanning.
    """

    role_name = serializers.CharField(
        source="role.name",
        read_only=True,
        default=None,
    )
    hierarchy_level = serializers.IntegerField(
        source="role.hierarchy_level",
        read_only=True,
        default=0,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "national_id",
            "phone_number",
            "first_name",
            "last_name",
            "is_active",
            "role",
            "role_name",
            "hierarchy_level",
        ]
        read_only_fields = fields


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Full user representation (used in retrieve, me, and registration
    response).  Includes the nested role object and a flat permissions
    list consumed by the Next.js frontend to conditionally render UI
    components.

    ``permissions`` is a read-only flat list such as:
        ['cases.view_case', 'evidence.add_evidence', ...]
    """

    role_detail = RoleListSerializer(source="role", read_only=True)
    permissions = serializers.ListField(
        child=serializers.CharField(),
        source="permissions_list",
        read_only=True,
        help_text="Flat list of 'app_label.codename' permission strings.",
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "national_id",
            "phone_number",
            "first_name",
            "last_name",
            "is_active",
            "date_joined",
            "role",
            "role_detail",
            "permissions",
        ]
        read_only_fields = [
            "id",
            "username",
            "date_joined",
            "is_active",
            "role",
            "role_detail",
            "permissions",
        ]


class AssignRoleSerializer(serializers.Serializer):
    """
    Accepts a ``role_id`` to assign to a user.

    Used by the ``assign-role`` action on ``UserViewSet``.
    Only System Admins or high-ranking officers (above the target user's
    hierarchy) are authorized.
    """

    role_id = serializers.IntegerField(
        help_text="PK of the Role to assign to this user. Must reference an existing Role.",
    )

    def validate_role_id(self, value: int) -> int:
        """
        Ensure the Role exists.

        Future implementation MUST:
        1. Return the value if Role with pk=value exists.
        2. Raise ``ValidationError`` otherwise.
        """
        if not Role.objects.filter(pk=value).exists():
            raise serializers.ValidationError(
                f"Role with id {value} does not exist."
            )
        return value


class MeUpdateSerializer(serializers.ModelSerializer):
    """
    Allows the authenticated user to update limited profile fields.
    Sensitive fields (role, is_active, username) are read-only and
    cannot be self-modified.
    """

    class Meta:
        model = User
        fields = [
            "email",
            "phone_number",
            "first_name",
            "last_name",
        ]

    def validate_email(self, value: str) -> str:
        """
        Ensure the new email is unique (excluding the current user).

        Future implementation MUST:
        1. Check ``User.objects.exclude(pk=self.instance.pk).filter(email=value)``.
        2. Raise ``ValidationError`` if duplicate.
        """
        if (
            self.instance
            and User.objects.exclude(pk=self.instance.pk)
            .filter(email=value)
            .exists()
        ):
            raise serializers.ValidationError(
                "This email is already in use by another account."
            )
        return value

    def validate_phone_number(self, value: str) -> str:
        """
        Ensure the new phone number is unique and valid format.

        Future implementation MUST:
        1. Check uniqueness excluding current user.
        2. Validate phone format.
        """
        if not re.match(r"^(\+98|0)?9\d{9}$", value):
            raise serializers.ValidationError(
                "Phone number must be a valid Iranian mobile number (e.g. 09121234567)."
            )
        if (
            self.instance
            and User.objects.exclude(pk=self.instance.pk)
            .filter(phone_number=value)
            .exists()
        ):
            raise serializers.ValidationError(
                "This phone number is already in use by another account."
            )
        return value


# ═══════════════════════════════════════════════════════════════════
#  Utility Serializers
# ═══════════════════════════════════════════════════════════════════


class PermissionSerializer(serializers.ModelSerializer):
    """
    Serializer for listing all available Django permissions.
    Used by admin UI when assigning permissions to roles.

    Returns ``app_label.codename`` as a convenience field alongside
    the raw PK so the admin can select permissions by human-readable
    label but submit by ID.
    """

    full_codename = serializers.SerializerMethodField(
        help_text="'app_label.codename' string.",
    )

    class Meta:
        model = Permission
        fields = ["id", "name", "codename", "full_codename"]
        read_only_fields = fields

    def get_full_codename(self, obj: Permission) -> str:
        """
        Return 'app_label.codename'.

        Future implementation MUST:
        1. Access ``obj.content_type.app_label``.
        2. Return ``f"{app_label}.{obj.codename}"``.
        """
        return f"{obj.content_type.app_label}.{obj.codename}"
