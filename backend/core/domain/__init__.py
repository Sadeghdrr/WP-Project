"""
core.domain — Shared domain utilities for cross-app service layers.

Modules
-------
exceptions     Domain-specific exceptions that map cleanly to HTTP responses.
notifications  Synchronous notification creation helper.
transactions   Helpers for ``transaction.atomic`` + ``select_for_update``.
access         Role-scoped queryset selectors (placeholder hooks).

Usage from any app::

    from core.domain.exceptions import DomainError, InvalidTransition
    from core.domain.notifications import NotificationService
    from core.domain.transactions import atomic_transition
    from core.domain.access import role_scoped_queryset
"""
