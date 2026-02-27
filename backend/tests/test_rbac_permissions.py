"""
Integration tests — 2.1 RBAC Permissions list endpoint.

Requirement reference: md-files/project-doc.md §2.2
    "Without needing to change the code, the system administrator must be
    able to add a new role, delete existing roles, or modify them."
    Permissions are the building blocks that are assigned to Roles (RBAC).

Roles/RBAC reference: md-files/00-rbac_implementation_report.md
    "Added a ManyToManyField named `permissions` to the Role model, linking
    it to Django's Permission model."

API reference: md-files/02-accounts_api_report.md §1 (Endpoint Table)
    GET /api/accounts/permissions/
        "List all available Django permissions."
        "Access Level: Authenticated (Admin in practice)"

Swagger reference: md-files/24-swagger_documentation_report.md §3.1
    PermissionListView  GET  /api/accounts/permissions/  Tag: Roles

Endpoint under test: GET /api/accounts/permissions/
                     (named URL: accounts:permission-list)

Response shape (02-accounts_api_report.md + PermissionSerializer):
    [
        {
            "id":            <int>,
            "name":          <str>,   # Human-readable label
            "codename":      <str>,   # e.g. "view_case"
            "full_codename": <str>,   # e.g. "cases.view_case"
        },
        ...
    ]

Permission class on the view: IsAuthenticated
    — Any **authenticated** user receives HTTP 200.
    — **Unauthenticated** requests receive HTTP 401 (doc-defined behaviour).
    — Frontend guards further restrict the UI to System Admins only
      ("Admin in practice").

Token scheme: Bearer <JWT access token>
    Login response: {"access": "...", "refresh": "...", "user": {...}}
    (02-accounts_api_report.md §3 Multi-Field Login Design)
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()

# ── Constants ────────────────────────────────────────────────────────────────

_ADMIN_PASSWORD = "Adm!nStr0ng99"
_NORMAL_PASSWORD = "N0rmal!Pass77"

_ADMIN_FIELDS = {
    "username":     "rbac_admin_user",
    "email":        "rbac_admin@lapd.gov",
    "phone_number": "09130000001",
    "national_id":  "1100000001",
    "first_name":   "RBAC",
    "last_name":    "Admin",
}

_NORMAL_FIELDS = {
    "username":     "rbac_normal_user",
    "email":        "rbac_normal@lapd.gov",
    "phone_number": "09130000002",
    "national_id":  "1100000002",
    "first_name":   "RBAC",
    "last_name":    "Normal",
}


class TestRBACPermissionsList(TestCase):
    """
    Integration tests for the RBAC permissions list endpoint.

    Covers requirement: project-doc §2.2 — User Levels
        "Without needing to change the code, the system administrator must be
        able to add a new role, delete existing roles, or modify them."
        (Requires knowing which permissions exist → this endpoint.)

    Covers RBAC report: 00-rbac_implementation_report.md
        Permissions are assigned to Roles via a ManyToManyField; the admin
        needs to list all available Django permissions to build the picker.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Create test users shared across all methods in this class.

        Two users are created:
          1. cls.admin_user  — Django superuser (is_superuser=True, is_staff=True).
             Superusers bypass all permission checks, making them the natural
             representative of the "System Admin" role in project-doc §2.2.
          2. cls.normal_user — Plain user with ``is_staff=False``.
             Represents any low-privilege role (e.g. Base User, Cadet).

        setUpTestData wraps creation in a transaction rolled back after the
        class finishes, keeping the test suite side-effect-free.
        """
        # --- Admin / System-Admin user ---
        cls.admin_user = User.objects.create_superuser(
            password=_ADMIN_PASSWORD,
            **_ADMIN_FIELDS,
        )

        # --- Normal user (no staff/admin flags) ---
        cls.normal_user = User.objects.create_user(
            password=_NORMAL_PASSWORD,
            **_NORMAL_FIELDS,
        )

    def setUp(self):
        """Provide a fresh, unauthenticated APIClient for every test method."""
        # Fresh client — no shared auth state between tests.
        self.client = APIClient()
        # Named URLs (app_name="accounts" in accounts/urls.py)
        self.login_url = reverse("accounts:login")
        self.permissions_url = reverse("accounts:permission-list")

    # ── Authentication helper ─────────────────────────────────────────────────

    def _get_bearer_token(self, username: str, password: str) -> str:
        """
        Authenticate via the real login endpoint and return the JWT access token.

        Uses:
            POST /api/accounts/auth/login/
            Request:  {"identifier": "<username>", "password": "<password>"}
            Response: {"access": "<jwt>", "refresh": "...", "user": {...}}

        Reference: 02-accounts_api_report.md §3 Multi-Field Login Design
            "The identifier field is polymorphic — it may contain any of the
            four unique-constrained fields."

        Token scheme: Bearer (SimpleJWT, configured in settings.SIMPLE_JWT)
        """
        response = self.client.post(
            self.login_url,
            {"identifier": username, "password": password},
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Login failed for '{username}': {response.data}",
        )
        return response.data["access"]

    def _authenticate_as(self, username: str, password: str) -> None:
        """Obtain JWT and set the Authorization header on self.client."""
        token = self._get_bearer_token(username, password)
        # Scheme: "Bearer" — per SimpleJWT default (settings.SIMPLE_JWT)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    # ── Tests ─────────────────────────────────────────────────────────────────

    def test_admin_can_list_permissions(self):
        """
        [2.1] Authorized admin user receives HTTP 200 and a non-empty list.

        Requirement: project-doc §2.2 — System Administrator must be able to
        manage roles without code changes, which requires inspecting available
        permissions.

        Asserts:
          • HTTP 200 OK.
          • Response body is a list (or paginated dict with "results" list).
          • The list is non-empty (Django always has built-in permissions).
          • Every item contains the required keys:
              "id", "name", "codename", "full_codename"
            as defined in 02-accounts_api_report.md §2 (PermissionSerializer).
          • "full_codename" follows the "app_label.codename" pattern.
        """
        self._authenticate_as(_ADMIN_FIELDS["username"], _ADMIN_PASSWORD)

        response = self.client.get(self.permissions_url, format="json")

        # ── Status ───────────────────────────────────────────────────
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # ── Response is a list (handle optional DRF pagination) ──────
        data = response.data
        if isinstance(data, dict) and "results" in data:
            # Paginated response — unwrap the results list
            items = data["results"]
        else:
            items = data

        self.assertIsInstance(items, list, "Response body must be a list of permissions.")

        # ── Non-empty ─────────────────────────────────────────────────
        # Django's migration framework registers built-in permissions for
        # every model, so the table is never empty after migrate.
        self.assertGreater(
            len(items),
            0,
            "Permissions list must be non-empty (Django has built-in permissions).",
        )

        # ── Item structure ────────────────────────────────────────────
        # PermissionSerializer fields: id, name, codename, full_codename
        # (02-accounts_api_report.md §2, accounts/serializers.py PermissionSerializer)
        required_keys = {"id", "name", "codename", "full_codename"}
        for item in items:
            missing = required_keys - item.keys()
            self.assertFalse(
                missing,
                f"Permission item missing required keys: {missing}. Item: {item}",
            )

            # id must be a positive integer (Django PK)
            self.assertIsInstance(item["id"], int)
            self.assertGreater(item["id"], 0)

            # name is the human-readable label (non-empty string)
            self.assertIsInstance(item["name"], str)
            self.assertTrue(item["name"].strip(), "Permission 'name' must not be empty.")

            # codename: e.g. "view_case" — no dots, no spaces
            self.assertIsInstance(item["codename"], str)
            self.assertNotIn(".", item["codename"], "codename must not contain dots.")

            # full_codename: must be "app_label.codename" format
            # Reference: PermissionSerializer.get_full_codename in serializers.py
            self.assertIn(
                ".",
                item["full_codename"],
                f"full_codename '{item['full_codename']}' must follow 'app_label.codename' pattern.",
            )
            app_label, _, codename_part = item["full_codename"].partition(".")
            self.assertTrue(app_label, "app_label portion of full_codename must not be empty.")
            self.assertEqual(
                codename_part,
                item["codename"],
                "full_codename's codename part must match the 'codename' field.",
            )

    def test_unauthenticated_cannot_list_permissions(self):
        """
        [2.1] Unauthenticated request receives HTTP 401 Unauthorized.

        Doc-defined behaviour: 02-accounts_api_report.md §1
            "Access Level: Authenticated (Admin in practice)"
        The view uses permission_classes = [IsAuthenticated].
        DRF returns HTTP 401 when no valid credentials are supplied,
        which is the enforced "cannot list permissions" outcome.

        Note on 403 vs 401:
            HTTP 401 = authentication credentials were not provided or are invalid.
            HTTP 403 = credentials are valid but the role is not permitted.
            Because the view only checks IsAuthenticated, unauthenticated callers
            receive 401 — this is the backend-enforced "unauthorized" case.
        """
        # No credentials set on self.client (fresh client from setUp)
        response = self.client.get(self.permissions_url, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
            "Unauthenticated request must be rejected with HTTP 401.",
        )

    def test_normal_authenticated_user_can_list_permissions(self):
        """
        [2.1] Normal authenticated user receives HTTP 200 (backend behaviour).

        The view's permission_classes = [IsAuthenticated] allows **any**
        authenticated user to call this endpoint. The doc note
        "Admin in practice" refers to a frontend guard, not a backend rule.

        This test documents the actual backend behaviour so that a future
        decision to add IsAdminUser (or a custom permission) would be
        immediately caught as a regression here and treated as a deliberate
        change rather than a surprise.
        """
        self._authenticate_as(_NORMAL_FIELDS["username"], _NORMAL_PASSWORD)

        response = self.client.get(self.permissions_url, format="json")

        # Current backend enforcement: IsAuthenticated → 200 for any valid user.
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "An authenticated (non-admin) user should currently receive 200. "
            "If this fails with 403, the view has been upgraded to IsAdminUser "
            "or a custom permission class — update this test accordingly.",
        )
