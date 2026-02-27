"""
Integration tests for scenario 3.2: submit complaint case to Cadet Review.

Reference docs:
- md-files/project-doc.md §4.2.1 (complaint submission then Cadet review)
- md-files/24-swagger_documentation_report.md §3.2
  (POST /api/cases/{id}/submit/, GET /api/cases/{id}/status-log/)
- md-files/16-cases_services_complaint_flow_report.md §3.1 Step 2
  (submit: 200 OK, status becomes "cadet_review")
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role
from cases.models import Case, CaseStatus
from core.permissions_constants import CasesPerms

User = get_user_model()


class TestComplaintCaseSubmitFlow(TestCase):
    """
    Scenario 3.2 integration tests executed through real HTTP endpoints.
    """

    @classmethod
    def setUpTestData(cls):
        # project-doc §4.1: base users can register and act as complainants.
        cls.base_role, _ = Role.objects.get_or_create(
            name="Base User",
            defaults={
                "hierarchy_level": 0,
                "description": "Default role for normal/citizen users.",
            },
        )

        # Submit transition (complaint_registered -> cadet_review) is guarded by
        # cases.add_case in the transition map.
        add_case_perm = Permission.objects.get(
            content_type__app_label="cases",
            codename=CasesPerms.ADD_CASE,
        )
        cls.base_role.permissions.add(add_case_perm)

        cls.complainant_password = "Submit!Pass42"
        cls.complainant = User.objects.create_user(
            username="complaint_submit_owner",
            password=cls.complainant_password,
            email="complaint_submit_owner@example.com",
            phone_number="09130000621",
            national_id="3200000621",
            first_name="Complaint",
            last_name="SubmitOwner",
            role=cls.base_role,
        )

        cls.other_user_password = "Submit!Pass43"
        cls.other_user = User.objects.create_user(
            username="complaint_submit_other",
            password=cls.other_user_password,
            email="complaint_submit_other@example.com",
            phone_number="09130000622",
            national_id="3200000622",
            first_name="Complaint",
            last_name="SubmitOther",
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

    def create_complaint_case_via_api(self, user: User, password: str) -> int:
        """
        Arrange: create case via POST /api/cases/ (real endpoint).
        """
        self.login_as(user, password)
        payload = {
            "creation_type": "complaint",
            "title": "Case prepared for submit flow",
            "description": "Created as setup for complaint submit transition.",
            "crime_level": 1,
        }
        resp = self.client.post(self.case_create_url, payload, format="json")
        self.assertEqual(
            resp.status_code,
            status.HTTP_201_CREATED,
            msg=f"Case setup creation failed: {resp.data}",
        )
        self.assertEqual(resp.data["status"], CaseStatus.COMPLAINT_REGISTERED)
        return resp.data["id"]

    def test_primary_complainant_can_submit_case_to_cadet_review(self):
        """
        POST /api/cases/{id}/submit/ should move complaint_registered -> cadet_review.
        """
        case_id = self.create_complaint_case_via_api(
            self.complainant,
            self.complainant_password,
        )
        submit_url = reverse("case-submit", kwargs={"pk": case_id})

        submit_resp = self.client.post(submit_url, format="json")

        self.assertEqual(
            submit_resp.status_code,
            status.HTTP_200_OK,
            msg=f"Expected 200 on submit endpoint. Body: {submit_resp.data}",
        )
        self.assertEqual(submit_resp.data["status"], CaseStatus.CADET_REVIEW)

        case = Case.objects.get(pk=case_id)
        self.assertEqual(case.status, CaseStatus.CADET_REVIEW)

        # Verify transition appears in status-log endpoint as latest entry.
        status_log_url = reverse("case-status-log", kwargs={"pk": case_id})
        log_resp = self.client.get(status_log_url, format="json")
        self.assertEqual(log_resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(log_resp.data, list)
        self.assertGreaterEqual(
            len(log_resp.data),
            2,
            msg="Expected at least creation + submit status log records.",
        )

        latest = log_resp.data[0]
        self.assertEqual(latest["from_status"], CaseStatus.COMPLAINT_REGISTERED)
        self.assertEqual(latest["to_status"], CaseStatus.CADET_REVIEW)
        self.assertEqual(latest["changed_by"], self.complainant.id)

    def test_submit_requires_authentication(self):
        """
        Unauthenticated submit request must be rejected with 401.
        """
        case_id = self.create_complaint_case_via_api(
            self.complainant,
            self.complainant_password,
        )
        self.client.credentials()

        submit_url = reverse("case-submit", kwargs={"pk": case_id})
        resp = self.client.post(submit_url, format="json")

        self.assertEqual(
            resp.status_code,
            status.HTTP_401_UNAUTHORIZED,
            msg=f"Unauthenticated submit should return 401. Body: {resp.data}",
        )

    def test_non_primary_user_cannot_submit_case(self):
        """
        Different authenticated user (not case complainant) must receive 403.
        """
        case_id = self.create_complaint_case_via_api(
            self.complainant,
            self.complainant_password,
        )
        self.login_as(self.other_user, self.other_user_password)

        submit_url = reverse("case-submit", kwargs={"pk": case_id})
        resp = self.client.post(submit_url, format="json")

        self.assertEqual(
            resp.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=f"Non-owner submit should return 403. Body: {resp.data}",
        )

        case = Case.objects.get(pk=case_id)
        self.assertEqual(case.status, CaseStatus.COMPLAINT_REGISTERED)

    def test_submit_when_case_not_in_complaint_registered_returns_409(self):
        """
        Calling submit again from cadet_review is an invalid transition.
        """
        case_id = self.create_complaint_case_via_api(
            self.complainant,
            self.complainant_password,
        )
        submit_url = reverse("case-submit", kwargs={"pk": case_id})

        first = self.client.post(submit_url, format="json")
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        second = self.client.post(submit_url, format="json")
        self.assertEqual(
            second.status_code,
            status.HTTP_409_CONFLICT,
            msg=f"Invalid-state submit should return 409. Body: {second.data}",
        )
