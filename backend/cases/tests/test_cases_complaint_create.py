"""
Integration tests for scenario 3.1: a normal user creates a complaint case.

Reference docs:
- md-files/project-doc.md §4.2.1 (complaint-based case creation flow)
- md-files/24-swagger_documentation_report.md §3.1/§3.2
  (POST /api/accounts/auth/login/, POST /api/cases/)
- md-files/16-cases_services_complaint_flow_report.md §3.1 Step 1
  (201 Created, initial status = "complaint_registered")
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role
from cases.models import (
    Case,
    CaseComplainant,
    CaseCreationType,
    CaseStatus,
    ComplainantStatus,
)

User = get_user_model()


class TestComplaintCaseCreateFlow(TestCase):
    """
    Scenario 3.1 integration tests executed through real HTTP endpoints.
    """

    @classmethod
    def setUpTestData(cls):
        # project-doc §4.1: users start as "Base User" and can act as complainants.
        cls.base_role, _ = Role.objects.get_or_create(
            name="Base User",
            defaults={
                "hierarchy_level": 0,
                "description": "Default role for normal/citizen users.",
            },
        )

        cls.normal_user_password = "Complaint!Pass42"
        cls.normal_user = User.objects.create_user(
            username="complaint_creator_user",
            password=cls.normal_user_password,
            email="complaint_creator_user@example.com",
            phone_number="09130000421",
            national_id="3200000421",
            first_name="Complaint",
            last_name="Creator",
            role=cls.base_role,
        )

    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse("accounts:login")
        self.case_create_url = reverse("case-list")

    def login_as(self, user: User, password: str) -> str:
        """
        Authenticate through POST /api/accounts/auth/login/ and set Bearer token.
        """
        resp = self.client.post(
            self.login_url,
            {"identifier": user.username, "password": password},
            format="json",
        )
        self.assertEqual(
            resp.status_code,
            status.HTTP_200_OK,
            msg=f"Login failed for test user: {resp.data}",
        )
        token = resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return token

    def test_normal_user_can_create_complaint_case(self):
        """
        project-doc §4.2.1 + complaint flow report:
        complainant creates case, initial status must be complaint_registered.
        """
        self.login_as(self.normal_user, self.normal_user_password)

        payload = {
            "creation_type": "complaint",
            "title": "Stolen laptop from dorm room",
            "description": "My laptop was stolen while I was in class.",
            "crime_level": 2,
        }

        resp = self.client.post(self.case_create_url, payload, format="json")

        self.assertEqual(
            resp.status_code,
            status.HTTP_201_CREATED,
            msg=f"Expected complaint case creation to return 201. Body: {resp.data}",
        )
        self.assertIn("id", resp.data)
        self.assertIn("status", resp.data)
        self.assertEqual(resp.data["status"], CaseStatus.COMPLAINT_REGISTERED)

        case = Case.objects.get(pk=resp.data["id"])
        self.assertEqual(case.created_by_id, self.normal_user.id)
        self.assertEqual(case.creation_type, CaseCreationType.COMPLAINT)
        self.assertEqual(case.status, CaseStatus.COMPLAINT_REGISTERED)

        primary_complainant = CaseComplainant.objects.get(
            case=case,
            user=self.normal_user,
        )
        self.assertTrue(primary_complainant.is_primary)
        self.assertEqual(primary_complainant.status, ComplainantStatus.PENDING)

    def test_create_complaint_case_requires_authentication(self):
        """
        Swagger docs define POST /api/cases/ as authenticated-only.
        Without credentials, DRF must return 401.
        """
        payload = {
            "creation_type": "complaint",
            "title": "Unauthorized attempt",
            "description": "This request should fail without JWT.",
            "crime_level": 1,
        }

        resp = self.client.post(self.case_create_url, payload, format="json")

        self.assertEqual(
            resp.status_code,
            status.HTTP_401_UNAUTHORIZED,
            msg=f"Unauthenticated case creation should return 401. Body: {resp.data}",
        )
