"""
Integration tests — 2.2 Create a new Role.

Requirement reference: md-files/project-doc.md §2.2
    "Without needing to change the code, the system administrator must be able
    to add a new role, delete existing roles, or modify them."

API reference: md-files/02-accounts_api_report.md §1
    POST /api/accounts/roles/
    Access Level: System Admin
    Request fields: name, description, hierarchy_level (permissions optional)
"""

from __future__ import annotations

from uuid import uuid4

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


class TestRBACRoleCreate(TestCase):
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

        # Admin needs can_manage_users permission (permission-based RBAC)
        _grant(cls.system_admin_role, "can_manage_users", "accounts")

        cls.admin_password = "Adm!nRoleCreate99"
        cls.normal_password = "N0rmalRoleCreate88"

        cls.admin_user = User.objects.create_user(
            username="rbac_role_admin",
            password=cls.admin_password,
            email="rbac_role_admin@example.com",
            phone_number="09131111111",
            national_id="1111111111",
            first_name="Role",
            last_name="Admin",
            role=cls.system_admin_role,
        )

        cls.normal_user = User.objects.create_user(
            username="rbac_role_normal",
            password=cls.normal_password,
            email="rbac_role_normal@example.com",
            phone_number="09132222222",
            national_id="2222222222",
            first_name="Role",
            last_name="Normal",
            role=cls.base_user_role,
        )

    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse("accounts:login")
        self.roles_url = reverse("accounts:role-list")

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

    def _build_role_payload(self, role_name: str) -> dict[str, object]:
        return {
            "name": role_name,
            "description": "Intern role for temporary investigative support.",
            "hierarchy_level": 1,
        }

    def test_admin_can_create_role(self):
        self._authenticate(self.admin_user.username, self.admin_password)

        role_name = f"Intern-{uuid4().hex[:8]}"
        payload = self._build_role_payload(role_name)

        response = self.client.post(self.roles_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["name"], role_name)

        created_role = Role.objects.get(name=role_name)
        self.assertEqual(created_role.description, payload["description"])
        self.assertEqual(created_role.hierarchy_level, payload["hierarchy_level"])

        if "permissions" in response.data:
            self.assertIsInstance(response.data["permissions"], list)
        if "permissions_display" in response.data:
            self.assertIsInstance(response.data["permissions_display"], list)
        if "created_at" in response.data:
            self.assertIsNotNone(response.data["created_at"])

    def test_role_name_must_be_unique(self):
        self._authenticate(self.admin_user.username, self.admin_password)

        role_name = f"Intern-{uuid4().hex[:8]}"
        payload = self._build_role_payload(role_name)

        first_response = self.client.post(self.roles_url, payload, format="json")
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)

        duplicate_response = self.client.post(self.roles_url, payload, format="json")
        self.assertIn(
            duplicate_response.status_code,
            {status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT},
        )
        if duplicate_response.status_code == status.HTTP_400_BAD_REQUEST:
            self.assertIn("name", duplicate_response.data)

    def test_non_admin_cannot_create_role(self):
        self._authenticate(self.normal_user.username, self.normal_password)

        payload = self._build_role_payload(f"Intern-{uuid4().hex[:8]}")
        response = self.client.post(self.roles_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
