"""
core.domain.access — Permission-scoped queryset selectors (shared patterns).

This module provides shared utilities that each app's service layer
calls to obtain querysets filtered by the requesting user's permissions.

╔══════════════════════════════════════════════════════════════════╗
║  IMPORTANT — Per-app scoping logic does NOT live here.         ║
║  Each app's ``services.py`` owns its own scope-rules list.     ║
║  This module provides:                                         ║
║    1) ``apply_permission_scope`` — ordered permission dispatch.║
║    2) ``require_permission`` — guard that checks has_perm.     ║
║    3) ``get_user_role_name`` — informational role-name helper. ║
╚══════════════════════════════════════════════════════════════════╝

Architecture overview
---------------------
Permission-based data access follows a **scope-rule** pattern:

    ┌─────────┐      ┌────────────────┐      ┌──────────────────┐
    │  View   │─────▶│  App service   │─────▶│ core.domain      │
    │ (thin)  │      │ (owns logic)   │      │   .access        │
    └─────────┘      └────────────────┘      │ (shared helpers) │
                                             └──────────────────┘

Usage in an app's service layer::

    from core.domain.access import apply_permission_scope

    CASE_SCOPE_RULES = [
        ("cases.can_scope_all_cases",       lambda qs, u: qs),
        ("cases.can_scope_assigned_cases",  lambda qs, u: qs.filter(assigned_detective=u)),
        ("cases.can_scope_own_cases",       lambda qs, u: qs.filter(created_by=u)),
    ]

    class CaseQueryService:
        def get_filtered_queryset(self, user):
            qs = Case.objects.all()
            return apply_permission_scope(qs, user, scope_rules=CASE_SCOPE_RULES)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from django.db.models import QuerySet

if TYPE_CHECKING:
    from accounts.models import User

# Type alias for a scope filter function.
# Takes (queryset, user) and returns a filtered queryset.
ScopeFilter = Callable[[QuerySet, "User"], QuerySet]

# Type alias for a single scope rule: (permission_codename, filter_fn).
# Permission codename should include the app label (e.g. "cases.can_scope_all_cases").
ScopeRule = tuple[str, ScopeFilter]

# Legacy type alias — kept for backward compatibility during migration.
ScopeConfig = dict[str, ScopeFilter]


def get_user_role_name(user: User) -> str | None:
    """
    Return the lowercased role name for a user, or ``None`` if unassigned.

    This is an **informational** helper — used for JWT tokens, API
    responses, and logging.  Service-layer access control should use
    ``apply_permission_scope`` or ``user.has_perm()``, never role names.

    Args:
        user: Authenticated User instance.

    Returns:
        Lowercased role name string, or ``None``.
    """
    if user.is_superuser:
        return "system_admin"
    role = getattr(user, "role", None)
    if role is None:
        return None
    return role.name.lower().replace(" ", "_")


def apply_permission_scope(
    queryset: QuerySet,
    user: User,
    *,
    scope_rules: list[ScopeRule],
    default: str = "none",
) -> QuerySet:
    """
    Apply the first matching permission-based scope rule.

    Rules are checked **in order** — first permission match wins.
    Order rules from broadest (unrestricted) to narrowest (most restricted)
    so that users with wider access hit their rule first.

    Args:
        queryset:     Base (unfiltered) queryset.
        user:         The authenticated user.
        scope_rules:  Ordered list of ``(perm_codename, filter_fn)`` tuples.
                      The ``perm_codename`` must include the app label
                      (e.g. ``"cases.can_scope_all_cases"``).
        default:      What to do when no matching permission is found.
                      ``"none"`` (default) → empty queryset.
                      ``"all"`` → return unfiltered.

    Returns:
        The (possibly filtered) queryset.

    Example::

        qs = apply_permission_scope(
            Case.objects.all(),
            request.user,
            scope_rules=[
                ("cases.can_scope_all_cases",
                 lambda qs, u: qs),
                ("cases.can_scope_assigned_cases",
                 lambda qs, u: qs.filter(assigned_detective=u)),
            ],
            default="none",
        )
    """
    for perm, filter_fn in scope_rules:
        if user.has_perm(perm):
            return filter_fn(queryset, user)

    if default == "none":
        return queryset.none()
    return queryset


def require_permission(user: User, *perms: str, message: str = "") -> None:
    """
    Guard that raises ``PermissionDenied`` if the user lacks **all** of
    the given permissions (OR-logic: having any one is sufficient).

    Args:
        user:    Authenticated user.
        *perms:  One or more full permission strings (``app.codename``).
        message: Optional custom error message.

    Raises:
        core.domain.exceptions.PermissionDenied: If the user has none
            of the listed permissions.

    Example::

        require_permission(user, "cases.can_create_crime_scene")
    """
    from core.domain.exceptions import PermissionDenied as DomainPermissionDenied

    for perm in perms:
        if user.has_perm(perm):
            return
    raise DomainPermissionDenied(
        message or f"Missing required permission: {', '.join(perms)}."
    )


# ── Legacy aliases (deprecated — migrate to permission-based) ───────


def apply_role_filter(
    queryset: QuerySet,
    user: User,
    *,
    scope_config: ScopeConfig,
    default: str = "all",
) -> QuerySet:
    """
    .. deprecated::
        Use ``apply_permission_scope`` with permission-keyed scope rules
        instead of role-name-keyed scope configs.

    Apply role-based filtering to a queryset using the provided config.
    Kept for backward compatibility during migration.
    """
    role_name = get_user_role_name(user)

    if role_name and role_name in scope_config:
        return scope_config[role_name](queryset, user)

    if default == "none":
        return queryset.none()
    return queryset


def require_role(user: User, *allowed_roles: str) -> None:
    """
    .. deprecated::
        Use ``require_permission`` with permission codenames instead.

    Guard that raises ``PermissionDenied`` if the user's role is not
    among ``allowed_roles``.
    """
    from core.domain.exceptions import PermissionDenied as DomainPermissionDenied

    role_name = get_user_role_name(user)
    if role_name not in allowed_roles:
        raise DomainPermissionDenied(
            f"Role '{role_name}' is not permitted for this operation. "
            f"Required: {', '.join(allowed_roles)}."
        )
