"""
Integration tests — 1.2 Login with multiple identifiers (multi-field login).

Requirement reference: md-files/project-doc.md §4.1
    "Logging into the system will be done using the password and one of the
    following: username, national ID, phone number, or email."

Endpoint under test:  POST /api/accounts/auth/login/
                      (named URL: accounts:login)
Request payload:      {"identifier": "<username|email|phone|national_id>",
                       "password": "<password>"}
Success response:     HTTP 200, body contains {"access": "...", "refresh": "...",
                      "user": {...}} (02-accounts_api_report.md §3)
Failure response:     HTTP 400 — serializer raises ValidationError when
                      credentials are invalid (CustomTokenObtainPairSerializer.validate)
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()

# ── Constants ────────────────────────────────────────────────────────────────
_PASSWORD = "Str0ng!Pass99"

# All four identifier fields populated so every login variant can be tested.
_USER_FIELDS = {
    "username":     "login_test_user",
    "email":        "login_test_user@example.com",
    "phone_number": "09130000099",
    "national_id":  "8800000099",
    "first_name":   "Login",
    "last_name":    "Tester",
}


class TestAuthLoginMultiIdentifier(TestCase):
    """
    Integration tests for the multi-field login endpoint.

    Covers requirement: project-doc §4.1 — Registration and Login.
        "Logging into the system will be done using the password and one of
        the following: username, national ID, phone number, or email.
        Naturally, all these fields must be unique."

    Token shape verified against: 02-accounts_api_report.md §3 (Multi-Field Login)
        Response payload: {"access": "...", "refresh": "...", "user": {...}}
    """

    @classmethod
    def setUpTestData(cls):
        """
        Create one user shared across all test methods in this class.

        All four unique identifier fields are explicitly set so that
        each login variant can resolve the user independently.
        setUpTestData wraps the creation in a transaction that is rolled
        back after the class, keeping the suite side-effect-free.
        """
        cls.user = User.objects.create_user(
            password=_PASSWORD,
            **_USER_FIELDS,
        )

    def setUp(self):
        # Fresh unauthenticated client for every test — no shared auth state.
        self.client = APIClient()
        # Named URL: app_name="accounts", name="login" (accounts/urls.py)
        self.login_url = reverse("accounts:login")

    # ── Helper ───────────────────────────────────────────────────────────────

    def _post_login(self, identifier: str, password: str):
        """
        POST to the login endpoint and return the Response.

        Request schema (02-accounts_api_report.md §3, LoginRequestSerializer):
            {"identifier": "<username|email|phone|national_id>",
             "password": "<password>"}
        """
        return self.client.post(
            self.login_url,
            {"identifier": identifier, "password": password},
            format="json",
        )

    # ── Success tests — one per identifier type ───────────────────────────────

    def test_login_with_username(self):
        """
        Login via username succeeds with HTTP 200 and JWT tokens.

        project-doc §4.1: "…using the password and one of the following:
        username, national ID, phone number, or email."
        """
        resp = self._post_login(_USER_FIELDS["username"], _PASSWORD)

        self.assertEqual(
            resp.status_code,
            status.HTTP_200_OK,
            msg=f"Expected 200 logging in with username. Body: {resp.data}",
        )
        self._assert_token_shape(resp)
        self._assert_user_info(resp)

    def test_login_with_email(self):
        """
        Login via email succeeds with HTTP 200 and JWT tokens.

        project-doc §4.1: identifier may be the email address.
        Resolved via MultiFieldAuthBackend Q(email=identifier).
        """
        resp = self._post_login(_USER_FIELDS["email"], _PASSWORD)

        self.assertEqual(
            resp.status_code,
            status.HTTP_200_OK,
            msg=f"Expected 200 logging in with email. Body: {resp.data}",
        )
        self._assert_token_shape(resp)
        self._assert_user_info(resp)

    def test_login_with_phone_number(self):
        """
        Login via phone_number succeeds with HTTP 200 and JWT tokens.

        project-doc §4.1: identifier may be the phone number.
        Resolved via MultiFieldAuthBackend Q(phone_number=identifier).
        """
        resp = self._post_login(_USER_FIELDS["phone_number"], _PASSWORD)

        self.assertEqual(
            resp.status_code,
            status.HTTP_200_OK,
            msg=f"Expected 200 logging in with phone_number. Body: {resp.data}",
        )
        self._assert_token_shape(resp)
        self._assert_user_info(resp)

    def test_login_with_national_id(self):
        """
        Login via national_id succeeds with HTTP 200 and JWT tokens.

        project-doc §4.1: identifier may be the national ID.
        Resolved via MultiFieldAuthBackend Q(national_id=identifier).
        """
        resp = self._post_login(_USER_FIELDS["national_id"], _PASSWORD)

        self.assertEqual(
            resp.status_code,
            status.HTTP_200_OK,
            msg=f"Expected 200 logging in with national_id. Body: {resp.data}",
        )
        self._assert_token_shape(resp)
        self._assert_user_info(resp)

    # ── All 4 identifiers in a single sweep ──────────────────────────────────

    def test_all_identifier_types_succeed(self):
        """
        Each identifier type must independently authenticate the same user.

        This is a sweep test complementing the four individual tests above;
        it makes the parametrized intent explicit in a single test body.

        project-doc §4.1: all four identifier types must work.
        """
        identifiers = {
            "username":     _USER_FIELDS["username"],
            "email":        _USER_FIELDS["email"],
            "phone_number": _USER_FIELDS["phone_number"],
            "national_id":  _USER_FIELDS["national_id"],
        }

        for field_name, value in identifiers.items():
            with self.subTest(identifier_field=field_name, value=value):
                resp = self._post_login(value, _PASSWORD)
                self.assertEqual(
                    resp.status_code,
                    status.HTTP_200_OK,
                    msg=(
                        f"Login with {field_name}={value!r} expected HTTP 200, "
                        f"got {resp.status_code}. Body: {resp.data}"
                    ),
                )
                self._assert_token_shape(resp)

    # ── Negative tests ────────────────────────────────────────────────────────

    def test_wrong_password_rejected(self):
        """
        Submitting the correct identifier but wrong password is rejected.

        The serializer (CustomTokenObtainPairSerializer.validate) raises
        ValidationError which DRF converts to HTTP 400.
        02-accounts_api_report.md @extend_schema: 400 for invalid credentials.
        """
        resp = self._post_login(_USER_FIELDS["username"], "WrongPassword!")

        self.assertEqual(
            resp.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Expected 400 for wrong password. Body: {resp.data}",
        )
        # Error detail must be present in body
        self.assertIn(
            "detail",
            resp.data,
            msg="Response body must contain a 'detail' error key.",
        )

    def test_unknown_identifier_rejected(self):
        """
        An identifier that matches no user in any identifier field is rejected.

        MultiFieldAuthBackend returns None → serializer raises ValidationError
        → HTTP 400.  project-doc §4.1 implies all four fields are unique;
        a non-existent value matches none of them.
        """
        resp = self._post_login("nobody_at_all_xyz", _PASSWORD)

        self.assertEqual(
            resp.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Expected 400 for unknown identifier. Body: {resp.data}",
        )
        self.assertIn("detail", resp.data)

    def test_inactive_user_cannot_login(self):
        """
        A deactivated user (is_active=False) must not receive tokens.

        Django's ModelBackend.user_can_authenticate() returns False for
        inactive users; MultiFieldAuthBackend inherits this check.
        02-accounts_api_report.md §3: "verifies is_active".
        """
        # Create a second, inactive user so we don't mutate setUpTestData state.
        inactive = User.objects.create_user(
            username="inactive_login_user",
            password=_PASSWORD,
            email="inactive_login@example.com",
            phone_number="09130000098",
            national_id="8800000098",
            first_name="Inactive",
            last_name="User",
            is_active=False,
        )
        resp = self._post_login(inactive.username, _PASSWORD)

        self.assertEqual(
            resp.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Expected 400 for inactive user login. Body: {resp.data}",
        )

    def test_missing_password_field_rejected(self):
        """
        Omitting the password field entirely must fail with HTTP 400.

        The LoginRequestSerializer marks 'password' as required.
        """
        resp = self.client.post(
            self.login_url,
            {"identifier": _USER_FIELDS["username"]},
            format="json",
        )
        self.assertEqual(
            resp.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Expected 400 when password field is missing. Body: {resp.data}",
        )

    def test_missing_identifier_field_rejected(self):
        """
        Omitting the identifier field entirely must fail with HTTP 400.

        The LoginRequestSerializer marks 'identifier' as required.
        """
        resp = self.client.post(
            self.login_url,
            {"password": _PASSWORD},
            format="json",
        )
        self.assertEqual(
            resp.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Expected 400 when identifier field is missing. Body: {resp.data}",
        )

    # ── Shared assertion helpers ──────────────────────────────────────────────

    def _assert_token_shape(self, resp) -> None:
        """
        Assert the response body contains the expected JWT token keys.

        02-accounts_api_report.md §3 — response payload:
            {"access": "...", "refresh": "...", "user": {...}}
        """
        self.assertIn(
            "access",
            resp.data,
            msg="Login response must include 'access' JWT token.",
        )
        self.assertIn(
            "refresh",
            resp.data,
            msg="Login response must include 'refresh' JWT token.",
        )
        # Tokens must be non-empty strings
        self.assertTrue(
            isinstance(resp.data["access"], str) and resp.data["access"],
            msg="'access' token must be a non-empty string.",
        )
        self.assertTrue(
            isinstance(resp.data["refresh"], str) and resp.data["refresh"],
            msg="'refresh' token must be a non-empty string.",
        )

    def _assert_user_info(self, resp) -> None:
        """
        Assert the nested 'user' object matches the test user.

        02-accounts_api_report.md §3:
            Response includes "user" serialized via UserDetailSerializer.
        """
        self.assertIn("user", resp.data, msg="Login response must include 'user' object.")
        user_data = resp.data["user"]
        self.assertEqual(
            user_data.get("username"),
            _USER_FIELDS["username"],
            msg="Response user.username must match the authenticated user.",
        )
        self.assertEqual(
            user_data.get("email"),
            _USER_FIELDS["email"],
            msg="Response user.email must match the authenticated user.",
        )
        # Password must not be leaked in the user object
        self.assertNotIn(
            "password",
            user_data,
            msg="Response user object must not contain the password field.",
        )
