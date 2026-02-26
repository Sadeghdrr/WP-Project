"""
Integration tests — Bail flow scenario 11.1.
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
from suspects.models import Bail, Suspect, SuspectStatus

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


class TestBailFlow(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sergeant_role = _make_role("Sergeant", hierarchy_level=8)
        cls.officer_role = _make_role("Police Officer", hierarchy_level=6)
        cls.detective_role = _make_role("Detective", hierarchy_level=7)

        _grant(cls.sergeant_role, "can_set_bail_amount", "suspects")
        _grant(cls.sergeant_role, "can_scope_supervised_suspects", "suspects")

        cls.sergeant_password = "Serg3ant!Bail11"
        cls.officer_password = "Officer!Bail11"
        cls.detective_password = "Detective!Bail11"

        cls.sergeant_user = User.objects.create_user(
            username="bail_sergeant",
            password=cls.sergeant_password,
            email="bail_sergeant@lapd.test",
            phone_number="09176000001",
            national_id="7600000001",
            first_name="Sam",
            last_name="Sergeant",
            role=cls.sergeant_role,
        )
        cls.officer_user = User.objects.create_user(
            username="bail_officer",
            password=cls.officer_password,
            email="bail_officer@lapd.test",
            phone_number="09176000002",
            national_id="7600000002",
            first_name="Owen",
            last_name="Officer",
            role=cls.officer_role,
        )
        cls.detective_user = User.objects.create_user(
            username="bail_detective",
            password=cls.detective_password,
            email="bail_detective@lapd.test",
            phone_number="09176000003",
            national_id="7600000003",
            first_name="Dana",
            last_name="Detective",
            role=cls.detective_role,
        )

        cls.case_l2 = Case.objects.create(
            title="Scenario 11.1 Level 2 Case",
            description="Fixture case for level-2 bail checks.",
            crime_level=CrimeLevel.LEVEL_2,
            creation_type=CaseCreationType.CRIME_SCENE,
            status=CaseStatus.OPEN,
            created_by=cls.sergeant_user,
            assigned_sergeant=cls.sergeant_user,
            assigned_detective=cls.detective_user,
        )
        cls.case_l3 = Case.objects.create(
            title="Scenario 11.1 Level 3 Case",
            description="Fixture case for level-3 bail checks.",
            crime_level=CrimeLevel.LEVEL_3,
            creation_type=CaseCreationType.CRIME_SCENE,
            status=CaseStatus.OPEN,
            created_by=cls.sergeant_user,
            assigned_sergeant=cls.sergeant_user,
            assigned_detective=cls.detective_user,
        )
        cls.case_l1 = Case.objects.create(
            title="Scenario 11.1 Level 1 Case",
            description="Fixture case for disallowed level-1 bail checks.",
            crime_level=CrimeLevel.LEVEL_1,
            creation_type=CaseCreationType.CRIME_SCENE,
            status=CaseStatus.OPEN,
            created_by=cls.sergeant_user,
            assigned_sergeant=cls.sergeant_user,
            assigned_detective=cls.detective_user,
        )
        cls.case_critical = Case.objects.create(
            title="Scenario 11.1 Critical Case",
            description="Fixture case for disallowed critical-level bail checks.",
            crime_level=CrimeLevel.CRITICAL,
            creation_type=CaseCreationType.CRIME_SCENE,
            status=CaseStatus.OPEN,
            created_by=cls.sergeant_user,
            assigned_sergeant=cls.sergeant_user,
            assigned_detective=cls.detective_user,
        )

        cls.l2_arrested_suspect = Suspect.objects.create(
            case=cls.case_l2,
            full_name="L2 Arrested Suspect",
            national_id="8610000001",
            phone_number="09177000001",
            description="Level 2 suspect in arrested status.",
            status=SuspectStatus.ARRESTED,
            identified_by=cls.detective_user,
            sergeant_approval_status="approved",
        )
        cls.l2_convicted_suspect = Suspect.objects.create(
            case=cls.case_l2,
            full_name="L2 Convicted Suspect",
            national_id="8610000002",
            phone_number="09177000002",
            description="Level 2 suspect in invalid convicted status for bail.",
            status=SuspectStatus.CONVICTED,
            identified_by=cls.detective_user,
            sergeant_approval_status="approved",
        )
        cls.l3_arrested_suspect = Suspect.objects.create(
            case=cls.case_l3,
            full_name="L3 Arrested Suspect",
            national_id="8610000003",
            phone_number="09177000003",
            description="Level 3 suspect in arrested status.",
            status=SuspectStatus.ARRESTED,
            identified_by=cls.detective_user,
            sergeant_approval_status="approved",
        )
        # No dedicated API transition exists in swagger to quickly seed a
        # convicted suspect for this isolated bail scenario, so we fixture it.
        cls.l3_convicted_suspect = Suspect.objects.create(
            case=cls.case_l3,
            full_name="L3 Convicted Suspect",
            national_id="8610000004",
            phone_number="09177000004",
            description="Level 3 suspect in convicted status.",
            status=SuspectStatus.CONVICTED,
            identified_by=cls.detective_user,
            sergeant_approval_status="approved",
        )
        cls.l1_arrested_suspect = Suspect.objects.create(
            case=cls.case_l1,
            full_name="L1 Arrested Suspect",
            national_id="8610000005",
            phone_number="09177000005",
            description="Level 1 arrested suspect for negative bail tests.",
            status=SuspectStatus.ARRESTED,
            identified_by=cls.detective_user,
            sergeant_approval_status="approved",
        )
        cls.critical_arrested_suspect = Suspect.objects.create(
            case=cls.case_critical,
            full_name="Critical Arrested Suspect",
            national_id="8610000006",
            phone_number="09177000006",
            description="Critical-level arrested suspect for negative bail tests.",
            status=SuspectStatus.ARRESTED,
            identified_by=cls.detective_user,
            sergeant_approval_status="approved",
        )

        cls.password_by_username = {
            cls.sergeant_user.username: cls.sergeant_password,
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

    def create_bail(self, *, suspect_id: int, payload: dict):
        return self.client.post(
            reverse("suspect-bail-list", kwargs={"suspect_pk": suspect_id}),
            payload,
            format="json",
        )

    def test_sergeant_can_create_bail_for_level_2_arrested_suspect(self):
        token = self.login(self.sergeant_user)
        self.auth(token)

        payload = {
            "amount": 50000000,
            "conditions": "Weekly station check-in for 8 weeks.",
        }
        response = self.create_bail(
            suspect_id=self.l2_arrested_suspect.id,
            payload=payload,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.data)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["suspect"], self.l2_arrested_suspect.id)
        self.assertEqual(response.data["case"], self.case_l2.id)
        self.assertEqual(int(response.data["amount"]), payload["amount"])
        self.assertEqual(response.data["conditions"], payload["conditions"])
        self.assertFalse(response.data["is_paid"])

        bail_id = response.data["id"]
        detail_response = self.client.get(
            reverse(
                "suspect-bail-detail",
                kwargs={"suspect_pk": self.l2_arrested_suspect.id, "pk": bail_id},
            )
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK, msg=detail_response.data)
        self.assertEqual(detail_response.data["id"], bail_id)
        self.assertEqual(detail_response.data["suspect"], self.l2_arrested_suspect.id)
        self.assertEqual(detail_response.data["case"], self.case_l2.id)
        self.assertFalse(detail_response.data["is_paid"])

    def test_sergeant_can_create_bail_for_level_3_arrested_suspect(self):
        token = self.login(self.sergeant_user)
        self.auth(token)

        response = self.create_bail(
            suspect_id=self.l3_arrested_suspect.id,
            payload={
                "amount": 51000000,
                "conditions": "No travel outside city limits.",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.data)
        self.assertEqual(response.data["suspect"], self.l3_arrested_suspect.id)
        self.assertEqual(response.data["case"], self.case_l3.id)
        self.assertFalse(response.data["is_paid"])

    def test_sergeant_can_create_bail_for_level_3_convicted_suspect(self):
        token = self.login(self.sergeant_user)
        self.auth(token)

        response = self.create_bail(
            suspect_id=self.l3_convicted_suspect.id,
            payload={
                "amount": 52000000,
                "conditions": "Electronic monitoring required.",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.data)
        self.assertEqual(response.data["suspect"], self.l3_convicted_suspect.id)
        self.assertEqual(response.data["case"], self.case_l3.id)
        self.assertEqual(int(response.data["amount"]), 52000000)
        self.assertFalse(response.data["is_paid"])

    def test_bail_creation_disallowed_for_level_1_and_critical(self):
        token = self.login(self.sergeant_user)
        self.auth(token)

        level_1_response = self.create_bail(
            suspect_id=self.l1_arrested_suspect.id,
            payload={"amount": 53000000, "conditions": "Level 1 should fail."},
        )
        self.assertEqual(
            level_1_response.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=level_1_response.data,
        )
        self.assertEqual(Bail.objects.filter(suspect=self.l1_arrested_suspect).count(), 0)

        critical_response = self.create_bail(
            suspect_id=self.critical_arrested_suspect.id,
            payload={"amount": 54000000, "conditions": "Critical should fail."},
        )
        self.assertEqual(
            critical_response.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=critical_response.data,
        )
        self.assertEqual(Bail.objects.filter(suspect=self.critical_arrested_suspect).count(), 0)

    def test_bail_creation_fails_for_wrong_suspect_status_on_level_2(self):
        token = self.login(self.sergeant_user)
        self.auth(token)

        response = self.create_bail(
            suspect_id=self.l2_convicted_suspect.id,
            payload={"amount": 55000000, "conditions": "Level 2 convicted should fail."},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=response.data)
        self.assertEqual(Bail.objects.filter(suspect=self.l2_convicted_suspect).count(), 0)

    def test_non_sergeant_cannot_create_bail(self):
        token = self.login(self.officer_user)
        self.auth(token)

        response = self.create_bail(
            suspect_id=self.l2_arrested_suspect.id,
            payload={"amount": 56000000, "conditions": "Officer should be forbidden."},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, msg=response.data)
        self.assertEqual(Bail.objects.filter(suspect=self.l2_arrested_suspect).count(), 0)
