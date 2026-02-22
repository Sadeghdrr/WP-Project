"""
Accounts app tests — registration and authentication (5 tests).

Covers:
  1. Registration success (user created, password hashed, Base User role)
  2. Registration duplicate field rejected
  3. Login success with username identifier
  4. Wrong password fails
  5. Inactive user cannot log in
"""

from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role, User

REGISTER_URL = "/api/accounts/auth/register/"
LOGIN_URL = "/api/accounts/auth/login/"


@pytest.fixture()
def base_role(db):
    """Ensure the 'Base User' role exists."""
    role, _ = Role.objects.get_or_create(
        name="Base User",
        defaults={"hierarchy_level": 0, "description": "Default role"},
    )
    return role


def _register_payload(**overrides) -> dict:
    """Return a valid registration payload, with optional overrides."""
    data = {
        "username": "newuser",
        "password": "Str0ng!Pass123",
        "password_confirm": "Str0ng!Pass123",
        "email": "newuser@example.com",
        "phone_number": "09121234567",
        "first_name": "New",
        "last_name": "User",
        "national_id": "1234567890",
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
class TestAccounts:

    # 1. Registration success
    def test_register_creates_user_with_base_role(self, api_client: APIClient, base_role):
        """POST /auth/register/ creates a user and assigns 'Base User' role."""
        resp = api_client.post(REGISTER_URL, _register_payload(), format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data

        user = User.objects.get(username="newuser")
        assert user.check_password("Str0ng!Pass123")
        assert user.role is not None
        assert user.role.name == "Base User"
        assert user.email == "newuser@example.com"
        assert user.national_id == "1234567890"
        assert user.phone_number == "09121234567"

    # 2. Registration duplicate field rejected
    def test_duplicate_username_rejected(self, api_client: APIClient, create_user, base_role):
        """Registering with a duplicate username is rejected."""
        create_user(username="existinguser")
        payload = _register_payload(username="existinguser")
        resp = api_client.post(REGISTER_URL, payload, format="json")
        assert resp.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT)

    # 3. Login success with username
    def test_login_with_username(self, api_client: APIClient, create_user):
        """Login succeeds when using username as the identifier."""
        create_user(username="loginuser", password="Str0ng!Pass123")
        resp = api_client.post(
            LOGIN_URL,
            {"identifier": "loginuser", "password": "Str0ng!Pass123"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert "access" in resp.data
        assert "refresh" in resp.data
        assert "user" in resp.data

    # 4. Wrong password fails
    def test_wrong_password_fails(self, api_client: APIClient, create_user):
        """Login with the wrong password returns 400."""
        create_user(username="wrongpw", password="CorrectPass1!")
        resp = api_client.post(
            LOGIN_URL,
            {"identifier": "wrongpw", "password": "WrongPass1!"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # 5. Inactive user cannot login
    def test_inactive_user_cannot_login(self, api_client: APIClient, create_user):
        """An inactive user cannot authenticate."""
        create_user(username="inactive", password="Str0ng!Pass123", is_active=False)
        resp = api_client.post(
            LOGIN_URL,
            {"identifier": "inactive", "password": "Str0ng!Pass123"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
