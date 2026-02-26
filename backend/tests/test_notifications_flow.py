from __future__ import annotations

from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role
from cases.models import Case, CaseCreationType, CaseStatus, CrimeLevel

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


class TestNotificationsFlow(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.detective_role = _make_role("Detective", 7)
        cls.officer_role = _make_role("Police Officer", 6)
        cls.coroner_role = _make_role("Coroner", 3)
        cls.sergeant_role = _make_role("Sergeant", 8)
        cls.base_role = _make_role("Base User", 0)

        for codename in ("add_evidence", "add_biologicalevidence", "add_evidencefile"):
            _grant(cls.officer_role, codename, "evidence")
        _grant(cls.coroner_role, "can_verify_evidence", "evidence")
        _grant(cls.sergeant_role, "can_assign_detective", "cases")
        # Detective must be assignable (permission-based RBAC)
        _grant(cls.detective_role, "can_be_assigned_detective", "cases")

        cls.passwords = {
            "detective": "D3tective!NFlow1",
            "officer": "0fficer!NFlow2",
            "coroner": "C0roner!NFlow3",
            "sergeant": "S3rgeant!NFlow4",
            "other": "0ther!NFlow5",
        }

        cls.detective_user = User.objects.create_user(
            username="notif_detective",
            password=cls.passwords["detective"],
            email="notif_detective@lapd.test",
            phone_number="09141111001",
            national_id="4111110001",
            first_name="Cole",
            last_name="Phelps",
            role=cls.detective_role,
        )
        cls.officer_user = User.objects.create_user(
            username="notif_officer",
            password=cls.passwords["officer"],
            email="notif_officer@lapd.test",
            phone_number="09141111002",
            national_id="4111110002",
            first_name="Ralph",
            last_name="Dunn",
            role=cls.officer_role,
        )
        cls.coroner_user = User.objects.create_user(
            username="notif_coroner",
            password=cls.passwords["coroner"],
            email="notif_coroner@lapd.test",
            phone_number="09141111003",
            national_id="4111110003",
            first_name="Stefan",
            last_name="Bekowsky",
            role=cls.coroner_role,
        )
        cls.sergeant_user = User.objects.create_user(
            username="notif_sergeant",
            password=cls.passwords["sergeant"],
            email="notif_sergeant@lapd.test",
            phone_number="09141111004",
            national_id="4111110004",
            first_name="Rusty",
            last_name="Galloway",
            role=cls.sergeant_role,
        )
        cls.other_user = User.objects.create_user(
            username="notif_other_user",
            password=cls.passwords["other"],
            email="notif_other@lapd.test",
            phone_number="09141111005",
            national_id="4111110005",
            first_name="Una",
            last_name="Related",
            role=cls.base_role,
        )

        cls.case = Case.objects.create(
            title="Notification Scenario 13.1 Case",
            description="Open case fixture used for notification flow tests.",
            crime_level=CrimeLevel.LEVEL_2,
            creation_type=CaseCreationType.CRIME_SCENE,
            status=CaseStatus.OPEN,
            created_by=cls.officer_user,
            assigned_detective=None,
        )

    def setUp(self) -> None:
        self.client = APIClient()
        self.login_url = reverse("accounts:login")
        self.evidence_url = reverse("evidence-list")
        self.notifications_url = reverse("core:notification-list")

    def login(self, user: User) -> str:
        password = {
            self.detective_user.username: self.passwords["detective"],
            self.officer_user.username: self.passwords["officer"],
            self.coroner_user.username: self.passwords["coroner"],
            self.sergeant_user.username: self.passwords["sergeant"],
            self.other_user.username: self.passwords["other"],
        }[user.username]

        response = self.client.post(
            self.login_url,
            {"identifier": user.username, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)
        return response.data["access"]

    def auth(self, token: str) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _extract_notifications(self, payload: object) -> list[dict]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and isinstance(payload.get("results"), list):
            return payload["results"]
        self.fail(f"Unexpected notifications payload shape: {payload!r}")

    def create_biological_evidence(self, case_id: int) -> dict:
        payload = {
            "evidence_type": "biological",
            "case": case_id,
            "title": f"Bio-{uuid4().hex[:8]}",
            "description": "Biological sample from crime scene for forensic review.",
        }
        response = self.client.post(self.evidence_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.data)
        return response.data

    def upload_file_to_evidence(self, evidence_id: int) -> dict:
        upload = SimpleUploadedFile(
            name=f"bio_{uuid4().hex[:8]}.jpg",
            content=b"\xff\xd8\xff\xe0fake-jpeg-content",
            content_type="image/jpeg",
        )
        response = self.client.post(
            reverse("evidence-files", kwargs={"pk": evidence_id}),
            {"file": upload, "file_type": "image", "caption": "Blood sample image"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.data)
        return response.data

    def verify_biological_evidence(self, evidence_id: int, decision: str) -> dict:
        payload = {"decision": decision}
        if decision == "approve":
            payload["forensic_result"] = "DNA profile matched to known suspect sample."
        else:
            payload["notes"] = "Insufficient sample quality."

        response = self.client.post(
            reverse("evidence-verify", kwargs={"pk": evidence_id}),
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)
        return response.data

    def get_notifications(self, expected_status: int = status.HTTP_200_OK):
        response = self.client.get(self.notifications_url, format="json")
        self.assertEqual(response.status_code, expected_status, msg=getattr(response, "data", response.content))
        return response

    def mark_notification_read(self, notification_id: int):
        return self.client.post(
            reverse("core:notification-mark-as-read", kwargs={"pk": notification_id}),
            {},
            format="json",
        )

    def _assign_detective(self) -> None:
        response = self.client.post(
            reverse("case-assign-detective", kwargs={"pk": self.case.pk}),
            {"user_id": self.detective_user.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)

    def _trigger_bio_approval_and_get_notification(self) -> dict:
        self.auth(self.login(self.officer_user))
        evidence = self.create_biological_evidence(case_id=self.case.pk)
        self.upload_file_to_evidence(evidence["id"])

        self.auth(self.login(self.sergeant_user))
        self._assign_detective()

        self.auth(self.login(self.detective_user))
        before_response = self.get_notifications()
        before_notifications = self._extract_notifications(before_response.data)
        before_ids = {item["id"] for item in before_notifications}

        self.auth(self.login(self.coroner_user))
        self.verify_biological_evidence(evidence["id"], decision="approve")

        self.auth(self.login(self.detective_user))
        after_response = self.get_notifications()
        after_notifications = self._extract_notifications(after_response.data)
        new_notifications = [item for item in after_notifications if item["id"] not in before_ids]

        matching = [
            item
            for item in new_notifications
            if item.get("title") == "Biological Evidence Verified"
            and item.get("object_id") == evidence["id"]
        ]
        self.assertTrue(
            matching,
            msg=f"No new biological verification notification found. New notifications: {new_notifications}",
        )
        return matching[0]

    def test_notification_created_after_biological_approve(self) -> None:
        notification = self._trigger_bio_approval_and_get_notification()

        self.assertIn("id", notification)
        self.assertIn("created_at", notification)
        self.assertTrue(notification["created_at"])
        self.assertIn("content_type", notification)
        self.assertIn("object_id", notification)
        self.assertFalse(notification["is_read"])

    def test_mark_notification_as_read(self) -> None:
        notification = self._trigger_bio_approval_and_get_notification()

        self.auth(self.login(self.detective_user))
        mark_response = self.mark_notification_read(notification["id"])
        self.assertIn(
            mark_response.status_code,
            (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT),
            msg=getattr(mark_response, "data", mark_response.content),
        )

        refreshed = self._extract_notifications(self.get_notifications().data)
        by_id = {item["id"]: item for item in refreshed}
        self.assertIn(notification["id"], by_id)
        self.assertTrue(by_id[notification["id"]]["is_read"])

    def test_notifications_require_authentication(self) -> None:
        self.client.credentials()
        self.get_notifications(expected_status=status.HTTP_401_UNAUTHORIZED)

    def test_unrelated_user_cannot_see_detective_notification(self) -> None:
        detective_notification = self._trigger_bio_approval_and_get_notification()

        self.auth(self.login(self.other_user))
        other_notifications = self._extract_notifications(self.get_notifications().data)
        other_notification_ids = {item["id"] for item in other_notifications}
        self.assertNotIn(detective_notification["id"], other_notification_ids)
