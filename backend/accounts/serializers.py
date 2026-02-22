"""
Accounts app serializers.

Contains all Request and Response serializers for the accounts API.
Serializers handle field definitions, read/write constraints, and
basic validation.  **No business logic** lives here — all domain
rules are delegated to ``services.py``.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework import serializers

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
        Cross-field validation stub.

        Future implementation MUST:
        1. Ensure ``password`` and ``password_confirm`` match.
        2. Validate ``national_id`` format (exactly 10 digits).
        3. Validate ``phone_number`` format (Iranian mobile format).
        4. Delegate any additional checks to django password validators.
        """
        raise NotImplementedError(
            "RegisterRequestSerializer.validate: "
            "Implement password-match check, national_id & phone format validation."
        )


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
    )


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
        raise NotImplementedError(
            "TokenResponseSerializer.get_user: Serialize user via UserDetailSerializer."
        )


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
        raise NotImplementedError(
            "RoleDetailSerializer.get_permissions_display: "
            "Return flat list of 'app_label.codename' strings."
        )


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
        raise NotImplementedError(
            "RoleAssignPermissionsSerializer.validate_permission_ids: "
            "Check all PKs exist in auth_permission table."
        )


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
        help_text="PK of the Role to assign to this user.",
    )

    def validate_role_id(self, value: int) -> int:
        """
        Ensure the Role exists.

        Future implementation MUST:
        1. Return the value if Role with pk=value exists.
        2. Raise ``ValidationError`` otherwise.
        """
        raise NotImplementedError(
            "AssignRoleSerializer.validate_role_id: "
            "Verify Role PK exists."
        )


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
        raise NotImplementedError(
            "MeUpdateSerializer.validate_email: Uniqueness check stub."
        )

    def validate_phone_number(self, value: str) -> str:
        """
        Ensure the new phone number is unique and valid format.

        Future implementation MUST:
        1. Check uniqueness excluding current user.
        2. Validate phone format.
        """
        raise NotImplementedError(
            "MeUpdateSerializer.validate_phone_number: Uniqueness + format check stub."
        )


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
        raise NotImplementedError(
            "PermissionSerializer.get_full_codename: "
            "Return 'app_label.codename'."
        )
