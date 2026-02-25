"""
Integration tests — Bounty Tips flow scenarios 10.1–10.4 (shared file).

Current scope in this file:
- Scenario 10.1: Citizen submits a bounty tip.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role
from cases.models import Case, CaseCreationType, CaseStatus, CrimeLevel
from suspects.models import BountyTip, Suspect, SuspectStatus

User = get_user_model()


def _make_role(name: str, hierarchy_level: int) -> Role:
    role, _ = Role.objects.get_or_create(
        name=name,
        defaults={
            "description": f"Test role: {name}",
            "hierarchy_level": hierarchy_level,
        },
    )
    return role


def _grant(role: Role, codename: str, app_label: str) -> None:
    permission = Permission.objects.get(
        codename=codename,
        content_type__app_label=app_label,
    )
    role.permissions.add(permission)


class TestBountyTipsFlow(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.citizen_role = _make_role("Base User", hierarchy_level=0)
        cls.officer_role = _make_role("Police Officer", hierarchy_level=6)
        cls.detective_role = _make_role("Detective", hierarchy_level=7)

        _grant(cls.officer_role, "can_review_bounty_tip", "suspects")
        _grant(cls.detective_role, "can_verify_bounty_tip", "suspects")

        cls.citizen_password = "Citizen!Pass101"
        cls.officer_password = "Officer!Pass101"
        cls.detective_password = "Detective!Pass101"

        cls.citizen_user = User.objects.create_user(
            username="bounty_citizen",
            password=cls.citizen_password,
            email="bounty_citizen@lapd.test",
            phone_number="09171000001",
            national_id="7100000001",
            first_name="Nora",
            last_name="Citizen",
            role=cls.citizen_role,
        )
        cls.officer_user = User.objects.create_user(
            username="bounty_officer",
            password=cls.officer_password,
            email="bounty_officer@lapd.test",
            phone_number="09171000002",
            national_id="7100000002",
            first_name="Ian",
            last_name="Officer",
            role=cls.officer_role,
        )
        cls.detective_user = User.objects.create_user(
            username="bounty_detective",
            password=cls.detective_password,
            email="bounty_detective@lapd.test",
            phone_number="09171000003",
            national_id="7100000003",
            first_name="Lea",
            last_name="Detective",
            role=cls.detective_role,
        )

        cls.open_case = Case.objects.create(
            title="Scenario 10.1 Open Case",
            description="Open case fixture for bounty-tip submission.",
            crime_level=CrimeLevel.LEVEL_2,
            creation_type=CaseCreationType.CRIME_SCENE,
            status=CaseStatus.OPEN,
            created_by=cls.officer_user,
            assigned_detective=cls.detective_user,
        )
        cls.closed_case = Case.objects.create(
            title="Scenario 10.1 Closed Case",
            description="Closed case fixture for negative validation.",
            crime_level=CrimeLevel.LEVEL_2,
            creation_type=CaseCreationType.CRIME_SCENE,
            status=CaseStatus.CLOSED,
            created_by=cls.officer_user,
            assigned_detective=cls.detective_user,
        )

        cls.wanted_suspect = Suspect.objects.create(
            case=cls.open_case,
            full_name="Roy Bounty",
            national_id="8100000001",
            phone_number="09172000001",
            description="Wanted suspect for bounty tip tests.",
            status=SuspectStatus.WANTED,
            identified_by=cls.detective_user,
            sergeant_approval_status="approved",
        )
        cls.closed_case_suspect = Suspect.objects.create(
            case=cls.closed_case,
            full_name="Closed Case Suspect",
            national_id="8100000002",
            phone_number="09172000002",
            description="Suspect attached to a closed case.",
            status=SuspectStatus.WANTED,
            identified_by=cls.detective_user,
            sergeant_approval_status="approved",
        )

        cls.password_by_username = {
            cls.citizen_user.username: cls.citizen_password,
            cls.officer_user.username: cls.officer_password,
            cls.detective_user.username: cls.detective_password,
        }

    def setUp(self):
        self.client = APIClient()

    def login(self, user: User) -> str:
        response = self.client.post(
            reverse("accounts:login"),
            {
                "identifier": user.username,
                "password": self.password_by_username[user.username],
            },
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Login failed for {user.username}: {response.data}",
        )
        return response.data["access"]

    def auth(self, token: str) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def create_bounty_tip_via_api(
        self,
        *,
        suspect_id: int,
        case_id: int,
        information: str,
    ) -> int:
        response = self.client.post(
            reverse("bounty-tip-list"),
            {
                "suspect": suspect_id,
                "case": case_id,
                "information": information,
            },
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Tip creation failed: {response.data}",
        )
        return response.data["id"]

    def create_tip_as_citizen(
        self,
        *,
        information: str = "Citizen tip for officer review scenario.",
    ) -> int:
        token = self.login(self.citizen_user)
        self.auth(token)
        return self.create_bounty_tip_via_api(
            suspect_id=self.wanted_suspect.id,
            case_id=self.open_case.id,
            information=information,
        )

    def review_tip(
        self,
        *,
        tip_id: int,
        decision: str,
        review_notes: str | None = None,
    ):
        payload = {"decision": decision}
        if review_notes is not None:
            payload["review_notes"] = review_notes
        return self.client.post(
            reverse("bounty-tip-review", kwargs={"pk": tip_id}),
            payload,
            format="json",
        )

    def test_citizen_submits_tip_successfully_with_pending_status_and_no_unique_code(self):
        token = self.login(self.citizen_user)
        self.auth(token)

        tip_id = self.create_bounty_tip_via_api(
            suspect_id=self.wanted_suspect.id,
            case_id=self.open_case.id,
            information="I saw the suspect near 5th Avenue around 3 AM.",
        )

        tip = BountyTip.objects.get(pk=tip_id)
        self.assertEqual(tip.suspect_id, self.wanted_suspect.id)
        self.assertEqual(tip.case_id, self.open_case.id)
        self.assertEqual(tip.status, "pending")
        self.assertIsNone(tip.unique_code)

        detail_response = self.client.get(
            reverse("bounty-tip-detail", kwargs={"pk": tip_id}),
            format="json",
        )
        self.assertEqual(
            detail_response.status_code,
            status.HTTP_200_OK,
            msg=f"Tip detail failed: {detail_response.data}",
        )
        self.assertEqual(detail_response.data["id"], tip_id)
        self.assertEqual(detail_response.data["suspect"], self.wanted_suspect.id)
        self.assertEqual(detail_response.data["case"], self.open_case.id)
        self.assertEqual(detail_response.data["status"], "pending")
        self.assertIn(detail_response.data["unique_code"], (None, ""))

    def test_unauthenticated_citizen_cannot_submit_tip(self):
        response = self.client.post(
            reverse("bounty-tip-list"),
            {
                "suspect": self.wanted_suspect.id,
                "case": self.open_case.id,
                "information": "Anonymous tip should be rejected.",
            },
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
            msg=f"Expected 401 for unauthenticated submission: {response.data}",
        )

    def test_submit_tip_missing_required_information_returns_400(self):
        token = self.login(self.citizen_user)
        self.auth(token)

        response = self.client.post(
            reverse("bounty-tip-list"),
            {
                "suspect": self.wanted_suspect.id,
                "case": self.open_case.id,
            },
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Expected 400 for missing information: {response.data}",
        )
        self.assertIn("information", response.data)

    def test_submit_tip_for_closed_case_is_rejected(self):
        token = self.login(self.citizen_user)
        self.auth(token)

        response = self.client.post(
            reverse("bounty-tip-list"),
            {
                "suspect": self.closed_case_suspect.id,
                "case": self.closed_case.id,
                "information": "Tip for a closed case should not be accepted.",
            },
            format="json",
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT),
            msg=f"Expected rejection for closed-case bounty tip: {response.data}",
        )

    def test_officer_accepts_pending_tip_successfully(self):
        tip_id = self.create_tip_as_citizen(
            information="Accept path: suspect seen near the bus terminal.",
        )

        officer_token = self.login(self.officer_user)
        self.auth(officer_token)
        response = self.review_tip(
            tip_id=tip_id,
            decision="accept",
            review_notes="Preliminary review complete; forwarded to detective.",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Officer accept review failed: {response.data}",
        )
        self.assertEqual(response.data["status"], "officer_reviewed")
        self.assertEqual(response.data["reviewed_by"], self.officer_user.id)
        if "reviewed_at" in response.data:
            self.assertIsNotNone(response.data["reviewed_at"])

        tip = BountyTip.objects.get(pk=tip_id)
        self.assertEqual(tip.status, "officer_reviewed")
        self.assertEqual(tip.reviewed_by_id, self.officer_user.id)

        detail_response = self.client.get(
            reverse("bounty-tip-detail", kwargs={"pk": tip_id}),
            format="json",
        )
        self.assertEqual(
            detail_response.status_code,
            status.HTTP_200_OK,
            msg=f"Tip detail after accept failed: {detail_response.data}",
        )
        self.assertEqual(detail_response.data["status"], "officer_reviewed")
        self.assertEqual(detail_response.data["reviewed_by"], self.officer_user.id)

    def test_officer_rejects_pending_tip_successfully(self):
        rejection_notes = "Information is inconsistent with current case facts."
        tip_id = self.create_tip_as_citizen(
            information="Reject path: conflicting location/time details.",
        )

        officer_token = self.login(self.officer_user)
        self.auth(officer_token)
        response = self.review_tip(
            tip_id=tip_id,
            decision="reject",
            review_notes=rejection_notes,
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Officer reject review failed: {response.data}",
        )
        self.assertEqual(response.data["status"], "rejected")
        self.assertEqual(response.data["reviewed_by"], self.officer_user.id)
        if "review_notes" in response.data:
            self.assertEqual(response.data["review_notes"], rejection_notes)
        if "reviewed_at" in response.data:
            self.assertIsNotNone(response.data["reviewed_at"])

        tip = BountyTip.objects.get(pk=tip_id)
        self.assertEqual(tip.status, "rejected")
        self.assertEqual(tip.reviewed_by_id, self.officer_user.id)

        detail_response = self.client.get(
            reverse("bounty-tip-detail", kwargs={"pk": tip_id}),
            format="json",
        )
        self.assertEqual(
            detail_response.status_code,
            status.HTTP_200_OK,
            msg=f"Tip detail after reject failed: {detail_response.data}",
        )
        self.assertEqual(detail_response.data["status"], "rejected")
        self.assertEqual(detail_response.data["reviewed_by"], self.officer_user.id)
        if "review_notes" in detail_response.data:
            self.assertEqual(detail_response.data["review_notes"], rejection_notes)

    def test_non_officer_cannot_review_tip(self):
        tip_id = self.create_tip_as_citizen(
            information="Non-officer review permission guard.",
        )

        detective_token = self.login(self.detective_user)
        self.auth(detective_token)
        response = self.review_tip(
            tip_id=tip_id,
            decision="accept",
            review_notes="I am not an officer reviewer.",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=f"Non-officer review should be forbidden: {response.data}",
        )

    def test_reject_without_required_review_notes_returns_400(self):
        tip_id = self.create_tip_as_citizen(
            information="Reject without notes should fail validation.",
        )

        officer_token = self.login(self.officer_user)
        self.auth(officer_token)
        response = self.review_tip(
            tip_id=tip_id,
            decision="reject",
            review_notes="",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Expected 400 when reject has no review_notes: {response.data}",
        )
        self.assertIn("review_notes", response.data)

    def test_review_non_pending_tip_returns_409_or_400(self):
        tip_id = self.create_tip_as_citizen(
            information="Second review should be blocked.",
        )

        officer_token = self.login(self.officer_user)
        self.auth(officer_token)
        first_review = self.review_tip(
            tip_id=tip_id,
            decision="accept",
            review_notes="Initial officer acceptance.",
        )
        self.assertEqual(
            first_review.status_code,
            status.HTTP_200_OK,
            msg=f"Initial review setup failed: {first_review.data}",
        )

        second_review = self.review_tip(
            tip_id=tip_id,
            decision="reject",
            review_notes="Second review attempt must fail.",
        )
        self.assertIn(
            second_review.status_code,
            (status.HTTP_409_CONFLICT, status.HTTP_400_BAD_REQUEST),
            msg=f"Expected rejection for non-pending review: {second_review.data}",
        )
