"""
Accounts Service Layer.

This module is the **single source of truth** for all business logic
within the ``accounts`` app.  Views must remain *thin*: they validate
input through serializers, call a service function / method, and
return the result wrapped in a DRF ``Response``.

Architecture
------------
- ``UserRegistrationService``  — handles new-user creation flow.
- ``AuthenticationService``    — multi-field login + JWT issuance.
- ``UserManagementService``    — role assignment, activate / deactivate.
- ``RoleManagementService``    — Role CRUD, permission assignment.
- ``CurrentUserService``       — "Me" endpoint helpers.

Each public method includes a detailed docstring describing the
exact future implementation contract required to satisfy the
project-doc.md specification.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth import authenticate as django_authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet
from rest_framework_simplejwt.tokens import RefreshToken

from core.domain.exceptions import Conflict, DomainError, NotFound, PermissionDenied

from .models import Role

User = get_user_model()


# ═══════════════════════════════════════════════════════════════════
#  Registration Service
# ═══════════════════════════════════════════════════════════════════


class UserRegistrationService:
    """
    Encapsulates the user registration flow described in
    project-doc §4.1.
    """

    @staticmethod
    def register_user(validated_data: dict[str, Any]) -> User:
        """
        Create a new user and assign the default "Base User" role.

        Parameters
        ----------
        validated_data : dict
            Cleaned data from ``RegisterRequestSerializer`` containing
            ``username``, ``password``, ``email``, ``phone_number``,
            ``first_name``, ``last_name``, ``national_id``.
            ``password_confirm`` has already been consumed during
            serializer validation.

        Returns
        -------
        User
            The newly created (and saved) ``User`` instance.

        Implementation Contract
        -----------------------
        1. Pop ``password_confirm`` from ``validated_data`` (already
           consumed by serializer — but guard against its presence).
        2. Pop ``password`` so it is not passed to ``create()``.
        3. Look up the ``Role`` where ``name='Base User'``.  If it
           does not exist, create it with ``hierarchy_level=0``.
        4. Create the user via ``User.objects.create_user()`` so that
           the password is hashed automatically by Django.
        5. Assign the "Base User" role to the new user.
        6. Return the saved user.

        Notes
        -----
        - ``User.objects.create_user()`` handles password hashing and
          ``is_active=True`` by default.
        - After registration, the System Administrator later assigns
          the real role via ``UserManagementService.assign_role()``.

        Raises
        ------
        core.domain.exceptions.Conflict
            If a unique field (username, email, phone_number, national_id)
            is already taken.
        """
        # 1. Pop password_confirm (already consumed by serializer validation)
        validated_data.pop("password_confirm", None)

        # 2. Pop password so it's not passed to create() directly
        password = validated_data.pop("password")

        # 3. Pre-check uniqueness — deterministic, field-specific errors
        conflicts = []
        if User.objects.filter(username=validated_data.get("username")).exists():
            conflicts.append("username")
        if User.objects.filter(email=validated_data.get("email")).exists():
            conflicts.append("email")
        if User.objects.filter(phone_number=validated_data.get("phone_number")).exists():
            conflicts.append("phone_number")
        if User.objects.filter(national_id=validated_data.get("national_id")).exists():
            conflicts.append("national_id")

        if conflicts:
            raise Conflict(
                f"The following field(s) already exist: {', '.join(conflicts)}."
            )

        # 4. Look up the "Base User" role (case-insensitive); create if missing
        try:
            base_role = Role.objects.get(name__iexact="Base User")
        except Role.DoesNotExist:
            base_role = Role.objects.create(
                name="Base User",
                hierarchy_level=0,
                description="Default role for newly registered users.",
            )

        # 5. Create user inside an atomic block to guard against race conditions
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    password=password,
                    **validated_data,
                )
                user.role = base_role
                user.save(update_fields=["role"])
        except IntegrityError:
            raise Conflict(
                "A user with one of the provided unique fields already exists."
            )

        return user


# ═══════════════════════════════════════════════════════════════════
#  Authentication Service
# ═══════════════════════════════════════════════════════════════════


class AuthenticationService:
    """
    Handles multi-field login and JWT token generation.
    Supports identification via any one of: username, national_id,
    phone_number, or email (project-doc §4.1).
    """

    @staticmethod
    def resolve_user(identifier: str) -> User | None:
        """
        Attempt to locate a ``User`` by matching the ``identifier``
        against ``username``, ``national_id``, ``phone_number``, and
        ``email`` in that order.

        Parameters
        ----------
        identifier : str
            The value the client submitted (could be any of the four
            unique fields).

        Returns
        -------
        User or None
            The matched user, or ``None`` if no match is found.

        Implementation Contract
        -----------------------
        1. Try ``User.objects.get(username=identifier)``.
        2. If not found, try ``User.objects.get(national_id=identifier)``.
        3. If not found, try ``User.objects.get(phone_number=identifier)``.
        4. If not found, try ``User.objects.get(email=identifier)``.
        5. If none match, return ``None``.

        Performance note: all four fields are unique and indexed, so
        each lookup is O(1).
        """
        try:
            return User.objects.select_related("role").get(
                Q(username=identifier)
                | Q(national_id=identifier)
                | Q(phone_number=identifier)
                | Q(email=identifier)
            )
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return None

    @staticmethod
    def authenticate(identifier: str, password: str) -> User | None:
        """
        Validate credentials and return the user if successful.

        Parameters
        ----------
        identifier : str
            Any of the four unique identifiers.
        password : str
            The raw password.

        Returns
        -------
        User or None
            The authenticated user, or ``None`` if credentials are
            invalid or the user is inactive.

        Implementation Contract
        -----------------------
        1. Call ``resolve_user(identifier)`` to get the user.
        2. If user is ``None``, return ``None``.
        3. Call ``user.check_password(password)``.
        4. If password check fails, return ``None``.
        5. If ``user.is_active`` is ``False``, return ``None`` (or
           raise a specific exception for the view to return 403).
        6. Return the user.
        """
        user = django_authenticate(identifier=identifier, password=password)
        return user

    @staticmethod
    def generate_tokens(user: User) -> dict[str, str]:
        """
        Issue a JWT access/refresh token pair for the given user.

        Parameters
        ----------
        user : User
            An authenticated, active user.

        Returns
        -------
        dict
            ``{"access": "<token>", "refresh": "<token>"}``.

        Implementation Contract
        -----------------------
        1. Import ``RefreshToken`` from ``rest_framework_simplejwt.tokens``.
        2. Create a refresh token: ``refresh = RefreshToken.for_user(user)``.
        3. Return ``{"access": str(refresh.access_token),
                      "refresh": str(refresh)}``.

        Prerequisites
        -------------
        ``djangorestframework-simplejwt`` must be installed and configured
        in ``settings.py`` (``DEFAULT_AUTHENTICATION_CLASSES``,
        ``SIMPLE_JWT`` settings, etc.).
        """
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


# ═══════════════════════════════════════════════════════════════════
#  User Management Service
# ═══════════════════════════════════════════════════════════════════


class UserManagementService:
    """
    Administrative operations on users: listing, role assignment,
    activation, and deactivation.

    Access Policies (enforced in views via permissions/decorators):
    - Only System Admins or officers with ``hierarchy_level`` higher
      than the target user may assign roles or toggle activation.
    """

    @staticmethod
    def list_users(
        *,
        role_id: int | None = None,
        hierarchy_level: int | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> QuerySet[User]:
        """
        Return a filtered queryset of users.

        Parameters
        ----------
        role_id : int, optional
            Filter by ``role__id``.
        hierarchy_level : int, optional
            Filter by ``role__hierarchy_level``.
        is_active : bool, optional
            Filter by ``is_active`` status.
        search : str, optional
            Case-insensitive search across ``username``, ``email``,
            ``national_id``, ``phone_number``, ``first_name``,
            ``last_name``.

        Returns
        -------
        QuerySet[User]

        Implementation Contract
        -----------------------
        1. Start from ``User.objects.select_related('role').all()``.
        2. Apply ``.filter(role_id=role_id)`` if provided.
        3. Apply ``.filter(role__hierarchy_level=hierarchy_level)`` if
           provided.
        4. Apply ``.filter(is_active=is_active)`` if provided.
        5. Apply a ``Q`` search across the six text fields if
           ``search`` is provided.
        6. Return the queryset (allow DRF pagination in views).
        """
        qs = User.objects.select_related("role").all()

        if role_id is not None:
            qs = qs.filter(role_id=role_id)
        if hierarchy_level is not None:
            qs = qs.filter(role__hierarchy_level=hierarchy_level)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(national_id__icontains=search)
                | Q(phone_number__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )

        return qs

    @staticmethod
    def get_user(user_id: int) -> User:
        """
        Retrieve a single user by PK.

        Raises
        ------
        User.DoesNotExist
            Propagated as DRF 404 by the view.

        Implementation Contract
        -----------------------
        1. Return ``User.objects.select_related('role').get(pk=user_id)``.
        """
        try:
            return User.objects.select_related("role").get(pk=user_id)
        except User.DoesNotExist:
            raise NotFound(f"User with id {user_id} not found.")

    @staticmethod
    def assign_role(
        *,
        user_id: int,
        role_id: int,
        performed_by: User,
    ) -> User:
        """
        Assign (or change) a user's role.

        Parameters
        ----------
        user_id : int
            PK of the target user.
        role_id : int
            PK of the ``Role`` to assign.
        performed_by : User
            The requesting user (for authorization checks).

        Returns
        -------
        User
            The updated user.

        Implementation Contract
        -----------------------
        1. Fetch the target ``User`` and the ``Role``.
        2. **Authorization check**: the requesting user must be a
           System Admin OR have a ``hierarchy_level`` strictly
           greater than both the target user's current role AND
           the new role.
        3. Set ``target_user.role = new_role`` and save.
        4. Clear the user's ``_perm_cache`` (if cached) so
           ``get_all_permissions()`` reflects the new role.
        5. Return the updated user.

        Raises
        ------
        PermissionDenied
            If the requester lacks authority.
        Role.DoesNotExist / User.DoesNotExist
            Propagated as 404.
        """
        try:
            target_user = User.objects.select_related("role").get(pk=user_id)
        except User.DoesNotExist:
            raise NotFound(f"User with id {user_id} not found.")

        try:
            new_role = Role.objects.get(pk=role_id)
        except Role.DoesNotExist:
            raise NotFound(f"Role with id {role_id} not found.")

        # Authorization: must be System Admin OR hierarchy > both current and new role
        is_admin = performed_by.role and performed_by.role.name == "System Admin"
        if not is_admin:
            performer_level = performed_by.hierarchy_level
            target_current_level = target_user.hierarchy_level
            new_role_level = new_role.hierarchy_level
            if performer_level <= target_current_level or performer_level <= new_role_level:
                raise PermissionDenied(
                    "You do not have sufficient authority to assign this role."
                )

        target_user.role = new_role
        target_user.save(update_fields=["role"])

        # Invalidate permission cache
        if hasattr(target_user, "_perm_cache"):
            del target_user._perm_cache

        return target_user

    @staticmethod
    def activate_user(user_id: int, performed_by: User) -> User:
        """
        Set ``is_active=True`` on the target user.

        Parameters
        ----------
        user_id : int
            PK of the target user.
        performed_by : User
            The requesting admin/officer.

        Returns
        -------
        User
            The updated user.

        Implementation Contract
        -----------------------
        1. Fetch the target user.
        2. Authorization: requester must be System Admin or have
           hierarchy_level > target's hierarchy_level.
        3. Set ``user.is_active = True`` and save.
        4. Return user.
        """
        try:
            target_user = User.objects.select_related("role").get(pk=user_id)
        except User.DoesNotExist:
            raise NotFound(f"User with id {user_id} not found.")

        is_admin = performed_by.role and performed_by.role.name == "System Admin"
        if not is_admin and performed_by.hierarchy_level <= target_user.hierarchy_level:
            raise PermissionDenied(
                "You do not have sufficient authority to activate this user."
            )

        target_user.is_active = True
        target_user.save(update_fields=["is_active"])
        return target_user

    @staticmethod
    def deactivate_user(user_id: int, performed_by: User) -> User:
        """
        Set ``is_active=False`` on the target user.

        Parameters
        ----------
        user_id : int
            PK of the target user.
        performed_by : User
            The requesting admin/officer.

        Returns
        -------
        User
            The updated user.

        Implementation Contract
        -----------------------
        1. Fetch the target user.
        2. Authorization: requester must be System Admin or have
           hierarchy_level > target's hierarchy_level.
        3. Prevent self-deactivation (raise ``ValidationError``).
        4. Set ``user.is_active = False`` and save.
        5. Return user.
        """
        try:
            target_user = User.objects.select_related("role").get(pk=user_id)
        except User.DoesNotExist:
            raise NotFound(f"User with id {user_id} not found.")

        # Prevent self-deactivation
        if target_user.pk == performed_by.pk:
            raise DomainError("You cannot deactivate your own account.")

        is_admin = performed_by.role and performed_by.role.name == "System Admin"
        if not is_admin and performed_by.hierarchy_level <= target_user.hierarchy_level:
            raise PermissionDenied(
                "You do not have sufficient authority to deactivate this user."
            )

        target_user.is_active = False
        target_user.save(update_fields=["is_active"])
        return target_user


# ═══════════════════════════════════════════════════════════════════
#  Role Management Service
# ═══════════════════════════════════════════════════════════════════


class RoleManagementService:
    """
    CRUD operations for roles and permission assignment.

    Only System Administrators should have access (enforced at the
    view / permission level).  Roles are fully dynamic — the system
    admin can create, rename, re-level, or delete roles at runtime
    without code changes (project-doc §2.2).
    """

    @staticmethod
    def list_roles() -> QuerySet[Role]:
        """
        Return all roles ordered by ``-hierarchy_level``.

        Implementation Contract
        -----------------------
        1. Return ``Role.objects.all()`` (default ordering is
           ``-hierarchy_level`` from the model Meta).
        """
        return Role.objects.all()

    @staticmethod
    def create_role(validated_data: dict[str, Any]) -> Role:
        """
        Create a new role.

        Parameters
        ----------
        validated_data : dict
            Fields: ``name``, ``description``, ``hierarchy_level``,
            and optionally ``permissions`` (list of Permission PKs).

        Returns
        -------
        Role

        Implementation Contract
        -----------------------
        1. Pop ``permissions`` list if present.
        2. Create the ``Role`` object.
        3. If permissions were provided, call
           ``role.permissions.set(permission_pks)``.
        4. Return the role.
        """
        permission_pks = validated_data.pop("permissions", None)
        role = Role.objects.create(**validated_data)
        if permission_pks is not None:
            role.permissions.set(permission_pks)
        return role

    @staticmethod
    def get_role(role_id: int) -> Role:
        """
        Retrieve a single role by PK.

        Implementation Contract
        -----------------------
        1. Return ``Role.objects.prefetch_related(
               'permissions__content_type'
           ).get(pk=role_id)``.
        """
        try:
            return Role.objects.prefetch_related(
                "permissions__content_type"
            ).get(pk=role_id)
        except Role.DoesNotExist:
            raise NotFound(f"Role with id {role_id} not found.")

    @staticmethod
    def update_role(role_id: int, validated_data: dict[str, Any]) -> Role:
        """
        Update an existing role's fields.

        Parameters
        ----------
        role_id : int
            PK of the role.
        validated_data : dict
            Partial or full fields.

        Returns
        -------
        Role

        Implementation Contract
        -----------------------
        1. Fetch the role.
        2. Pop ``permissions`` if present and call
           ``role.permissions.set(...)`` separately.
        3. Update remaining scalar fields.
        4. Save and return the role.
        5. **Important**: after changing a role's permissions, all
           users with this role should have their ``_perm_cache``
           invalidated.  (In the simplest approach this happens
           naturally on the next request because the cache is
           per-request.)
        """
        try:
            role = Role.objects.prefetch_related(
                "permissions__content_type"
            ).get(pk=role_id)
        except Role.DoesNotExist:
            raise NotFound(f"Role with id {role_id} not found.")

        permission_pks = validated_data.pop("permissions", None)

        for field, value in validated_data.items():
            setattr(role, field, value)
        role.save()

        if permission_pks is not None:
            role.permissions.set(permission_pks)

        # Refresh from DB so prefetch is accurate
        role.refresh_from_db()
        return Role.objects.prefetch_related(
            "permissions__content_type"
        ).get(pk=role.pk)

    @staticmethod
    def delete_role(role_id: int) -> None:
        """
        Delete a role.

        Implementation Contract
        -----------------------
        1. Fetch the role.
        2. Check that no users are currently assigned to this role
           (``role.users.exists()``).  If users exist, raise
           ``ValidationError`` to prevent orphan records (or
           alternatively re-assign them to "Base User" — product
           decision).
        3. Delete the role.
        """
        try:
            role = Role.objects.get(pk=role_id)
        except Role.DoesNotExist:
            raise NotFound(f"Role with id {role_id} not found.")

        if role.users.exists():
            raise DomainError(
                f"Cannot delete role '{role.name}' because it is still assigned to "
                f"{role.users.count()} user(s). Re-assign them first."
            )

        role.delete()

    @staticmethod
    def assign_permissions_to_role(
        role_id: int,
        permission_ids: list[int],
    ) -> Role:
        """
        Replace the role's permissions set with the given IDs.

        Parameters
        ----------
        role_id : int
            PK of the role.
        permission_ids : list[int]
            Django ``auth.Permission`` PKs.

        Returns
        -------
        Role
            The updated role with new permissions.

        Implementation Contract
        -----------------------
        1. Fetch the role.
        2. Validate that all ``permission_ids`` exist.
        3. ``role.permissions.set(permission_ids)``.
        4. Return the role with prefetched permissions.
        """
        try:
            role = Role.objects.get(pk=role_id)
        except Role.DoesNotExist:
            raise NotFound(f"Role with id {role_id} not found.")

        # Validate that all permission IDs exist
        existing = set(
            Permission.objects.filter(pk__in=permission_ids)
            .values_list("pk", flat=True)
        )
        invalid = set(permission_ids) - existing
        if invalid:
            raise DomainError(
                f"The following permission IDs do not exist: {sorted(invalid)}"
            )

        role.permissions.set(permission_ids)

        return Role.objects.prefetch_related(
            "permissions__content_type"
        ).get(pk=role.pk)


# ═══════════════════════════════════════════════════════════════════
#  Current User (Me) Service
# ═══════════════════════════════════════════════════════════════════


class CurrentUserService:
    """
    Helpers for the "Me" endpoint.

    The "Me" endpoint (project-doc §5.3 — modular dashboard) is the
    primary way the Next.js frontend discovers:
    - Who the logged-in user is.
    - What ``Role`` they hold.
    - A **flat list of permission strings** used to conditionally
      render UI modules (e.g., show "Detective Board" only if the
      user has detective-level permissions).
    """

    @staticmethod
    def get_profile(user: User) -> User:
        """
        Return the user instance with role and permissions
        pre-fetched for serialization.

        Parameters
        ----------
        user : User
            The currently authenticated user (from ``request.user``).

        Returns
        -------
        User
            The same user instance, but with ``select_related('role')``
            and the role's permissions prefetched so that
            ``UserDetailSerializer`` can render the full payload
            without N+1 queries.

        Implementation Contract
        -----------------------
        1. Re-fetch the user with:
           ``User.objects.select_related('role')
                .prefetch_related('role__permissions__content_type')
                .get(pk=user.pk)``
        2. Return the enriched instance.
        """
        return (
            User.objects.select_related("role")
            .prefetch_related("role__permissions__content_type")
            .get(pk=user.pk)
        )

    @staticmethod
    def update_profile(user: User, validated_data: dict[str, Any]) -> User:
        """
        Update the authenticated user's own profile fields.

        Parameters
        ----------
        user : User
            The currently authenticated user.
        validated_data : dict
            Cleaned fields from ``MeUpdateSerializer`` (email,
            phone_number, first_name, last_name).

        Returns
        -------
        User
            The updated user.

        Implementation Contract
        -----------------------
        1. Update only the fields present in ``validated_data``.
        2. Save the user.
        3. Return the updated user.

        Notes
        -----
        The user may NOT change their own ``role``, ``is_active``,
        ``username``, or ``national_id`` via this endpoint.
        """
        for field, value in validated_data.items():
            setattr(user, field, value)
        user.save(update_fields=list(validated_data.keys()))

        # Re-fetch with prefetched relations for serialization
        return (
            User.objects.select_related("role")
            .prefetch_related("role__permissions__content_type")
            .get(pk=user.pk)
        )


# ═══════════════════════════════════════════════════════════════════
#  Utility: Permission Listing
# ═══════════════════════════════════════════════════════════════════


def list_all_permissions() -> QuerySet[Permission]:
    """
    Return all Django permissions available in the system.

    Used by the admin UI when selecting which permissions to
    assign to a role.

    Implementation Contract
    -----------------------
    1. Return ``Permission.objects.select_related('content_type').all()``.
    2. Optionally filter to only project-app permissions (exclude
       Django internal apps like ``admin``, ``contenttypes``, etc.)
       for cleaner UX.
    """
    return Permission.objects.select_related("content_type").all()
