"""
Integration tests — 1.3 Current profile (Me) endpoint.

Requirement reference: md-files/project-doc.md §4.1
    "Every user creates an account in the system with a 'base user' role …"

Endpoint under test:  GET  /api/accounts/me/   (named URL: accounts:me)
                      PATCH /api/accounts/me/  (named URL: accounts:me)
Access:               Authenticated only (IsAuthenticated permission class)
Response serializer:  UserDetailSerializer — returns:
                        id, username, email, national_id, phone_number,
                        first_name, last_name, is_active, date_joined,
                        role, role_detail, permissions
                      (accounts/serializers.py — UserDetailSerializer.Meta.fields)

Auth scheme:          JWT Bearer  (settings.py → DEFAULT_AUTHENTICATION_CLASSES
                       = JWTAuthentication; accounts_api_report.md §5)
Login endpoint:       POST /api/accounts/auth/login/
Login payload:        {"identifier": "...", "password": "..."}
Login response keys:  {"access": "...", "refresh": "...", "user": {...}}
                      (accounts_api_report.md §3; accounts/views.py LoginView)

Engineering constraints:
  * django.test.TestCase + rest_framework.test.APIClient.
  * Tests hit real endpoints via views/urls — no direct service calls.
  * No shared auth state between tests; each test acquires its own token.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role

User = get_user_model()

# ── Test user constants ───────────────────────────────────────────────────────
_PASSWORD = "Str0ng!Pass77"
_USER = {
    "username":     "me_test_user",
    "email":        "me_test_user@example.com",
    "phone_number": "09130000077",
    "national_id":  "7700000077",
    "first_name":   "Me",
    "last_name":    "Tester",
}


class TestMeEndpoint(TestCase):
    """
    Integration tests for GET /api/accounts/me/ and PATCH /api/accounts/me/.

    All assertions map to documented requirements:
      - project-doc §4.1   : user fields registered at sign-up
      - accounts_api_report §1: /me/ requires authentication (IsAuthenticated)
      - accounts_api_report §4: response shape defined by UserDetailSerializer
      - accounts_api_report §3: JWT Bearer scheme; access/refresh token keys
    """

    @classmethod
    def setUpTestData(cls):
        """
        Seed the 'Base User' role and create the test user once for the class.

        The role is seeded so that UserRegistrationService.register_user
        (and any test path that exercises it) finds the role; direct
        create_user() calls don't run that service, so the role must exist
        for the FK lookup in assertions.
        """
        cls.base_role, _ = Role.objects.get_or_create(
            name="Base User",
            defaults={"hierarchy_level": 0, "description": "Default role"},
        )
        cls.user = User.objects.create_user(password=_PASSWORD, **_USER)
        # Assign base role so role_detail in response is populated
        cls.user.role = cls.base_role
        cls.user.save(update_fields=["role"])

    def setUp(self):
        # Fresh unauthenticated client for every test — no shared auth state.
        self.client = APIClient()
        self.me_url    = reverse("accounts:me")
        self.login_url = reverse("accounts:login")

    # ── Helper ────────────────────────────────────────────────────────────────

    def _login_and_get_token(self, identifier: str = _USER["username"],
                             password: str = _PASSWORD) -> str:
        """
        POST to the login endpoint and return the JWT access token string.

        Login schema (accounts_api_report.md §3):
            Request:  {"identifier": "...", "password": "..."}
            Response: {"access": "...", "refresh": "...", "user": {...}}
        """
        resp = self.client.post(
            self.login_url,
            {"identifier": identifier, "password": password},
            format="json",
        )
        self.assertEqual(
            resp.status_code,
            status.HTTP_200_OK,
            msg=f"Login during test setup failed: {resp.data}",
        )
        return resp.data["access"]

    def _authenticate(self, token: str | None = None) -> None:
        """
        Set the Authorization header on self.client.

        Auth scheme: Bearer JWT
        (settings.py DEFAULT_AUTHENTICATION_CLASSES = JWTAuthentication,
         accounts_api_report.md §5)
        """
        if token is None:
            token = self._login_and_get_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    # ── Authenticated success tests ───────────────────────────────────────────

    def test_me_authenticated_returns_200(self):
        """
        GET /me/ with a valid Bearer token must return HTTP 200.

        accounts_api_report.md §1: GET /me/ → Authenticated; 200 OK.
        """
        self._authenticate()
        resp = self.client.get(self.me_url)

        self.assertEqual(
            resp.status_code,
            status.HTTP_200_OK,
            msg=f"Expected 200 from /me/ when authenticated. Body: {resp.data}",
        )

    def test_me_response_contains_required_fields(self):
        """
        The /me/ response body must include all fields from UserDetailSerializer.

        accounts/serializers.py — UserDetailSerializer.Meta.fields:
            id, username, email, national_id, phone_number, first_name,
            last_name, is_active, date_joined, role, role_detail, permissions
        """
        self._authenticate()
        resp = self.client.get(self.me_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        expected_fields = {
            "id", "username", "email", "national_id", "phone_number",
            "first_name", "last_name", "is_active", "date_joined",
            "role", "role_detail", "permissions",
        }
        missing = expected_fields - set(resp.data.keys())
        self.assertFalse(
            missing,
            msg=f"/me/ response is missing fields: {missing}. Got: {set(resp.data.keys())}",
        )

    def test_me_returns_correct_user_identity(self):
        """
        The /me/ response must reflect the authenticated user's own data.

        project-doc §4.1: username, email, phone_number, national_id,
        first_name, last_name are all registered at sign-up and must be
        returned correctly by /me/.
        """
        self._authenticate()
        resp = self.client.get(self.me_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        data = resp.data
        self.assertEqual(data["username"],     _USER["username"])
        self.assertEqual(data["email"],        _USER["email"])
        self.assertEqual(data["phone_number"], _USER["phone_number"])
        self.assertEqual(data["national_id"],  _USER["national_id"])
        self.assertEqual(data["first_name"],   _USER["first_name"])
        self.assertEqual(data["last_name"],    _USER["last_name"])
        # DB primary key must match
        self.assertEqual(data["id"], self.user.pk)

    def test_me_does_not_leak_password(self):
        """
        The /me/ response must NOT expose any password-related field.

        project-doc §4.1 (implied security): passwords must never be
        returned in API responses.  UserDetailSerializer does not include
        a password field (write_only in RegisterRequestSerializer).
        """
        self._authenticate()
        resp = self.client.get(self.me_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        self.assertNotIn(
            "password",
            resp.data,
            msg="/me/ response must NOT contain 'password'.",
        )

    def test_me_user_is_active(self):
        """
        is_active must be True for a freshly created, non-deactivated user.

        project-doc §4.1: no forced deactivation on registration;
        UserDetailSerializer exposes is_active.
        """
        self._authenticate()
        resp = self.client.get(self.me_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        self.assertTrue(
            resp.data.get("is_active"),
            msg="/me/ response must show is_active=True for an active user.",
        )

    def test_me_role_detail_is_base_user(self):
        """
        After registration (or direct creation with role assignment) the
        user's role must be 'Base User', and role_detail must reflect that.

        project-doc §4.1:
            "Every user creates an account … with a 'base user' role."
        accounts_api_report.md §4:
            role_detail is a nested object: {id, name, description, hierarchy_level}
        """
        self._authenticate()
        resp = self.client.get(self.me_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        role_detail = resp.data.get("role_detail")
        self.assertIsNotNone(
            role_detail,
            msg="/me/ response must include a non-null 'role_detail'.",
        )
        self.assertEqual(
            role_detail.get("name"),
            "Base User",
            msg=f"Expected role_detail.name='Base User', got {role_detail.get('name')!r}.",
        )

    def test_me_permissions_is_list(self):
        """
        The 'permissions' field must be a list (possibly empty for Base User).

        accounts_api_report.md §4:
            permissions: flat list of 'app_label.codename' strings for
            frontend conditional rendering.
        accounts/models.py — User.permissions_list returns list(get_all_permissions()).
        """
        self._authenticate()
        resp = self.client.get(self.me_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        self.assertIsInstance(
            resp.data.get("permissions"),
            list,
            msg="/me/ 'permissions' field must be a list.",
        )

    # ── Unauthenticated tests ─────────────────────────────────────────────────

    def test_me_unauthenticated_returns_401(self):
        """
        GET /me/ without credentials must return HTTP 401 Unauthorized.

        accounts_api_report.md §1:
            GET /me/ — Access Level: Authenticated (IsAuthenticated)
        accounts/views.py MeView: permission_classes = [IsAuthenticated]
        """
        # Deliberately do NOT call _authenticate() — client has no credentials.
        resp = self.client.get(self.me_url)

        self.assertEqual(
            resp.status_code,
            status.HTTP_401_UNAUTHORIZED,
            msg=f"Expected 401 from /me/ when unauthenticated. Got: {resp.status_code}",
        )

    def test_me_invalid_token_returns_401(self):
        """
        Providing a malformed / expired JWT token must return 401.

        JWTAuthentication raises AuthenticationFailed for invalid tokens.
        """
        self.client.credentials(HTTP_AUTHORIZATION="Bearer this.is.not.a.valid.jwt")
        resp = self.client.get(self.me_url)

        self.assertEqual(
            resp.status_code,
            status.HTTP_401_UNAUTHORIZED,
            msg=f"Expected 401 for invalid token. Got: {resp.status_code}",
        )

    def test_me_after_credentials_cleared_returns_401(self):
        """
        After explicitly clearing credentials, /me/ must return 401 again.

        Verifies that the test client correctly resets auth state and that
        the endpoint enforces authentication every time independently.
        """
        # Step 1: authenticate and verify 200
        self._authenticate()
        resp = self.client.get(self.me_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Step 2: clear credentials — should now get 401
        self.client.credentials()
        resp = self.client.get(self.me_url)
        self.assertEqual(
            resp.status_code,
            status.HTTP_401_UNAUTHORIZED,
            msg="Expected 401 after clearing credentials.",
        )

    # ── PATCH /me/ — profile update ───────────────────────────────────────────

    def test_me_patch_updates_allowed_fields(self):
        """
        PATCH /me/ must allow the user to update their own email and name.

        accounts_api_report.md §1: PATCH /me/ → Authenticated; updates
        email, phone_number, first_name, last_name.
        accounts/serializers.py MeUpdateSerializer.Meta.fields.
        """
        # Create a dedicated user for this mutation test so setUpTestData user
        # is unaffected for other test methods.
        patch_user = User.objects.create_user(
            username="me_patch_user",
            password=_PASSWORD,
            email="patch_before@example.com",
            phone_number="09130000070",
            national_id="7700000070",
            first_name="Before",
            last_name="Patch",
        )
        patch_user.role = self.base_role
        patch_user.save(update_fields=["role"])

        token = self._login_and_get_token(identifier="me_patch_user")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        resp = self.client.patch(
            self.me_url,
            {"first_name": "After", "last_name": "Update"},
            format="json",
        )
        self.assertEqual(
            resp.status_code,
            status.HTTP_200_OK,
            msg=f"PATCH /me/ expected 200. Body: {resp.data}",
        )
        self.assertEqual(resp.data["first_name"], "After")
        self.assertEqual(resp.data["last_name"],  "Update")

    def test_me_patch_unauthenticated_returns_401(self):
        """
        PATCH /me/ without credentials must return 401.

        accounts/views.py MeView: permission_classes = [IsAuthenticated].
        """
        resp = self.client.patch(
            self.me_url,
            {"first_name": "Hacker"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
