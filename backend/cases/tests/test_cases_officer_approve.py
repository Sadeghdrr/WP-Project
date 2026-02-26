"""
Integration tests for scenario 3.4: officer approves case -> OPEN.

Reference docs:
- md-files/project-doc.md §4.2.1 (Cadet forwards to Police Officer, Officer approves)
- md-files/swagger_documentation_report.md §3.2
  (POST /api/cases/{id}/officer-review/, GET /api/cases/{id}/, GET /api/cases/{id}/status-log/)
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


class TestComplaintOfficerApproveFlow(TestCase):
    """
    Scenario 3.4 integration tests through real endpoints only.
    """

    @classmethod
    def setUpTestData(cls):
        # Base role: complaint create/submit path uses cases.add_case transition perm.
        cls.base_role, _ = Role.objects.get_or_create(
            name="Base User",
            defaults={"hierarchy_level": 0, "description": "Default user role."},
        )
        add_case_perm = Permission.objects.get(
            content_type__app_label="cases",
            codename=CasesPerms.ADD_CASE,
        )
        cls.base_role.permissions.add(add_case_perm)

        # Cadet role: review complainant + cadet review endpoint.
        cls.cadet_role, _ = Role.objects.get_or_create(
            name="Cadet",
            defaults={"hierarchy_level": 1, "description": "Cadet role."},
        )
        cadet_review_perm = Permission.objects.get(
            content_type__app_label="cases",
            codename=CasesPerms.CAN_REVIEW_COMPLAINT,
        )
        cls.cadet_role.permissions.add(cadet_review_perm)

        # Officer role: approve officer_review -> open.
        cls.officer_role, _ = Role.objects.get_or_create(
            name="Police Officer",
            defaults={"hierarchy_level": 2, "description": "Officer role."},
        )
        officer_approve_perm = Permission.objects.get(
            content_type__app_label="cases",
            codename=CasesPerms.CAN_APPROVE_CASE,
        )
        cls.officer_role.permissions.add(officer_approve_perm)
        # Officer needs scope permission to view cases via detail endpoint
        officer_scope_perm = Permission.objects.get(
            content_type__app_label="cases",
            codename=CasesPerms.CAN_SCOPE_OFFICER_CASES,
        )
        cls.officer_role.permissions.add(officer_scope_perm)

        cls.complainant_password = "OfficerFlow!Pass41"
        cls.complainant = User.objects.create_user(
            username="officer_flow_complainant",
            password=cls.complainant_password,
            email="officer_flow_complainant@example.com",
            phone_number="09130000831",
            national_id="3200000831",
            first_name="OfficerFlow",
            last_name="Complainant",
            role=cls.base_role,
        )

        cls.cadet_password = "OfficerFlow!Pass42"
        cls.cadet_user = User.objects.create_user(
            username="officer_flow_cadet",
            password=cls.cadet_password,
            email="officer_flow_cadet@example.com",
            phone_number="09130000832",
            national_id="3200000832",
            first_name="OfficerFlow",
            last_name="Cadet",
            role=cls.cadet_role,
        )

        cls.officer_password = "OfficerFlow!Pass43"
        cls.officer_user = User.objects.create_user(
            username="officer_flow_officer",
            password=cls.officer_password,
            email="officer_flow_officer@example.com",
            phone_number="09130000833",
            national_id="3200000833",
            first_name="OfficerFlow",
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
        Build scenario chain via API:
        create complaint -> submit -> cadet approves complainant -> cadet approves case.
        """
        self.login_as(self.complainant, self.complainant_password)

        create_resp = self.client.post(
            self.case_create_url,
            {
                "creation_type": "complaint",
                "title": "Officer review arrangement case",
                "description": "Prepared for officer-approve integration tests.",
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

        review_complainant_url = reverse(
            "case-review-complainant",
            kwargs={"pk": case_id, "complainant_pk": complainant_id},
        )
        review_complainant_resp = self.client.post(
            review_complainant_url,
            {"decision": "approve"},
            format="json",
        )
        self.assertEqual(review_complainant_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            review_complainant_resp.data["status"],
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

    def test_officer_can_approve_case_and_transition_to_open(self):
        """
        Officer review approve must move officer_review -> open.
        """
        case_id = self.arrange_case_in_officer_review()
        self.login_as(self.officer_user, self.officer_password)

        officer_review_url = reverse("case-officer-review", kwargs={"pk": case_id})
        officer_review_resp = self.client.post(
            officer_review_url,
            {"decision": "approve"},
            format="json",
        )

        self.assertEqual(
            officer_review_resp.status_code,
            status.HTTP_200_OK,
            msg=f"Officer approve failed: {officer_review_resp.data}",
        )
        self.assertEqual(officer_review_resp.data["status"], CaseStatus.OPEN)
        self.assertEqual(officer_review_resp.data["approved_by"], self.officer_user.id)

        # Case detail endpoint should also show OPEN.
        case_detail_url = reverse("case-detail", kwargs={"pk": case_id})
        detail_resp = self.client.get(case_detail_url, format="json")
        self.assertEqual(detail_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_resp.data["status"], CaseStatus.OPEN)
        self.assertEqual(detail_resp.data["approved_by"], self.officer_user.id)

        # Status log should include latest officer transition.
        status_log_url = reverse("case-status-log", kwargs={"pk": case_id})
        status_log_resp = self.client.get(status_log_url, format="json")
        self.assertEqual(status_log_resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(status_log_resp.data), 4)

        latest = status_log_resp.data[0]
        self.assertEqual(latest["from_status"], CaseStatus.OFFICER_REVIEW)
        self.assertEqual(latest["to_status"], CaseStatus.OPEN)
        self.assertEqual(latest["changed_by"], self.officer_user.id)

        case = Case.objects.get(pk=case_id)
        self.assertEqual(case.status, CaseStatus.OPEN)
        self.assertEqual(case.approved_by_id, self.officer_user.id)

    def test_normal_user_cannot_call_officer_review_endpoint(self):
        """
        Normal complainant user must receive 403 on officer-review endpoint.
        """
        case_id = self.arrange_case_in_officer_review()
        self.login_as(self.complainant, self.complainant_password)

        officer_review_url = reverse("case-officer-review", kwargs={"pk": case_id})
        resp = self.client.post(
            officer_review_url,
            {"decision": "approve"},
            format="json",
        )

        self.assertEqual(
            resp.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=f"Expected 403 for non-officer review action. Body: {resp.data}",
        )

    def test_officer_approve_requires_officer_review_state(self):
        """
        Officer approve attempt on a non-officer_review case should be rejected.
        """
        # Arrange a case only up to cadet_review (no cadet case approval).
        self.login_as(self.complainant, self.complainant_password)
        create_resp = self.client.post(
            self.case_create_url,
            {
                "creation_type": "complaint",
                "title": "Invalid-state officer review test",
                "description": "Case is not yet in officer_review.",
                "crime_level": 1,
            },
            format="json",
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        case_id = create_resp.data["id"]

        submit_url = reverse("case-submit", kwargs={"pk": case_id})
        submit_resp = self.client.post(submit_url, format="json")
        self.assertEqual(submit_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(submit_resp.data["status"], CaseStatus.CADET_REVIEW)

        self.login_as(self.officer_user, self.officer_password)
        officer_review_url = reverse("case-officer-review", kwargs={"pk": case_id})
        resp = self.client.post(
            officer_review_url,
            {"decision": "approve"},
            format="json",
        )

        self.assertEqual(
            resp.status_code,
            status.HTTP_409_CONFLICT,
            msg=f"Invalid-state officer approve should return 409. Body: {resp.data}",
        )
