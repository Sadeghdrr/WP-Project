"""
Integration tests for scenario 3.3: Cadet reviews complainant + case.

Reference docs:
- md-files/project-doc.md §4.2.1 (complaint flow and Cadet responsibilities)
- md-files/swagger_documentation_report.md §3.2 (cadet-review, complainant-review)
- md-files/cases_services_complaint_flow_report.md §3.1 Steps 3-4
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role
from cases.models import Case, CaseComplainant, CaseStatus, ComplainantStatus
from core.permissions_constants import CasesPerms

User = get_user_model()


class TestComplaintCadetReviewFlow(TestCase):
    """
    Scenario 3.3 integration tests through real HTTP endpoints only.
    """

    @classmethod
    def setUpTestData(cls):
        # Base user can create/submit complaint cases.
        cls.base_role, _ = Role.objects.get_or_create(
            name="Base User",
            defaults={"hierarchy_level": 0, "description": "Default user role."},
        )
        add_case_perm = Permission.objects.get(
            content_type__app_label="cases",
            codename=CasesPerms.ADD_CASE,
        )
        cls.base_role.permissions.add(add_case_perm)

        # Cadet can review complainants and complaint cases.
        cls.cadet_role, _ = Role.objects.get_or_create(
            name="Cadet",
            defaults={"hierarchy_level": 1, "description": "Cadet role."},
        )
        review_perm = Permission.objects.get(
            content_type__app_label="cases",
            codename=CasesPerms.CAN_REVIEW_COMPLAINT,
        )
        cls.cadet_role.permissions.add(review_perm)

        cls.complainant_password = "CadetFlow!Pass41"
        cls.complainant = User.objects.create_user(
            username="cadet_flow_complainant",
            password=cls.complainant_password,
            email="cadet_flow_complainant@example.com",
            phone_number="09130000731",
            national_id="3200000731",
            first_name="CadetFlow",
            last_name="Complainant",
            role=cls.base_role,
        )

        cls.cadet_password = "CadetFlow!Pass42"
        cls.cadet_user = User.objects.create_user(
            username="cadet_flow_cadet",
            password=cls.cadet_password,
            email="cadet_flow_cadet@example.com",
            phone_number="09130000732",
            national_id="3200000732",
            first_name="CadetFlow",
            last_name="Cadet",
            role=cls.cadet_role,
        )

    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse("accounts:login")
        self.case_create_url = reverse("case-list")

    def login_as(self, user: User, password: str) -> str:
        """
        Authenticate via real login endpoint and set Bearer token.
        """
        resp = self.client.post(
            self.login_url,
            {"identifier": user.username, "password": password},
            format="json",
        )
        self.assertEqual(
            resp.status_code,
            status.HTTP_200_OK,
            msg=f"Login failed for {user.username}: {resp.data}",
        )
        token = resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return token

    def arrange_case_submitted_to_cadet_review(self) -> tuple[int, int]:
        """
        Create complaint case and submit it as complainant (scenario 3.2 setup).

        Returns:
            (case_id, primary_complainant_id)
        """
        self.login_as(self.complainant, self.complainant_password)

        create_payload = {
            "creation_type": "complaint",
            "title": "Cadet review arrangement case",
            "description": "Case created for cadet review integration tests.",
            "crime_level": 1,
        }
        create_resp = self.client.post(self.case_create_url, create_payload, format="json")
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        case_id = create_resp.data["id"]
        self.assertEqual(create_resp.data["status"], CaseStatus.COMPLAINT_REGISTERED)

        submit_url = reverse("case-submit", kwargs={"pk": case_id})
        submit_resp = self.client.post(submit_url, format="json")
        self.assertEqual(
            submit_resp.status_code,
            status.HTTP_200_OK,
            msg=f"Submit arrangement step failed: {submit_resp.data}",
        )
        self.assertEqual(submit_resp.data["status"], CaseStatus.CADET_REVIEW)

        complainants_url = reverse("case-complainants", kwargs={"pk": case_id})
        complainants_resp = self.client.get(complainants_url, format="json")
        self.assertEqual(complainants_resp.status_code, status.HTTP_200_OK)
        self.assertGreater(len(complainants_resp.data), 0)

        complainant_id = complainants_resp.data[0]["id"]
        return case_id, complainant_id

    def test_cadet_can_approve_complainant(self):
        """
        Cadet approves individual complainant:
        POST /api/cases/{id}/complainants/{complainant_id}/review/
        """
        case_id, complainant_id = self.arrange_case_submitted_to_cadet_review()
        self.login_as(self.cadet_user, self.cadet_password)

        review_url = reverse(
            "case-review-complainant",
            kwargs={"pk": case_id, "complainant_pk": complainant_id},
        )
        resp = self.client.post(review_url, {"decision": "approve"}, format="json")

        self.assertEqual(
            resp.status_code,
            status.HTTP_200_OK,
            msg=f"Complainant review endpoint failed: {resp.data}",
        )
        self.assertEqual(resp.data["status"], ComplainantStatus.APPROVED)
        self.assertEqual(resp.data["reviewed_by"], self.cadet_user.id)

        complainant = CaseComplainant.objects.get(pk=complainant_id)
        self.assertEqual(complainant.status, ComplainantStatus.APPROVED)
        self.assertEqual(complainant.reviewed_by_id, self.cadet_user.id)

    def test_cadet_can_approve_case_and_move_to_officer_review(self):
        """
        After complainant approval, Cadet approves case:
        POST /api/cases/{id}/cadet-review/ -> status officer_review.
        """
        case_id, complainant_id = self.arrange_case_submitted_to_cadet_review()
        self.login_as(self.cadet_user, self.cadet_password)

        complainant_review_url = reverse(
            "case-review-complainant",
            kwargs={"pk": case_id, "complainant_pk": complainant_id},
        )
        complainant_review_resp = self.client.post(
            complainant_review_url,
            {"decision": "approve"},
            format="json",
        )
        self.assertEqual(complainant_review_resp.status_code, status.HTTP_200_OK)

        cadet_review_url = reverse("case-cadet-review", kwargs={"pk": case_id})
        cadet_review_resp = self.client.post(
            cadet_review_url,
            {"decision": "approve"},
            format="json",
        )

        self.assertEqual(
            cadet_review_resp.status_code,
            status.HTTP_200_OK,
            msg=f"Cadet case review failed: {cadet_review_resp.data}",
        )
        self.assertEqual(cadet_review_resp.data["status"], CaseStatus.OFFICER_REVIEW)

        case = Case.objects.get(pk=case_id)
        self.assertEqual(case.status, CaseStatus.OFFICER_REVIEW)

        # Verify status log transition and actor through the real endpoint.
        status_log_url = reverse("case-status-log", kwargs={"pk": case_id})
        status_log_resp = self.client.get(status_log_url, format="json")
        self.assertEqual(status_log_resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(status_log_resp.data), 3)

        latest = status_log_resp.data[0]
        self.assertEqual(latest["from_status"], CaseStatus.CADET_REVIEW)
        self.assertEqual(latest["to_status"], CaseStatus.OFFICER_REVIEW)
        self.assertEqual(latest["changed_by"], self.cadet_user.id)

    def test_normal_user_cannot_review_complainant(self):
        """
        Normal user token on complainant review endpoint must return 403.
        """
        case_id, complainant_id = self.arrange_case_submitted_to_cadet_review()
        self.login_as(self.complainant, self.complainant_password)

        review_url = reverse(
            "case-review-complainant",
            kwargs={"pk": case_id, "complainant_pk": complainant_id},
        )
        resp = self.client.post(review_url, {"decision": "approve"}, format="json")

        self.assertEqual(
            resp.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=f"Expected 403 for non-cadet complainant review. Body: {resp.data}",
        )

    def test_normal_user_cannot_cadet_approve_case(self):
        """
        Normal user token on cadet-review endpoint must return 403.
        """
        case_id, _ = self.arrange_case_submitted_to_cadet_review()
        self.login_as(self.complainant, self.complainant_password)

        cadet_review_url = reverse("case-cadet-review", kwargs={"pk": case_id})
        resp = self.client.post(cadet_review_url, {"decision": "approve"}, format="json")

        self.assertEqual(
            resp.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=f"Expected 403 for non-cadet case review. Body: {resp.data}",
        )

    def test_cadet_review_endpoint_rejects_invalid_case_state(self):
        """
        Cadet cannot review case before complainant submits it to cadet_review.
        """
        self.login_as(self.complainant, self.complainant_password)
        create_resp = self.client.post(
            self.case_create_url,
            {
                "creation_type": "complaint",
                "title": "Invalid-state cadet review test",
                "description": "Case remains complaint_registered.",
                "crime_level": 1,
            },
            format="json",
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        case_id = create_resp.data["id"]
        self.assertEqual(create_resp.data["status"], CaseStatus.COMPLAINT_REGISTERED)

        self.login_as(self.cadet_user, self.cadet_password)
        cadet_review_url = reverse("case-cadet-review", kwargs={"pk": case_id})
        resp = self.client.post(cadet_review_url, {"decision": "approve"}, format="json")

        self.assertEqual(
            resp.status_code,
            status.HTTP_409_CONFLICT,
            msg=f"Invalid-state cadet review should return 409. Body: {resp.data}",
        )
