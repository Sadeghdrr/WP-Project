"""
core.domain.access — Role-scoped queryset selectors (shared patterns).

This module provides **placeholder hooks** and shared utilities that
each app's service layer will call to obtain querysets filtered by the
requesting user's role.

╔══════════════════════════════════════════════════════════════════╗
║  IMPORTANT — Per-app scoping logic does NOT live here.         ║
║  Each app's ``services.py`` owns its own ``get_filtered_qs()`` ║
║  implementation.  This module provides:                        ║
║    1) A registry pattern for role→queryset filters.            ║
║    2) Helper functions that apps can call.                      ║
║    3) Documented hooks explaining how to plug in.              ║
╚══════════════════════════════════════════════════════════════════╝

Architecture overview
---------------------
Role-based data access follows a **selector** pattern:

    ┌─────────┐      ┌────────────────┐      ┌──────────────────┐
    │  View   │─────▶│  App service   │─────▶│ core.domain      │
    │ (thin)  │      │ (owns logic)   │      │   .access        │
    └─────────┘      └────────────────┘      │ (shared helpers) │
                                             └──────────────────┘

Usage in an app's service layer::

    from core.domain.access import apply_role_filter

    class CaseQueryService:
        def get_filtered_queryset(self, user):
            qs = Case.objects.all()
            return apply_role_filter(qs, user, scope_config=CASE_SCOPE_CONFIG)

Where ``CASE_SCOPE_CONFIG`` is defined inside the cases app::

    CASE_SCOPE_CONFIG = {
        "detective": lambda qs, user: qs.filter(assigned_detective=user),
        "sergeant":  lambda qs, user: qs.filter(assigned_sergeant=user),
        # ... other roles ...
    }
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from django.db.models import QuerySet

if TYPE_CHECKING:
    from accounts.models import User

# Type alias for a scope filter function.
# Takes (queryset, user) and returns a filtered queryset.
ScopeFilter = Callable[[QuerySet, "User"], QuerySet]

# Type alias for a complete scope configuration dict.
# Maps role name (lowercased) → ScopeFilter.
ScopeConfig = dict[str, ScopeFilter]


def get_user_role_name(user: User) -> str | None:
    """
    Return the lowercased role name for a user, or ``None`` if unassigned.

    This is the canonical way to obtain the user's role string for
    scope-config lookups — avoids repeating the attribute access and
    null-check everywhere.

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


def apply_role_filter(
    queryset: QuerySet,
    user: User,
    *,
    scope_config: ScopeConfig,
    default: str = "all",
) -> QuerySet:
    """
    Apply role-based filtering to a queryset using the provided config.

    Lookup order:
        1. If the user's role name matches a key in ``scope_config``,
           the corresponding filter is applied.
        2. Otherwise, the ``default`` strategy is used:
           - ``"all"`` → return the queryset unfiltered.
           - ``"none"`` → return an empty queryset.

    Args:
        queryset:     Base (unfiltered) queryset.
        user:         The authenticated user.
        scope_config: Dict mapping role names to filter callables.
        default:      What to do when no matching role is found.
                      ``"all"`` (default) or ``"none"``.

    Returns:
        The (possibly filtered) queryset.

    Example::

        qs = apply_role_filter(
            Case.objects.all(),
            request.user,
            scope_config={
                "detective": lambda qs, u: qs.filter(assigned_detective=u),
                "sergeant":  lambda qs, u: qs.filter(assigned_sergeant=u),
                "captain":   lambda qs, u: qs.all(),
                "police_chief": lambda qs, u: qs.all(),
                "system_admin": lambda qs, u: qs.all(),
            },
            default="none",
        )
    """
    role_name = get_user_role_name(user)

    if role_name and role_name in scope_config:
        return scope_config[role_name](queryset, user)

    if default == "none":
        return queryset.none()
    return queryset


def require_role(user: User, *allowed_roles: str) -> None:
    """
    Guard that raises ``PermissionDenied`` if the user's role is not
    among ``allowed_roles``.

    Role names should be **lowercase with underscores** (e.g.
    ``"detective"``, ``"police_chief"``).

    Args:
        user:          Authenticated user.
        *allowed_roles: One or more role name strings.

    Raises:
        core.domain.exceptions.PermissionDenied: If the user's role
            is not in the allowed set.

    Example::

        require_role(user, "detective", "sergeant", "captain")
    """
    from core.domain.exceptions import PermissionDenied as DomainPermissionDenied

    role_name = get_user_role_name(user)
    if role_name not in allowed_roles:
        raise DomainPermissionDenied(
            f"Role '{role_name}' is not permitted for this operation. "
            f"Required: {', '.join(allowed_roles)}."
        )
