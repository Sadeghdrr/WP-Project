"""
Integration tests for scenario 3.5: three-strike rejection -> VOIDED.

Reference docs:
- md-files/project-doc.md §4.2.1
  (if complainant submits false/incomplete info 3 times, case is voided)
- md-files/swagger_documentation_report.md §3.2
  (POST /api/cases/{id}/cadet-review/, POST /api/cases/{id}/resubmit/)
- md-files/cases_services_complaint_flow_report.md §3.3
  (reject/resubmit cycles and auto-void after third reject)
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


class TestComplaintThreeStrikeVoidFlow(TestCase):
    """
    Scenario 3.5 integration tests executed via real API endpoints.
    """

    @classmethod
    def setUpTestData(cls):
        # Complainant-side transitions (submit/resubmit) use cases.add_case.
        cls.base_role, _ = Role.objects.get_or_create(
            name="Base User",
            defaults={"hierarchy_level": 0, "description": "Default user role."},
        )
        add_case_perm = Permission.objects.get(
            content_type__app_label="cases",
            codename=CasesPerms.ADD_CASE,
        )
        cls.base_role.permissions.add(add_case_perm)

        # Cadet-side review/reject actions use cases.can_review_complaint.
        cls.cadet_role, _ = Role.objects.get_or_create(
            name="Cadet",
            defaults={"hierarchy_level": 1, "description": "Cadet role."},
        )
        cadet_perm = Permission.objects.get(
            content_type__app_label="cases",
            codename=CasesPerms.CAN_REVIEW_COMPLAINT,
        )
        cls.cadet_role.permissions.add(cadet_perm)

        cls.complainant_password = "ThreeStrike!Pass41"
        cls.complainant = User.objects.create_user(
            username="three_strike_complainant",
            password=cls.complainant_password,
            email="three_strike_complainant@example.com",
            phone_number="09130000941",
            national_id="3200000941",
            first_name="ThreeStrike",
            last_name="Complainant",
            role=cls.base_role,
        )

        cls.cadet_password = "ThreeStrike!Pass42"
        cls.cadet_user = User.objects.create_user(
            username="three_strike_cadet",
            password=cls.cadet_password,
            email="three_strike_cadet@example.com",
            phone_number="09130000942",
            national_id="3200000942",
            first_name="ThreeStrike",
            last_name="Cadet",
            role=cls.cadet_role,
        )

        cls.other_user_password = "ThreeStrike!Pass43"
        cls.other_user = User.objects.create_user(
            username="three_strike_other",
            password=cls.other_user_password,
            email="three_strike_other@example.com",
            phone_number="09130000943",
            national_id="3200000943",
            first_name="ThreeStrike",
            last_name="Other",
            role=cls.base_role,
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

    def arrange_case_in_cadet_review(self) -> int:
        """
        Create complaint case and submit to cadet_review through API.
        """
        self.login_as(self.complainant, self.complainant_password)
        create_resp = self.client.post(
            self.case_create_url,
            {
                "creation_type": "complaint",
                "title": "Three-strike arrangement case",
                "description": "Prepared for cadet reject/resubmit cycles.",
                "crime_level": 1,
            },
            format="json",
        )
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
        return case_id

    def test_single_reject_then_resubmit_cycle(self):
        """
        Cadet reject returns to complainant; complainant resubmit returns to cadet_review.
        """
        case_id = self.arrange_case_in_cadet_review()

        self.login_as(self.cadet_user, self.cadet_password)
        cadet_review_url = reverse("case-cadet-review", kwargs={"pk": case_id})
        reject_resp = self.client.post(
            cadet_review_url,
            {"decision": "reject", "message": "Missing critical incident details."},
            format="json",
        )

        self.assertEqual(reject_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            reject_resp.data["status"],
            CaseStatus.RETURNED_TO_COMPLAINANT,
        )
        self.assertEqual(reject_resp.data["rejection_count"], 1)

        case = Case.objects.get(pk=case_id)
        self.assertEqual(case.status, CaseStatus.RETURNED_TO_COMPLAINANT)
        self.assertEqual(case.rejection_count, 1)

        self.login_as(self.complainant, self.complainant_password)
        resubmit_url = reverse("case-resubmit", kwargs={"pk": case_id})
        resubmit_resp = self.client.post(
            resubmit_url,
            {"description": "Added the missing incident details for re-review."},
            format="json",
        )

        self.assertEqual(
            resubmit_resp.status_code,
            status.HTTP_200_OK,
            msg=f"Resubmit endpoint failed: {resubmit_resp.data}",
        )
        self.assertEqual(resubmit_resp.data["status"], CaseStatus.CADET_REVIEW)
        self.assertEqual(resubmit_resp.data["rejection_count"], 1)

    def test_three_strike_rejection_moves_case_to_voided_and_blocks_further_flow(self):
        """
        After 3 cadet rejections, case must auto-transition to VOIDED.
        """
        case_id = self.arrange_case_in_cadet_review()
        cadet_review_url = reverse("case-cadet-review", kwargs={"pk": case_id})
        resubmit_url = reverse("case-resubmit", kwargs={"pk": case_id})
        submit_url = reverse("case-submit", kwargs={"pk": case_id})

        for i in range(3):
            self.login_as(self.cadet_user, self.cadet_password)
            reject_resp = self.client.post(
                cadet_review_url,
                {
                    "decision": "reject",
                    "message": f"Reject strike {i + 1}: information still incomplete.",
                },
                format="json",
            )
            self.assertEqual(
                reject_resp.status_code,
                status.HTTP_200_OK,
                msg=f"Cadet reject strike {i + 1} failed: {reject_resp.data}",
            )

            if i < 2:
                self.assertEqual(
                    reject_resp.data["status"],
                    CaseStatus.RETURNED_TO_COMPLAINANT,
                )
                self.assertEqual(reject_resp.data["rejection_count"], i + 1)

                self.login_as(self.complainant, self.complainant_password)
                resubmit_resp = self.client.post(
                    resubmit_url,
                    {
                        "description": f"Resubmission after strike {i + 1}.",
                    },
                    format="json",
                )
                self.assertEqual(
                    resubmit_resp.status_code,
                    status.HTTP_200_OK,
                    msg=f"Resubmit after strike {i + 1} failed: {resubmit_resp.data}",
                )
                self.assertEqual(resubmit_resp.data["status"], CaseStatus.CADET_REVIEW)
            else:
                self.assertEqual(reject_resp.data["status"], CaseStatus.VOIDED)
                self.assertEqual(reject_resp.data["rejection_count"], 3)

        case = Case.objects.get(pk=case_id)
        self.assertEqual(case.status, CaseStatus.VOIDED)
        self.assertEqual(case.rejection_count, 3)

        # After VOIDED, no further complainant submission actions should work.
        self.login_as(self.complainant, self.complainant_password)
        resubmit_after_voided = self.client.post(
            resubmit_url,
            {"description": "Attempt to resubmit after voided."},
            format="json",
        )
        self.assertEqual(
            resubmit_after_voided.status_code,
            status.HTTP_409_CONFLICT,
            msg=(
                "Resubmit must fail after case is voided. "
                f"Body: {resubmit_after_voided.data}"
            ),
        )

        submit_after_voided = self.client.post(submit_url, format="json")
        self.assertEqual(
            submit_after_voided.status_code,
            status.HTTP_409_CONFLICT,
            msg=f"Submit must fail after case is voided. Body: {submit_after_voided.data}",
        )

        status_log_url = reverse("case-status-log", kwargs={"pk": case_id})
        status_log_resp = self.client.get(status_log_url, format="json")
        self.assertEqual(status_log_resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(status_log_resp.data), 7)

        latest = status_log_resp.data[0]
        self.assertEqual(latest["to_status"], CaseStatus.VOIDED)
        self.assertEqual(latest["from_status"], CaseStatus.CADET_REVIEW)
        self.assertEqual(latest["changed_by"], self.cadet_user.id)

    def test_only_primary_complainant_can_resubmit(self):
        """
        Non-complainant user attempting resubmit should get 403.
        """
        case_id = self.arrange_case_in_cadet_review()
        self.login_as(self.cadet_user, self.cadet_password)

        cadet_review_url = reverse("case-cadet-review", kwargs={"pk": case_id})
        reject_resp = self.client.post(
            cadet_review_url,
            {"decision": "reject", "message": "Initial reject for ownership guard test."},
            format="json",
        )
        self.assertEqual(reject_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(reject_resp.data["status"], CaseStatus.RETURNED_TO_COMPLAINANT)

        self.login_as(self.other_user, self.other_user_password)
        resubmit_url = reverse("case-resubmit", kwargs={"pk": case_id})
        resubmit_resp = self.client.post(
            resubmit_url,
            {"description": "Unauthorized resubmission attempt."},
            format="json",
        )

        self.assertEqual(
            resubmit_resp.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=f"Non-owner resubmit should return 403. Body: {resubmit_resp.data}",
        )

    def test_cadet_reject_without_message_returns_400(self):
        """
        Cadet reject payload without message should fail serializer validation.
        """
        case_id = self.arrange_case_in_cadet_review()
        self.login_as(self.cadet_user, self.cadet_password)

        cadet_review_url = reverse("case-cadet-review", kwargs={"pk": case_id})
        resp = self.client.post(
            cadet_review_url,
            {"decision": "reject"},
            format="json",
        )

        self.assertEqual(
            resp.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Reject without message should return 400. Body: {resp.data}",
        )
        self.assertIn("message", resp.data)
