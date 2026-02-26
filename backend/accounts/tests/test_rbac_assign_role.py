"""
Integration tests — 2.4 Assign role to a user.

Requirement reference:
  - md-files/project-doc.md §4.1 (admin assigns roles after registration)
  - md-files/accounts_api_report.md (PATCH /users/{id}/assign-role/)
  - md-files/accounts_services_rbac_report.md (authorization behavior)

Engineering constraints:
  - django.test.TestCase + rest_framework.test.APIClient.
  - Real endpoint calls through APIClient (no service-layer direct calls).
  - Authentication via real login endpoint, Bearer JWT headers.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role

User = get_user_model()


class TestAssignRoleEndpoint(TestCase):
    @classmethod
    def setUpTestData(cls):
        """
        Seed role hierarchy and users required for assign-role tests.

        Roles:
          - System Admin: authorized performer role.
          - Base User: low privilege baseline role.
          - Detective: target role to assign in success test.
        """
        cls.system_admin_role, _ = Role.objects.get_or_create(
            name="System Admin",
            defaults={
                "description": "Full system access",
                "hierarchy_level": 100,
            },
        )
        cls.base_user_role, _ = Role.objects.get_or_create(
            name="Base User",
            defaults={
                "description": "Default role",
                "hierarchy_level": 1,
            },
        )
        cls.detective_role, _ = Role.objects.get_or_create(
            name="Detective",
            defaults={
                "description": "Investigates cases",
                "hierarchy_level": 5,
            },
        )

        # Grant can_manage_users so admin can assign any role (including same-level)
        manage_perm = Permission.objects.get(
            codename="can_manage_users",
            content_type__app_label="accounts",
        )
        cls.system_admin_role.permissions.add(manage_perm)

        cls.admin_user = User.objects.create_user(
            username="rbac_admin",
            password="Str0ng!Admin99",
            email="rbac_admin@example.com",
            phone_number="09130010001",
            national_id="9001000001",
            first_name="Rbac",
            last_name="Admin",
            role=cls.system_admin_role,
        )
        cls.target_user = User.objects.create_user(
            username="rbac_target",
            password="Str0ng!Target99",
            email="rbac_target@example.com",
            phone_number="09130010002",
            national_id="9001000002",
            first_name="Rbac",
            last_name="Target",
            role=cls.base_user_role,
        )
        cls.normal_user = User.objects.create_user(
            username="rbac_normal",
            password="Str0ng!Normal99",
            email="rbac_normal@example.com",
            phone_number="09130010003",
            national_id="9001000003",
            first_name="Rbac",
            last_name="Normal",
            role=cls.base_user_role,
        )

    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse("accounts:login")
        self.assign_role_url = reverse(
            "accounts:user-assign-role",
            kwargs={"pk": self.target_user.pk},
        )
        self.roles_list_url = reverse("accounts:role-list")

    def _authenticate_as(self, *, identifier: str, password: str) -> str:
        """
        Login through the real endpoint and set Bearer token on APIClient.
        """
        login_resp = self.client.post(
            self.login_url,
            {"identifier": identifier, "password": password},
            format="json",
        )
        self.assertEqual(
            login_resp.status_code,
            status.HTTP_200_OK,
            msg=f"Login failed in test setup: {login_resp.data}",
        )
        token = login_resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return token

    def test_assign_role_success(self):
        """
        Admin can assign a new role to a user via PATCH /users/{id}/assign-role/.
        """
        self._authenticate_as(identifier="rbac_admin", password="Str0ng!Admin99")

        resp = self.client.patch(
            self.assign_role_url,
            {"role_id": self.detective_role.id},
            format="json",
        )

        self.assertEqual(
            resp.status_code,
            status.HTTP_200_OK,
            msg=f"Expected 200 for successful role assignment. Body: {resp.data}",
        )
        self.assertEqual(resp.data["id"], self.target_user.id)
        self.assertEqual(resp.data["role"], self.detective_role.id)
        self.assertEqual(resp.data["role_detail"]["name"], "Detective")
        self.assertEqual(resp.data["role_detail"]["hierarchy_level"], 5)

        self.target_user.refresh_from_db()
        self.assertEqual(self.target_user.role_id, self.detective_role.id)

    def test_assign_role_forbidden_for_non_admin(self):
        """
        Low-privilege user cannot assign roles; endpoint must return 403.
        """
        self._authenticate_as(identifier="rbac_normal", password="Str0ng!Normal99")

        resp = self.client.patch(
            self.assign_role_url,
            {"role_id": self.detective_role.id},
            format="json",
        )

        self.assertEqual(
            resp.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=f"Expected 403 when non-admin assigns role. Body: {resp.data}",
        )
        self.target_user.refresh_from_db()
        self.assertEqual(self.target_user.role_id, self.base_user_role.id)

    def test_role_change_affects_permissions(self):
        """
        After role assignment, target user's access to admin-only endpoint changes.
        """
        self._authenticate_as(identifier="rbac_target", password="Str0ng!Target99")
        before_resp = self.client.get(self.roles_list_url)
        self.assertEqual(
            before_resp.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=f"Expected 403 before role elevation. Body: {before_resp.data}",
        )

        self._authenticate_as(identifier="rbac_admin", password="Str0ng!Admin99")
        assign_resp = self.client.patch(
            self.assign_role_url,
            {"role_id": self.system_admin_role.id},
            format="json",
        )
        self.assertEqual(
            assign_resp.status_code,
            status.HTTP_200_OK,
            msg=f"Role assignment should succeed. Body: {assign_resp.data}",
        )

        # Re-login as target user to validate end-to-end auth flow after role change.
        self._authenticate_as(identifier="rbac_target", password="Str0ng!Target99")
        after_resp = self.client.get(self.roles_list_url)
        self.assertEqual(
            after_resp.status_code,
            status.HTTP_200_OK,
            msg=f"Expected 200 after role elevation. Body: {after_resp.data}",
        )
        self.assertIsInstance(after_resp.data, list)

