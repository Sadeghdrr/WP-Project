"""
Smoke tests — verify that Django boots, URL routing resolves, and
the core domain modules are importable.

These tests require a DB (they use ``@pytest.mark.django_db`` where
needed) but do NOT require real data — they just prove the plumbing
works.
"""

from __future__ import annotations

import pytest
from django.urls import resolve, reverse


# ════════════════════════════════════════════════════════════════════
#  URL Routing Smoke Tests
# ════════════════════════════════════════════════════════════════════

class TestURLRouting:
    """Ensure all top-level app URL namespaces resolve without 404."""

    EXPECTED_URLS = [
        # (url_name, expected_path_prefix)
        ("suspect-list",       "/api/suspects/"),
        ("bounty-tip-list",    "/api/bounty-tips/"),
        ("core:dashboard-stats", "/api/core/dashboard/"),
        ("core:global-search",   "/api/core/search/"),
        ("core:system-constants", "/api/core/constants/"),
    ]

    @pytest.mark.parametrize("url_name,expected_prefix", EXPECTED_URLS)
    def test_url_resolves(self, url_name: str, expected_prefix: str):
        """Named URL reverses to the expected path prefix."""
        url = reverse(url_name)
        assert url.startswith(expected_prefix), (
            f"{url_name} resolved to {url}, expected prefix {expected_prefix}"
        )

    @pytest.mark.parametrize("url_name,expected_prefix", EXPECTED_URLS)
    def test_url_resolve_matches_view(self, url_name: str, expected_prefix: str):
        """Path resolves to a view function (not a 404)."""
        match = resolve(expected_prefix)
        assert match.func is not None


# ════════════════════════════════════════════════════════════════════
#  Core Domain Module Import Tests
# ════════════════════════════════════════════════════════════════════

class TestCoreDomainImports:
    """Verify that shared domain utility modules are importable."""

    def test_import_exceptions(self):
        from core.domain.exceptions import (
            DomainError,
            PermissionDenied,
            NotFound,
            Conflict,
            InvalidTransition,
        )
        # Ensure they form an inheritance chain
        assert issubclass(InvalidTransition, Conflict)
        assert issubclass(Conflict, DomainError)
        assert issubclass(PermissionDenied, DomainError)
        assert issubclass(NotFound, DomainError)

    def test_import_notifications(self):
        from core.domain.notifications import NotificationService
        assert hasattr(NotificationService, "create")

    def test_import_transactions(self):
        from core.domain.transactions import (
            atomic_transition,
            run_in_atomic,
            lock_for_update,
        )
        assert callable(atomic_transition)
        assert callable(run_in_atomic)
        assert callable(lock_for_update)

    def test_import_access(self):
        from core.domain.access import (
            apply_role_filter,
            get_user_role_name,
            require_role,
        )
        assert callable(apply_role_filter)
        assert callable(get_user_role_name)
        assert callable(require_role)


# ════════════════════════════════════════════════════════════════════
#  Exception Behaviour Tests
# ════════════════════════════════════════════════════════════════════

class TestDomainExceptions:
    """Unit tests for domain exception classes."""

    def test_domain_error_message(self):
        from core.domain.exceptions import DomainError
        err = DomainError("test message")
        assert str(err) == "test message"

    def test_invalid_transition_structured(self):
        from core.domain.exceptions import InvalidTransition
        err = InvalidTransition(
            current="pending",
            target="closed",
            reason="Not approved yet",
        )
        assert "pending" in str(err)
        assert "closed" in str(err)
        assert "Not approved yet" in str(err)
        assert err.current == "pending"
        assert err.target == "closed"

    def test_invalid_transition_plain_message(self):
        from core.domain.exceptions import InvalidTransition
        err = InvalidTransition("Cannot close case.")
        assert str(err) == "Cannot close case."


# ════════════════════════════════════════════════════════════════════
#  Access Helper Unit Tests
# ════════════════════════════════════════════════════════════════════

class TestAccessHelpers:
    """Unit tests for core.domain.access helpers."""

    def test_apply_role_filter_unknown_role_default_all(self):
        """Unknown role with default='all' returns unfiltered qs."""
        from unittest.mock import MagicMock
        from core.domain.access import apply_role_filter

        user = MagicMock()
        user.is_superuser = False
        user.role = MagicMock()
        user.role.name = "Unknown Role"

        qs = MagicMock()
        result = apply_role_filter(qs, user, scope_config={}, default="all")
        assert result is qs  # returned unmodified

    def test_apply_role_filter_unknown_role_default_none(self):
        """Unknown role with default='none' returns empty qs."""
        from unittest.mock import MagicMock
        from core.domain.access import apply_role_filter

        user = MagicMock()
        user.is_superuser = False
        user.role = MagicMock()
        user.role.name = "Unknown Role"

        qs = MagicMock()
        apply_role_filter(qs, user, scope_config={}, default="none")
        qs.none.assert_called_once()

    def test_require_role_raises(self):
        """require_role raises PermissionDenied for wrong role."""
        from unittest.mock import MagicMock
        from core.domain.access import require_role
        from core.domain.exceptions import PermissionDenied

        user = MagicMock()
        user.is_superuser = False
        user.role = MagicMock()
        user.role.name = "Cadet"

        with pytest.raises(PermissionDenied):
            require_role(user, "detective", "sergeant")

    def test_get_user_role_name_superuser(self):
        """Superusers are mapped to 'system_admin'."""
        from unittest.mock import MagicMock
        from core.domain.access import get_user_role_name

        user = MagicMock()
        user.is_superuser = True
        assert get_user_role_name(user) == "system_admin"
