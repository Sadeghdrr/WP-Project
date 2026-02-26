"""
Integration tests — 2.3 Assign permissions to a role.

Requirement reference: md-files/project-doc.md §2.2
    "Without needing to change the code, the system administrator must be able
    to add a new role, delete existing roles, or modify them."

RBAC/API reference:
    POST /api/accounts/roles/{id}/assign-permissions/
    Payload schema: {"permission_ids": [<permission_pk>, ...]}
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


def _grant(role: Role, codename: str, app_label: str) -> None:
    perm = Permission.objects.get(codename=codename, content_type__app_label=app_label)
    role.permissions.add(perm)


class TestRBACAssignPermissions(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.system_admin_role, _ = Role.objects.get_or_create(
            name="System Admin",
            defaults={
                "description": "Highest administrative role.",
                "hierarchy_level": 100,
            },
        )
        cls.base_user_role, _ = Role.objects.get_or_create(
            name="Base User",
            defaults={
                "description": "Default role.",
                "hierarchy_level": 0,
            },
        )
        cls.target_role, _ = Role.objects.get_or_create(
            name="RBAC Permission Target",
            defaults={
                "description": "Role used for assign-permissions integration tests.",
                "hierarchy_level": 1,
            },
        )

        # Admin needs can_manage_users permission (permission-based RBAC)
        _grant(cls.system_admin_role, "can_manage_users", "accounts")

        cls.admin_password = "Adm!nAssignPerm99"
        cls.normal_password = "N0rmalAssignPerm88"

        cls.admin_user = User.objects.create_user(
            username="rbac_perm_admin",
            password=cls.admin_password,
            email="rbac_perm_admin@example.com",
            phone_number="09133333333",
            national_id="3333333333",
            first_name="Perm",
            last_name="Admin",
            role=cls.system_admin_role,
        )
        cls.normal_user = User.objects.create_user(
            username="rbac_perm_normal",
            password=cls.normal_password,
            email="rbac_perm_normal@example.com",
            phone_number="09134444444",
            national_id="4444444444",
            first_name="Perm",
            last_name="Normal",
            role=cls.base_user_role,
        )

        # Deterministic source of valid permissions without hardcoding IDs.
        cls.valid_permissions = list(
            Permission.objects.select_related("content_type").order_by("id")[:2]
        )
        if len(cls.valid_permissions) < 2:
            raise RuntimeError("Need at least two permissions for assign-permissions tests.")

    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse("accounts:login")
        self.assign_url = reverse(
            "accounts:role-assign-permissions",
            kwargs={"pk": self.target_role.pk},
        )

    def _authenticate(self, username: str, password: str) -> None:
        login_response = self.client.post(
            self.login_url,
            {"identifier": username, "password": password},
            format="json",
        )
        self.assertEqual(
            login_response.status_code,
            status.HTTP_200_OK,
            msg=f"Login failed for {username}: {login_response.data}",
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )

    def _permission_codes(self, permissions: list[Permission]) -> set[str]:
        return {
            f"{perm.content_type.app_label}.{perm.codename}"
            for perm in permissions
        }

    def test_admin_can_assign_permissions_to_role(self):
        # project-doc §2.2 requires RBAC admin manageability without code changes.
        self._authenticate(self.admin_user.username, self.admin_password)

        permission_ids = [perm.id for perm in self.valid_permissions]
        expected_codes = self._permission_codes(self.valid_permissions)

        response = self.client.post(
            self.assign_url,
            {"permission_ids": permission_ids},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.target_role.id)

        if "permissions" in response.data:
            self.assertEqual(set(response.data["permissions"]), set(permission_ids))
        if "permissions_display" in response.data:
            self.assertEqual(set(response.data["permissions_display"]), expected_codes)

        self.target_role.refresh_from_db()
        assigned_ids = set(self.target_role.permissions.values_list("id", flat=True))
        self.assertEqual(assigned_ids, set(permission_ids))

        # Idempotency: assigning the same set again should keep stable M2M state.
        second_response = self.client.post(
            self.assign_url,
            {"permission_ids": permission_ids},
            format="json",
        )
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.target_role.refresh_from_db()
        self.assertEqual(
            set(self.target_role.permissions.values_list("id", flat=True)),
            set(permission_ids),
        )

    def test_non_admin_cannot_assign_permissions(self):
        self._authenticate(self.normal_user.username, self.normal_password)

        payload = {"permission_ids": [self.valid_permissions[0].id]}
        response = self.client.post(self.assign_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.target_role.refresh_from_db()
        self.assertEqual(self.target_role.permissions.count(), 0)

    def test_invalid_permission_id_returns_400_and_keeps_existing_state(self):
        self._authenticate(self.admin_user.username, self.admin_password)

        baseline_permission = self.valid_permissions[0]
        self.target_role.permissions.set([baseline_permission.id])
        before_ids = set(self.target_role.permissions.values_list("id", flat=True))

        max_permission_id = Permission.objects.order_by("-id").values_list("id", flat=True).first() or 0
        invalid_permission_id = max_permission_id + 9999
        payload = {
            "permission_ids": [baseline_permission.id, invalid_permission_id],
        }

        response = self.client.post(self.assign_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("permission_ids", response.data)

        self.target_role.refresh_from_db()
        after_ids = set(self.target_role.permissions.values_list("id", flat=True))
        self.assertEqual(after_ids, before_ids)
