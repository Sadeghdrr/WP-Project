"""
Integration tests — 1.1 Successful Registration Flow.

Requirement reference: md-files/project-doc.md §4.1
    "First, every user creates an account in the system with a 'base user'
    role by setting at least a username, password, email, phone number,
    full name, and national ID."

Endpoint under test:  POST /api/accounts/auth/register/
                      (named URL: accounts:register)
Expected status:      201 Created
Response serializer:  UserDetailSerializer (see accounts/serializers.py)

Engineering constraints satisfied:
  * Uses django.test.TestCase (NOT APITestCase).
  * Uses rest_framework.test.APIClient for real HTTP-layer calls.
  * No direct service-layer mutations (DB state read-back only).
  * Deterministic: unique field values are built per test to prevent
    cross-test bleed.
  * No external services or factories.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _registration_payload(**overrides) -> dict:
    """
    Build a valid registration payload.

    All uniqueness-constrained fields are set to values that are
    specific to this helper's caller so tests don't collide.
    Override any field with keyword arguments.

    Required fields (per project-doc §4.1 and RegisterRequestSerializer):
        username, password, password_confirm, email, phone_number,
        first_name, last_name, national_id
    """
    base = {
        "username": "test_reg_user",
        "password": "Str0ng!Pass99",
        "password_confirm": "Str0ng!Pass99",
        "email": "test_reg_user@example.com",
        "phone_number": "09121234599",
        "first_name": "Test",
        "last_name": "Registrant",
        # national_id: exactly 10 digits (project-doc §4.1 + serializer validation)
        "national_id": "9876543210",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestAuthRegistrationFlow(TestCase):
    """
    Integration tests for the user registration endpoint.

    Covers requirement: project-doc §4.1 — Registration and Login.
        "Every user creates an account … with a 'base user' role."
    """

    @classmethod
    def setUpTestData(cls):
        """
        Seed the 'Base User' role once for the entire test class.

        The service layer (UserRegistrationService.register_user) also
        creates this role on-demand, but seeding it here makes the test
        independent of that implicit side-effect and faster (one DB write
        shared across all methods in this class).

        Reference: accounts/services.py — step 3 of register_user:
            "Look up the 'Base User' role; create if missing."
        """
        Role.objects.get_or_create(
            name="Base User",
            defaults={
                "hierarchy_level": 0,
                "description": "Default role for newly registered users.",
            },
        )

    def setUp(self):
        # Fresh unauthenticated client for every test method.
        self.client = APIClient()
        # Named URL (app_name = "accounts", name = "register") — see accounts/urls.py
        self.register_url = reverse("accounts:register")

    # -------------------------------------------------------------------
    # 1.1  Successful registration
    # -------------------------------------------------------------------

    def test_register_returns_201(self):
        """
        POST to the registration endpoint with valid data returns HTTP 201.

        project-doc §4.1: "Every user creates an account … with a 'base user' role."
        accounts_api_report.md §1: POST /auth/register/ → 201 Created (AllowAny).
        """
        payload = _registration_payload()
        response = self.client.post(self.register_url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Expected 201 Created, got {response.status_code}. Body: {response.data}",
        )

    def test_register_response_contains_expected_keys(self):
        """
        The 201 response body must contain the fields defined by
        UserDetailSerializer (accounts/serializers.py):
            id, username, email, national_id, phone_number,
            first_name, last_name, is_active, date_joined,
            role, role_detail, permissions.

        Reference: accounts_api_report.md §4 (Me endpoint example shows
        the same serializer shape; RegisterView reuses UserDetailSerializer).
        """
        payload = _registration_payload(
            username="reg_keys_user",
            email="reg_keys_user@example.com",
            phone_number="09130000001",
            national_id="1111111111",
        )
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.data
        expected_keys = {
            "id",
            "username",
            "email",
            "national_id",
            "phone_number",
            "first_name",
            "last_name",
            "is_active",
            "date_joined",
            "role",
            "role_detail",
            "permissions",
        }
        missing = expected_keys - set(data.keys())
        self.assertFalse(
            missing,
            msg=f"Response is missing expected keys: {missing}. Got: {set(data.keys())}",
        )

    def test_register_password_not_in_response(self):
        """
        The raw password MUST NOT appear in the registration response.

        Security requirement implied by project-doc §4.1 and enforced
        in RegisterRequestSerializer (password field is write_only=True).
        """
        payload = _registration_payload(
            username="reg_nopw_user",
            email="reg_nopw_user@example.com",
            phone_number="09130000002",
            national_id="2222222222",
        )
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertNotIn(
            "password",
            response.data,
            msg="'password' field must NOT be returned in the registration response.",
        )
        self.assertNotIn(
            "password_confirm",
            response.data,
            msg="'password_confirm' field must NOT be returned in the registration response.",
        )

    def test_register_creates_user_in_database(self):
        """
        After a successful registration the user must exist in the database
        with the exact field values that were submitted.

        project-doc §4.1: username, email, phone_number, first_name,
        last_name, national_id are all required at registration.
        """
        raw_password = "Str0ng!Pass99"
        payload = _registration_payload(
            username="reg_db_user",
            email="reg_db_user@example.com",
            phone_number="09130000003",
            national_id="3333333333",
            password=raw_password,
            password_confirm=raw_password,
        )
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # DB read-back
        user = User.objects.get(username="reg_db_user")
        self.assertEqual(user.email, "reg_db_user@example.com")
        self.assertEqual(user.phone_number, "09130000003")
        self.assertEqual(user.national_id, "3333333333")
        self.assertEqual(user.first_name, "Test")
        self.assertEqual(user.last_name, "Registrant")

    def test_register_password_is_hashed(self):
        """
        The stored password must be hashed, not stored as plaintext.

        Verified via:
          1. user.password != raw_password  (not plaintext)
          2. user.check_password(raw_password) is True  (hash is correct)

        Django's AbstractUser.create_user() handles hashing automatically;
        UserRegistrationService.register_user calls create_user (services.py).
        """
        raw_password = "Str0ng!Pass99"
        payload = _registration_payload(
            username="reg_hash_user",
            email="reg_hash_user@example.com",
            phone_number="09130000004",
            national_id="4444444444",
            password=raw_password,
            password_confirm=raw_password,
        )
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username="reg_hash_user")

        # Password must NOT be stored as plaintext
        self.assertNotEqual(
            user.password,
            raw_password,
            msg="Password must be stored as a hash, not plaintext.",
        )
        # Hash must be correct — i.e. Django can verify it
        self.assertTrue(
            user.check_password(raw_password),
            msg="user.check_password(raw_password) must return True after registration.",
        )

    def test_register_user_is_active_by_default(self):
        """
        Newly registered users must be active (is_active=True) by default.

        Django's create_user() sets is_active=True.  The project-doc does
        not require email confirmation on initial registration.
        """
        payload = _registration_payload(
            username="reg_active_user",
            email="reg_active_user@example.com",
            phone_number="09130000005",
            national_id="5555555555",
        )
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username="reg_active_user")
        self.assertTrue(
            user.is_active,
            msg="New users must have is_active=True after registration.",
        )
        # Also verify via response body
        self.assertTrue(
            response.data.get("is_active"),
            msg="Response body must reflect is_active=True.",
        )

    def test_register_assigns_base_user_role(self):
        """
        After successful registration the user MUST be assigned the
        "Base User" role — not null, not any other role.

        project-doc §4.1:
            "Every user creates an account in the system with a 'base user' role."

        accounts_api_report.md §1:
            POST /auth/register/ → "defaults to 'Base User' role"

        accounts/services.py — UserRegistrationService.register_user step 3:
            "Look up the Role where name='Base User'. If it does not exist,
            create it with hierarchy_level=0."
        """
        payload = _registration_payload(
            username="reg_role_user",
            email="reg_role_user@example.com",
            phone_number="09130000006",
            national_id="6666666666",
        )
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # DB assertion — role must not be null
        user = User.objects.select_related("role").get(username="reg_role_user")
        self.assertIsNotNone(
            user.role,
            msg="Newly registered user must have a role assigned (expected 'Base User').",
        )
        self.assertEqual(
            user.role.name,
            "Base User",
            msg=f"Expected role 'Base User', got '{user.role.name}'.",
        )

        # Response body assertion — role_detail must reflect "Base User"
        role_detail = response.data.get("role_detail")
        self.assertIsNotNone(role_detail, msg="Response must contain 'role_detail'.")
        self.assertEqual(
            role_detail.get("name"),
            "Base User",
            msg=f"Response role_detail.name expected 'Base User', got '{role_detail.get('name')}'.",
        )

    def test_register_response_matches_database_state(self):
        """
        The id returned in the response must correspond to the actual
        User row — i.e. response and DB are consistent.

        This guards against serializer misconfiguration that could return
        stale or wrong data after creation.
        """
        payload = _registration_payload(
            username="reg_consistency_user",
            email="reg_consistency_user@example.com",
            phone_number="09130000007",
            national_id="7777777777",
        )
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        resp_id = response.data.get("id")
        self.assertIsNotNone(resp_id, msg="Response must include the new user's 'id'.")

        # The user with that DB id must have the same username
        user = User.objects.get(pk=resp_id)
        self.assertEqual(user.username, "reg_consistency_user")
        self.assertEqual(user.email, "reg_consistency_user@example.com")
