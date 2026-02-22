"""
Root conftest.py — shared fixtures for the entire test suite.

Provides:
  - ``api_client`` fixture returning a DRF ``APIClient``.
  - ``create_user`` factory fixture for creating test users.
  - ``auth_header`` fixture for authenticated requests (JWT).
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient


@pytest.fixture()
def api_client() -> APIClient:
    """Unauthenticated DRF test client."""
    return APIClient()


@pytest.fixture()
def create_user(db):
    """
    Factory fixture that creates a user with sensible defaults.

    Usage::

        def test_something(create_user):
            user = create_user(username="alice")
            # or with all fields:
            user = create_user(
                username="bob",
                password="Str0ng!Pass",
                email="bob@example.com",
                national_id="1234567890",
                phone_number="09121234567",
            )
    """
    from accounts.models import User

    _counter = 0

    def _factory(
        *,
        username: str | None = None,
        password: str = "TestPass123!",
        email: str | None = None,
        national_id: str | None = None,
        phone_number: str | None = None,
        role=None,
        is_active: bool = True,
        **kwargs,
    ) -> User:
        nonlocal _counter
        _counter += 1
        if username is None:
            username = f"testuser{_counter}"
        if email is None:
            email = f"{username}@test.local"
        if national_id is None:
            national_id = f"{_counter:010d}"
        if phone_number is None:
            phone_number = f"0912{_counter:07d}"

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            national_id=national_id,
            phone_number=phone_number,
            is_active=is_active,
            **kwargs,
        )
        if role is not None:
            user.role = role
            user.save(update_fields=["role"])
        return user

    return _factory


@pytest.fixture()
def auth_header(create_user, api_client):
    """
    Returns a helper function that creates a user and returns an
    ``Authorization`` header dict with a valid JWT access token.

    Usage::

        def test_protected(auth_header, api_client):
            header = auth_header(username="alice")
            api_client.credentials(HTTP_AUTHORIZATION=header["Authorization"])
            resp = api_client.get("/api/core/dashboard/")
            assert resp.status_code != 401

    The returned dict looks like::

        {"Authorization": "Bearer eyJ..."}
    """
    from rest_framework_simplejwt.tokens import AccessToken

    def _make(
        *,
        username: str | None = None,
        role=None,
        **user_kwargs,
    ) -> dict[str, str]:
        user = create_user(username=username, role=role, **user_kwargs)
        token = AccessToken.for_user(user)
        return {"Authorization": f"Bearer {token}"}

    return _make
