"""
Integration tests — Suspect workflow scenarios 7.1–7.6 (shared file).

This file currently implements Scenario 7.1:
Detective creates a suspect for a case, initial suspect status is "wanted",
and sergeant approval status is "pending".
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
from suspects.models import Suspect, SuspectStatus

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
    perm = Permission.objects.get(
        codename=codename,
        content_type__app_label=app_label,
    )
    role.permissions.add(perm)


class TestSuspectWorkflow(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Roles for scenario 7.x chain
        cls.detective_role = _make_role("Detective", hierarchy_level=7)
        cls.sergeant_role = _make_role("Sergeant", hierarchy_level=8)
        cls.captain_role = _make_role("Captain", hierarchy_level=9)
        cls.chief_role = _make_role("Police Chief", hierarchy_level=10)

        # Minimum permissions required for 7.1 endpoint interactions.
        _grant(cls.detective_role, "can_identify_suspect", "suspects")
        _grant(cls.detective_role, "add_suspect", "suspects")
        _grant(cls.detective_role, "view_suspect", "suspects")
        _grant(cls.sergeant_role, "can_approve_suspect", "suspects")

        _grant(cls.chief_role, "can_assign_detective", "cases")
        _grant(cls.chief_role, "view_case", "cases")

        cls.detective_password = "Det3ctive!Pass77"
        cls.sergeant_password = "Serg3ant!Pass77"
        cls.captain_password = "Capt@in!Pass77"
        cls.chief_password = "Ch!ef!Pass777"

        cls.detective_user = User.objects.create_user(
            username="suspect_det",
            password=cls.detective_password,
            email="suspect_det@lapd.test",
            phone_number="09133000001",
            national_id="3300000001",
            first_name="Cole",
            last_name="Phelps",
            role=cls.detective_role,
        )
        cls.sergeant_user = User.objects.create_user(
            username="suspect_sergeant",
            password=cls.sergeant_password,
            email="suspect_sergeant@lapd.test",
            phone_number="09133000002",
            national_id="3300000002",
            first_name="Nate",
            last_name="Sergeant",
            role=cls.sergeant_role,
        )
        cls.captain_user = User.objects.create_user(
            username="suspect_captain",
            password=cls.captain_password,
            email="suspect_captain@lapd.test",
            phone_number="09133000003",
            national_id="3300000003",
            first_name="Mina",
            last_name="Captain",
            role=cls.captain_role,
        )
        cls.chief_user = User.objects.create_user(
            username="suspect_chief",
            password=cls.chief_password,
            email="suspect_chief@lapd.test",
            phone_number="09133000004",
            national_id="3300000004",
            first_name="Lena",
            last_name="Chief",
            role=cls.chief_role,
        )

        # Start OPEN, then assign detective via API helper (assign endpoint moves to INVESTIGATION).
        cls.case = Case.objects.create(
            title="Scenario 7.1 Case",
            description="Fixture case for suspect creation workflow.",
            crime_level=CrimeLevel.LEVEL_2,
            creation_type=CaseCreationType.CRIME_SCENE,
            status=CaseStatus.OPEN,
            created_by=cls.chief_user,
            assigned_sergeant=cls.sergeant_user,
            assigned_captain=cls.captain_user,
        )

    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse("accounts:login")
        self.suspect_create_url = reverse("suspect-list")

    def login(self, user: User, password: str) -> str:
        response = self.client.post(
            self.login_url,
            {"identifier": user.username, "password": password},
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

    def create_case(self, *, status_value: str = CaseStatus.OPEN) -> Case:
        return Case.objects.create(
            title="Scenario 7.x Extra Case",
            description="Generated by test helper.",
            crime_level=CrimeLevel.LEVEL_2,
            creation_type=CaseCreationType.CRIME_SCENE,
            status=status_value,
            created_by=self.chief_user,
            assigned_sergeant=self.sergeant_user,
            assigned_captain=self.captain_user,
        )

    def assign_detective_to_case(self, case: Case) -> None:
        chief_token = self.login(self.chief_user, self.chief_password)
        self.auth(chief_token)
        assign_url = reverse("case-assign-detective", kwargs={"pk": case.pk})
        response = self.client.post(
            assign_url,
            {"user_id": self.detective_user.pk},
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Detective assignment failed: {response.data}",
        )
        case.refresh_from_db()
        self.assertEqual(case.assigned_detective_id, self.detective_user.id)
        self.assertEqual(case.status, CaseStatus.INVESTIGATION)

    def _suspect_payload(self, *, case_id: int, **overrides) -> dict:
        payload = {
            "case": case_id,
            "full_name": "Roy Earle",
            "national_id": "1234567890",
            "description": "Identified from crime-scene testimony.",
        }
        payload.update(overrides)
        return payload

    def create_suspect_as_detective(self, *, case: Case | None = None, **payload_overrides) -> dict:
        target_case = case or self.create_case()
        self.assign_detective_to_case(target_case)

        detective_token = self.login(self.detective_user, self.detective_password)
        self.auth(detective_token)

        payload = self._suspect_payload(case_id=target_case.id, **payload_overrides)
        response = self.client.post(self.suspect_create_url, payload, format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Suspect setup creation failed: {response.data}",
        )
        return response.data

    def test_detective_creates_suspect_successfully(self):
        self.assign_detective_to_case(self.case)

        detective_token = self.login(self.detective_user, self.detective_password)
        self.auth(detective_token)

        payload = self._suspect_payload(case_id=self.case.id)
        create_response = self.client.post(self.suspect_create_url, payload, format="json")

        self.assertEqual(
            create_response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Expected 201 creating suspect. Body: {create_response.data}",
        )
        self.assertIn("id", create_response.data)
        self.assertEqual(create_response.data["case"], self.case.id)
        self.assertEqual(create_response.data["status"], SuspectStatus.WANTED)
        self.assertEqual(create_response.data["sergeant_approval_status"], "pending")

        suspect_id = create_response.data["id"]
        detail_url = reverse("suspect-detail", kwargs={"pk": suspect_id})
        detail_response = self.client.get(detail_url, format="json")

        self.assertEqual(
            detail_response.status_code,
            status.HTTP_200_OK,
            msg=f"Expected 200 on suspect detail. Body: {detail_response.data}",
        )
        self.assertEqual(detail_response.data["id"], suspect_id)
        self.assertEqual(detail_response.data["case"], self.case.id)
        self.assertEqual(detail_response.data["full_name"], payload["full_name"])
        self.assertEqual(detail_response.data["national_id"], payload["national_id"])
        self.assertEqual(detail_response.data["description"], payload["description"])
        self.assertEqual(detail_response.data["status"], SuspectStatus.WANTED)
        self.assertEqual(detail_response.data["sergeant_approval_status"], "pending")

        suspect = Suspect.objects.get(pk=suspect_id)
        self.assertEqual(suspect.case_id, self.case.id)
        self.assertEqual(suspect.identified_by_id, self.detective_user.id)
        self.assertEqual(suspect.status, SuspectStatus.WANTED)
        self.assertEqual(suspect.sergeant_approval_status, "pending")

    def test_create_suspect_unauthenticated_returns_401(self):
        payload = self._suspect_payload(case_id=self.case.id, full_name="No Auth Suspect")
        response = self.client.post(self.suspect_create_url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
            msg=f"Expected 401 for unauthenticated suspect creation. Body: {response.data}",
        )

    def test_non_detective_cannot_create_suspect_returns_403(self):
        sergeant_token = self.login(self.sergeant_user, self.sergeant_password)
        self.auth(sergeant_token)

        payload = self._suspect_payload(case_id=self.case.id, full_name="Forbidden Actor")
        response = self.client.post(self.suspect_create_url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=f"Expected 403 for non-detective suspect creation. Body: {response.data}",
        )

    def test_create_suspect_invalid_national_id_returns_400(self):
        self.assign_detective_to_case(self.case)

        detective_token = self.login(self.detective_user, self.detective_password)
        self.auth(detective_token)

        payload = self._suspect_payload(
            case_id=self.case.id,
            national_id="12345678901",  # > 10 chars; fails serializer max_length.
        )
        response = self.client.post(self.suspect_create_url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Expected 400 for invalid national_id. Body: {response.data}",
        )
        self.assertIn("national_id", response.data)

    def test_sergeant_can_approve_suspect_successfully(self):
        suspect_data = self.create_suspect_as_detective()
        suspect_id = suspect_data["id"]

        sergeant_token = self.login(self.sergeant_user, self.sergeant_password)
        self.auth(sergeant_token)

        approve_url = reverse("suspect-approve", kwargs={"pk": suspect_id})
        response = self.client.post(approve_url, {"decision": "approve"}, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Expected 200 approving suspect. Body: {response.data}",
        )
        self.assertEqual(response.data["id"], suspect_id)
        self.assertEqual(response.data["sergeant_approval_status"], "approved")
        self.assertEqual(response.data["status"], SuspectStatus.WANTED)
        self.assertEqual(response.data["approved_by_sergeant"], self.sergeant_user.id)

        detail_url = reverse("suspect-detail", kwargs={"pk": suspect_id})
        detail_response = self.client.get(detail_url, format="json")
        self.assertEqual(
            detail_response.status_code,
            status.HTTP_200_OK,
            msg=f"Expected 200 for detail after approve. Body: {detail_response.data}",
        )
        self.assertEqual(detail_response.data["sergeant_approval_status"], "approved")
        self.assertEqual(detail_response.data["status"], SuspectStatus.WANTED)
        self.assertEqual(detail_response.data["approved_by_sergeant"], self.sergeant_user.id)

        suspect = Suspect.objects.get(pk=suspect_id)
        self.assertEqual(suspect.sergeant_approval_status, "approved")
        self.assertEqual(suspect.approved_by_sergeant_id, self.sergeant_user.id)
        self.assertEqual(suspect.status, SuspectStatus.WANTED)

    def test_sergeant_can_reject_suspect_with_message(self):
        suspect_data = self.create_suspect_as_detective(full_name="Rejectable Suspect")
        suspect_id = suspect_data["id"]
        rejection_message = "Insufficient evidence linking suspect to the scene."

        sergeant_token = self.login(self.sergeant_user, self.sergeant_password)
        self.auth(sergeant_token)

        approve_url = reverse("suspect-approve", kwargs={"pk": suspect_id})
        response = self.client.post(
            approve_url,
            {"decision": "reject", "rejection_message": rejection_message},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Expected 200 rejecting suspect. Body: {response.data}",
        )
        self.assertEqual(response.data["sergeant_approval_status"], "rejected")
        self.assertEqual(response.data["sergeant_rejection_message"], rejection_message)
        self.assertEqual(response.data["approved_by_sergeant"], self.sergeant_user.id)

        detail_url = reverse("suspect-detail", kwargs={"pk": suspect_id})
        detail_response = self.client.get(detail_url, format="json")
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["sergeant_approval_status"], "rejected")
        self.assertEqual(detail_response.data["sergeant_rejection_message"], rejection_message)

        suspect = Suspect.objects.get(pk=suspect_id)
        self.assertEqual(suspect.sergeant_approval_status, "rejected")
        self.assertEqual(suspect.sergeant_rejection_message, rejection_message)

    def test_non_sergeant_cannot_approve_or_reject_suspect(self):
        suspect_id = self.create_suspect_as_detective(full_name="Protected Suspect")["id"]
        approve_url = reverse("suspect-approve", kwargs={"pk": suspect_id})

        captain_token = self.login(self.captain_user, self.captain_password)
        self.auth(captain_token)

        for payload in (
            {"decision": "approve"},
            {"decision": "reject", "rejection_message": "Should be forbidden."},
        ):
            with self.subTest(payload=payload):
                response = self.client.post(approve_url, payload, format="json")
                self.assertEqual(
                    response.status_code,
                    status.HTTP_403_FORBIDDEN,
                    msg=f"Expected 403 for non-sergeant approval action. Body: {response.data}",
                )

    def test_sergeant_reject_without_message_returns_400(self):
        suspect_id = self.create_suspect_as_detective(full_name="Missing Message Suspect")["id"]

        sergeant_token = self.login(self.sergeant_user, self.sergeant_password)
        self.auth(sergeant_token)

        approve_url = reverse("suspect-approve", kwargs={"pk": suspect_id})
        response = self.client.post(
            approve_url,
            {"decision": "reject"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Expected 400 for reject without rejection_message. Body: {response.data}",
        )
        self.assertIn("rejection_message", response.data)

    def test_cannot_approve_already_processed_suspect(self):
        suspect_id = self.create_suspect_as_detective(full_name="Already Processed Suspect")["id"]

        sergeant_token = self.login(self.sergeant_user, self.sergeant_password)
        self.auth(sergeant_token)

        approve_url = reverse("suspect-approve", kwargs={"pk": suspect_id})
        first_response = self.client.post(
            approve_url,
            {"decision": "approve"},
            format="json",
        )
        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK,
            msg=f"Initial approval should succeed. Body: {first_response.data}",
        )

        second_response = self.client.post(
            approve_url,
            {"decision": "approve"},
            format="json",
        )
        self.assertIn(
            second_response.status_code,
            (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT),
            msg=f"Expected 400/409 for already-processed approval. Body: {second_response.data}",
        )
