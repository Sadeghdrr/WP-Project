"""
Integration tests for scenario 3.6: officer rejects and returns case to cadet.

Reference docs:
- md-files/project-doc.md §4.2.1 (officer rejection goes back to cadet)
- md-files/24-swagger_documentation_report.md §3.2
  (POST /api/cases/{id}/officer-review/, OfficerReviewSerializer)
- md-files/16-cases_services_complaint_flow_report.md §3.2
  (officer reject -> returned_to_cadet, cadet can move back to officer_review)
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role
from cases.models import Case, CaseStatus, ComplainantStatus
from core.permissions_constants import CasesPerms

User = get_user_model()


class TestComplaintOfficerRejectToCadetFlow(TestCase):
    """
    Scenario 3.6 integration tests executed through real API endpoints.
    """

    @classmethod
    def setUpTestData(cls):
        # Complainant transitions (create/submit) need cases.add_case.
        cls.base_role, _ = Role.objects.get_or_create(
            name="Base User",
            defaults={"hierarchy_level": 0, "description": "Default user role."},
        )
        add_case_perm = Permission.objects.get(
            content_type__app_label="cases",
            codename=CasesPerms.ADD_CASE,
        )
        cls.base_role.permissions.add(add_case_perm)

        # Cadet permissions for complainant + case review.
        cls.cadet_role, _ = Role.objects.get_or_create(
            name="Cadet",
            defaults={"hierarchy_level": 1, "description": "Cadet role."},
        )
        cadet_review_perm = Permission.objects.get(
            content_type__app_label="cases",
            codename=CasesPerms.CAN_REVIEW_COMPLAINT,
        )
        cls.cadet_role.permissions.add(cadet_review_perm)

        # Officer permission for officer-review action.
        cls.officer_role, _ = Role.objects.get_or_create(
            name="Police Officer",
            defaults={"hierarchy_level": 2, "description": "Officer role."},
        )
        officer_perm = Permission.objects.get(
            content_type__app_label="cases",
            codename=CasesPerms.CAN_APPROVE_CASE,
        )
        cls.officer_role.permissions.add(officer_perm)

        cls.complainant_password = "OfficerReject!Pass41"
        cls.complainant = User.objects.create_user(
            username="officer_reject_complainant",
            password=cls.complainant_password,
            email="officer_reject_complainant@example.com",
            phone_number="09130001041",
            national_id="3200001041",
            first_name="OfficerReject",
            last_name="Complainant",
            role=cls.base_role,
        )

        cls.cadet_password = "OfficerReject!Pass42"
        cls.cadet_user = User.objects.create_user(
            username="officer_reject_cadet",
            password=cls.cadet_password,
            email="officer_reject_cadet@example.com",
            phone_number="09130001042",
            national_id="3200001042",
            first_name="OfficerReject",
            last_name="Cadet",
            role=cls.cadet_role,
        )

        cls.officer_password = "OfficerReject!Pass43"
        cls.officer_user = User.objects.create_user(
            username="officer_reject_officer",
            password=cls.officer_password,
            email="officer_reject_officer@example.com",
            phone_number="09130001043",
            national_id="3200001043",
            first_name="OfficerReject",
            last_name="Officer",
            role=cls.officer_role,
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

    def arrange_case_in_officer_review(self) -> int:
        """
        Build prerequisite flow via APIs:
        complaint create -> submit -> cadet approves complainant + case.
        """
        self.login_as(self.complainant, self.complainant_password)
        create_resp = self.client.post(
            self.case_create_url,
            {
                "creation_type": "complaint",
                "title": "Officer reject arrangement case",
                "description": "Prepared for officer reject path testing.",
                "crime_level": 1,
            },
            format="json",
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        case_id = create_resp.data["id"]
        self.assertEqual(create_resp.data["status"], CaseStatus.COMPLAINT_REGISTERED)

        submit_url = reverse("case-submit", kwargs={"pk": case_id})
        submit_resp = self.client.post(submit_url, format="json")
        self.assertEqual(submit_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(submit_resp.data["status"], CaseStatus.CADET_REVIEW)

        complainants_url = reverse("case-complainants", kwargs={"pk": case_id})
        complainants_resp = self.client.get(complainants_url, format="json")
        self.assertEqual(complainants_resp.status_code, status.HTTP_200_OK)
        self.assertGreater(len(complainants_resp.data), 0)
        complainant_id = complainants_resp.data[0]["id"]

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
        self.assertEqual(
            complainant_review_resp.data["status"],
            ComplainantStatus.APPROVED,
        )

        cadet_review_url = reverse("case-cadet-review", kwargs={"pk": case_id})
        cadet_review_resp = self.client.post(
            cadet_review_url,
            {"decision": "approve"},
            format="json",
        )
        self.assertEqual(cadet_review_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(cadet_review_resp.data["status"], CaseStatus.OFFICER_REVIEW)

        return case_id

    def test_officer_reject_returns_case_to_cadet(self):
        """
        Officer reject should transition officer_review -> returned_to_cadet.
        """
        case_id = self.arrange_case_in_officer_review()
        self.login_as(self.officer_user, self.officer_password)

        officer_review_url = reverse("case-officer-review", kwargs={"pk": case_id})
        reject_resp = self.client.post(
            officer_review_url,
            {
                "decision": "reject",
                "message": "Evidence package is inconsistent. Return to cadet.",
            },
            format="json",
        )

        self.assertEqual(
            reject_resp.status_code,
            status.HTTP_200_OK,
            msg=f"Officer reject failed: {reject_resp.data}",
        )
        self.assertEqual(reject_resp.data["status"], CaseStatus.RETURNED_TO_CADET)

        case = Case.objects.get(pk=case_id)
        self.assertEqual(case.status, CaseStatus.RETURNED_TO_CADET)

        status_log_url = reverse("case-status-log", kwargs={"pk": case_id})
        status_log_resp = self.client.get(status_log_url, format="json")
        self.assertEqual(status_log_resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(status_log_resp.data), 4)

        latest = status_log_resp.data[0]
        self.assertEqual(latest["from_status"], CaseStatus.OFFICER_REVIEW)
        self.assertEqual(latest["to_status"], CaseStatus.RETURNED_TO_CADET)
        self.assertEqual(latest["changed_by"], self.officer_user.id)

    def test_cadet_can_transition_returned_to_cadet_back_to_officer_review(self):
        """
        Optional follow-up:
        After officer rejection, cadet can move returned_to_cadet -> officer_review.
        """
        case_id = self.arrange_case_in_officer_review()
        self.login_as(self.officer_user, self.officer_password)
        officer_review_url = reverse("case-officer-review", kwargs={"pk": case_id})
        reject_resp = self.client.post(
            officer_review_url,
            {
                "decision": "reject",
                "message": "Return for cadet re-review.",
            },
            format="json",
        )
        self.assertEqual(reject_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(reject_resp.data["status"], CaseStatus.RETURNED_TO_CADET)

        self.login_as(self.cadet_user, self.cadet_password)
        transition_url = reverse("case-transition", kwargs={"pk": case_id})
        transition_resp = self.client.post(
            transition_url,
            {"target_status": CaseStatus.OFFICER_REVIEW},
            format="json",
        )

        self.assertEqual(
            transition_resp.status_code,
            status.HTTP_200_OK,
            msg=f"Cadet transition back to officer_review failed: {transition_resp.data}",
        )
        self.assertEqual(transition_resp.data["status"], CaseStatus.OFFICER_REVIEW)

    def test_officer_reject_without_message_returns_400(self):
        """
        OfficerReviewSerializer requires message when decision=reject.
        """
        case_id = self.arrange_case_in_officer_review()
        self.login_as(self.officer_user, self.officer_password)

        officer_review_url = reverse("case-officer-review", kwargs={"pk": case_id})
        resp = self.client.post(
            officer_review_url,
            {"decision": "reject"},
            format="json",
        )

        self.assertEqual(
            resp.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Reject without message should return 400. Body: {resp.data}",
        )
        self.assertIn("message", resp.data)

    def test_normal_user_cannot_call_officer_review(self):
        """
        Normal complainant user attempting officer review must be denied (403).
        """
        case_id = self.arrange_case_in_officer_review()
        self.login_as(self.complainant, self.complainant_password)

        officer_review_url = reverse("case-officer-review", kwargs={"pk": case_id})
        resp = self.client.post(
            officer_review_url,
            {
                "decision": "reject",
                "message": "Unauthorized actor should not reach service action.",
            },
            format="json",
        )

        self.assertEqual(
            resp.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=f"Expected 403 for normal user officer-review action. Body: {resp.data}",
        )
