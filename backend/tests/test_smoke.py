"""
Core app tests — domain utilities and exception handling (5 tests).

Covers:
  1. Domain exception hierarchy (Conflict, NotFound, PermissionDenied inherit DomainError)
  2. DomainError carries message
  3. InvalidTransition structured message
  4. get_user_role_name returns 'system_admin' for superusers
  5. apply_role_filter unknown role with default='all' returns unfiltered qs
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class TestCoreDomain:
    """Unit tests for core.domain utilities."""

    # 1. Exception hierarchy
    def test_exception_hierarchy(self):
        """Conflict, NotFound, PermissionDenied all inherit from DomainError."""
        from core.domain.exceptions import (
            Conflict,
            DomainError,
            InvalidTransition,
            NotFound,
            PermissionDenied,
        )
        assert issubclass(InvalidTransition, Conflict)
        assert issubclass(Conflict, DomainError)
        assert issubclass(PermissionDenied, DomainError)
        assert issubclass(NotFound, DomainError)

    # 2. DomainError message
    def test_domain_error_message(self):
        """DomainError carries the provided message."""
        from core.domain.exceptions import DomainError
        err = DomainError("test message")
        assert str(err) == "test message"
        assert err.message == "test message"

    # 3. InvalidTransition structured
    def test_invalid_transition_structured(self):
        """InvalidTransition includes current/target/reason in message."""
        from core.domain.exceptions import InvalidTransition
        err = InvalidTransition(current="pending", target="closed", reason="Not approved yet")
        assert "pending" in str(err)
        assert "closed" in str(err)
        assert err.current == "pending"
        assert err.target == "closed"

    # 4. get_user_role_name for superuser
    def test_get_user_role_name_superuser(self):
        """Superusers are mapped to 'system_admin'."""
        from core.domain.access import get_user_role_name
        user = MagicMock()
        user.is_superuser = True
        assert get_user_role_name(user) == "system_admin"

    # 5. apply_role_filter unknown role default='all'
    def test_apply_role_filter_unknown_role_default_all(self):
        """Unknown role with default='all' returns unfiltered queryset."""
        from core.domain.access import apply_role_filter
        user = MagicMock()
        user.is_superuser = False
        user.role = MagicMock()
        user.role.name = "Unknown Role"
        qs = MagicMock()
        result = apply_role_filter(qs, user, scope_config={}, default="all")
        assert result is qs
