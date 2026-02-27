"""
Integration tests for scenario 3.7: add complainant + cadet complainant review.

Reference docs:
- md-files/project-doc.md §4.2.1
  (cases can have multiple complainants; Cadet approves/rejects complainant info)
- md-files/24-swagger_documentation_report.md §3.2
  (POST /api/cases/{id}/complainants/, POST /api/cases/{id}/review-complainant/)
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role
from cases.models import CaseComplainant, CaseStatus, ComplainantStatus
from core.permissions_constants import CasesPerms

User = get_user_model()


class TestAddComplainantAndCadetReviewFlow(TestCase):
    """
    Scenario 3.7 tests executed through real HTTP endpoints only.
    """

    @classmethod
    def setUpTestData(cls):
        # Base users can create and submit complaint cases.
        cls.base_role, _ = Role.objects.get_or_create(
            name="Base User",
            defaults={"hierarchy_level": 0, "description": "Default user role."},
        )
        add_case_perm = Permission.objects.get(
            content_type__app_label="cases",
            codename=CasesPerms.ADD_CASE,
        )
        cls.base_role.permissions.add(add_case_perm)

        # Cadet can add complainants and review complainants.
        cls.cadet_role, _ = Role.objects.get_or_create(
            name="Cadet",
            defaults={"hierarchy_level": 1, "description": "Cadet role."},
        )
        add_complainant_perm = Permission.objects.get(
            content_type__app_label="cases",
            codename=CasesPerms.ADD_CASECOMPLAINANT,
        )
        review_complainant_perm = Permission.objects.get(
            content_type__app_label="cases",
            codename=CasesPerms.CAN_REVIEW_COMPLAINT,
        )
        cls.cadet_role.permissions.add(add_complainant_perm, review_complainant_perm)

        cls.user_a_password = "AddComp!Pass41"
        cls.user_a = User.objects.create_user(
            username="add_comp_user_a",
            password=cls.user_a_password,
            email="add_comp_user_a@example.com",
            phone_number="09130001141",
            national_id="3200001141",
            first_name="AddComp",
            last_name="UserA",
            role=cls.base_role,
        )

        cls.user_b_password = "AddComp!Pass42"
        cls.user_b = User.objects.create_user(
            username="add_comp_user_b",
            password=cls.user_b_password,
            email="add_comp_user_b@example.com",
            phone_number="09130001142",
            national_id="3200001142",
            first_name="AddComp",
            last_name="UserB",
            role=cls.base_role,
        )

        cls.cadet_password = "AddComp!Pass43"
        cls.cadet_user = User.objects.create_user(
            username="add_comp_cadet",
            password=cls.cadet_password,
            email="add_comp_cadet@example.com",
            phone_number="09130001143",
            national_id="3200001143",
            first_name="AddComp",
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

    def arrange_case_in_cadet_review(self) -> int:
        """
        Create complaint case as user A and submit it to cadet_review.
        """
        self.login_as(self.user_a, self.user_a_password)

        create_resp = self.client.post(
            self.case_create_url,
            {
                "creation_type": "complaint",
                "title": "Add complainant arrangement case",
                "description": "Prepared for add-complainant workflow tests.",
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

        return case_id

    def test_cadet_can_add_additional_complainant_to_case(self):
        """
        POST /api/cases/{id}/complainants/ should add user B as non-primary complainant.
        """
        case_id = self.arrange_case_in_cadet_review()
        self.login_as(self.cadet_user, self.cadet_password)

        add_url = reverse("case-complainants", kwargs={"pk": case_id})
        add_resp = self.client.post(
            add_url,
            {"user_id": self.user_b.id},
            format="json",
        )

        self.assertEqual(
            add_resp.status_code,
            status.HTTP_201_CREATED,
            msg=f"Add complainant failed: {add_resp.data}",
        )
        self.assertIn("id", add_resp.data)
        self.assertEqual(add_resp.data["user"], self.user_b.id)
        self.assertFalse(add_resp.data["is_primary"])
        self.assertEqual(add_resp.data["status"], ComplainantStatus.PENDING)

        link = CaseComplainant.objects.get(pk=add_resp.data["id"])
        self.assertEqual(link.user_id, self.user_b.id)
        self.assertFalse(link.is_primary)

    def test_cadet_can_approve_newly_added_complainant(self):
        """
        Cadet can review/approve the added complainant via review endpoint.
        """
        case_id = self.arrange_case_in_cadet_review()
        self.login_as(self.cadet_user, self.cadet_password)

        add_url = reverse("case-complainants", kwargs={"pk": case_id})
        add_resp = self.client.post(add_url, {"user_id": self.user_b.id}, format="json")
        self.assertEqual(add_resp.status_code, status.HTTP_201_CREATED)
        complainant_id = add_resp.data["id"]

        review_url = reverse(
            "case-review-complainant",
            kwargs={"pk": case_id, "complainant_pk": complainant_id},
        )
        review_resp = self.client.post(review_url, {"decision": "approve"}, format="json")

        self.assertEqual(
            review_resp.status_code,
            status.HTTP_200_OK,
            msg=f"Complainant review failed: {review_resp.data}",
        )
        self.assertEqual(review_resp.data["status"], ComplainantStatus.APPROVED)
        self.assertEqual(review_resp.data["reviewed_by"], self.cadet_user.id)

        link = CaseComplainant.objects.get(pk=complainant_id)
        self.assertEqual(link.status, ComplainantStatus.APPROVED)
        self.assertEqual(link.reviewed_by_id, self.cadet_user.id)

    def test_unauthorized_user_cannot_add_complainant(self):
        """
        User A (base user) must not be able to add additional complainants.
        """
        case_id = self.arrange_case_in_cadet_review()
        self.login_as(self.user_a, self.user_a_password)

        add_url = reverse("case-complainants", kwargs={"pk": case_id})
        resp = self.client.post(add_url, {"user_id": self.user_b.id}, format="json")

        self.assertEqual(
            resp.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=f"Unauthorized add should return 403. Body: {resp.data}",
        )

    def test_non_cadet_cannot_review_complainant(self):
        """
        User A (non-cadet) must not be able to review complainants.
        """
        case_id = self.arrange_case_in_cadet_review()
        self.login_as(self.cadet_user, self.cadet_password)

        add_url = reverse("case-complainants", kwargs={"pk": case_id})
        add_resp = self.client.post(add_url, {"user_id": self.user_b.id}, format="json")
        self.assertEqual(add_resp.status_code, status.HTTP_201_CREATED)
        complainant_id = add_resp.data["id"]

        self.login_as(self.user_a, self.user_a_password)
        review_url = reverse(
            "case-review-complainant",
            kwargs={"pk": case_id, "complainant_pk": complainant_id},
        )
        resp = self.client.post(review_url, {"decision": "approve"}, format="json")

        self.assertEqual(
            resp.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=f"Non-cadet review should return 403. Body: {resp.data}",
        )

    def test_cannot_add_same_complainant_twice(self):
        """
        Adding the same user twice to one case should fail (DomainError -> 400).
        """
        case_id = self.arrange_case_in_cadet_review()
        self.login_as(self.cadet_user, self.cadet_password)

        add_url = reverse("case-complainants", kwargs={"pk": case_id})
        first = self.client.post(add_url, {"user_id": self.user_b.id}, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        second = self.client.post(add_url, {"user_id": self.user_b.id}, format="json")
        self.assertEqual(
            second.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Duplicate complainant add should fail. Body: {second.data}",
        )
