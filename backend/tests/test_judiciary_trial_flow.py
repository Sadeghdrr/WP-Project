"""
Integration tests — Judiciary trial flow scenarios 8.1–8.2 (shared file).
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
from suspects.models import Suspect, SuspectStatus, Trial

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
    perms = Permission.objects.filter(
        codename=codename,
        content_type__app_label=app_label,
    )
    if not perms.exists():
        raise Permission.DoesNotExist(
            f"Permission {app_label}.{codename} was not found for test setup."
        )
    role.permissions.add(*perms)


class TestJudiciaryTrialFlow(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.judge_role = _make_role("Judge", hierarchy_level=11)
        cls.detective_role = _make_role("Detective", hierarchy_level=7)
        cls.captain_role = _make_role("Captain", hierarchy_level=9)

        _grant(cls.judge_role, "can_judge_trial", "suspects")
        _grant(cls.captain_role, "can_render_verdict", "suspects")

        cls.judge_password = "Judge!Pass9901"
        cls.detective_password = "Det!Pass9902"
        cls.captain_password = "Cap!Pass9903"

        cls.judge_user = User.objects.create_user(
            username="judiciary_judge",
            password=cls.judge_password,
            email="judiciary_judge@lapd.test",
            phone_number="09141000001",
            national_id="4100000001",
            first_name="Judy",
            last_name="Judge",
            role=cls.judge_role,
        )
        cls.detective_user = User.objects.create_user(
            username="judiciary_detective",
            password=cls.detective_password,
            email="judiciary_detective@lapd.test",
            phone_number="09141000002",
            national_id="4100000002",
            first_name="Dina",
            last_name="Detective",
            role=cls.detective_role,
        )
        cls.captain_user = User.objects.create_user(
            username="judiciary_captain",
            password=cls.captain_password,
            email="judiciary_captain@lapd.test",
            phone_number="09141000003",
            national_id="4100000003",
            first_name="Cory",
            last_name="Captain",
            role=cls.captain_role,
        )

        cls.case_ready = Case.objects.create(
            title="Judiciary Trial Ready Case",
            description="Fixture for trial creation success and validation checks.",
            crime_level=CrimeLevel.LEVEL_1,
            creation_type=CaseCreationType.CRIME_SCENE,
            status=CaseStatus.JUDICIARY,
            created_by=cls.captain_user,
            assigned_captain=cls.captain_user,
            assigned_judge=cls.judge_user,
        )
        # Last-resort fixture setup: trial creation requires UNDER_TRIAL,
        # but reaching this state via APIs requires a long 4.4/4.5 chain.
        cls.suspect_under_trial = Suspect.objects.create(
            case=cls.case_ready,
            full_name="Roy Trial",
            national_id="5100000001",
            description="Prepared suspect for scenario 8.1 trial creation.",
            status=SuspectStatus.UNDER_TRIAL,
            identified_by=cls.detective_user,
            sergeant_approval_status="approved",
        )

        cls.case_pending = Case.objects.create(
            title="Judiciary Trial Pending Case",
            description="Fixture for trial state-gate transition test.",
            crime_level=CrimeLevel.LEVEL_2,
            creation_type=CaseCreationType.CRIME_SCENE,
            status=CaseStatus.CAPTAIN_REVIEW,
            created_by=cls.captain_user,
            assigned_captain=cls.captain_user,
            assigned_judge=cls.judge_user,
        )
        cls.suspect_not_under_trial = Suspect.objects.create(
            case=cls.case_pending,
            full_name="Mina Pending",
            national_id="5100000002",
            description="Suspect waiting for captain verdict.",
            status=SuspectStatus.PENDING_CAPTAIN_VERDICT,
            identified_by=cls.detective_user,
            sergeant_approval_status="approved",
        )

    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse("accounts:login")

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

    def trial_list_url(self, suspect_id: int) -> str:
        return reverse("suspect-trial-list", kwargs={"suspect_pk": suspect_id})

    def trial_detail_url(self, suspect_id: int, trial_id: int) -> str:
        return reverse(
            "suspect-trial-detail",
            kwargs={"suspect_pk": suspect_id, "pk": trial_id},
        )

    def test_judge_can_create_trial_record(self):
        token = self.login(self.judge_user, self.judge_password)
        self.auth(token)

        response = self.client.post(
            self.trial_list_url(self.suspect_under_trial.id),
            {
                "verdict": "guilty",
                "punishment_title": "First Degree Murder",
                "punishment_description": "25 years imprisonment without parole.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Expected 201 when judge creates trial: {response.data}",
        )
        self.assertIn("id", response.data)
        self.assertEqual(response.data["suspect"], self.suspect_under_trial.id)
        self.assertEqual(response.data["case"], self.case_ready.id)
        self.assertEqual(response.data["judge"], self.judge_user.id)
        self.assertEqual(response.data["verdict"], "guilty")
        self.assertEqual(response.data["punishment_title"], "First Degree Murder")

        trial = Trial.objects.get(pk=response.data["id"])
        self.assertEqual(trial.suspect_id, self.suspect_under_trial.id)
        self.assertEqual(trial.case_id, self.case_ready.id)
        self.assertEqual(trial.judge_id, self.judge_user.id)
        self.assertEqual(trial.verdict, "guilty")
        self.assertEqual(
            trial.punishment_description,
            "25 years imprisonment without parole.",
        )

        self.suspect_under_trial.refresh_from_db()
        self.assertEqual(self.suspect_under_trial.status, SuspectStatus.CONVICTED)

        detail_response = self.client.get(
            self.trial_detail_url(
                self.suspect_under_trial.id,
                trial.id,
            ),
            format="json",
        )
        self.assertEqual(
            detail_response.status_code,
            status.HTTP_200_OK,
            msg=f"Expected 200 when reading trial detail: {detail_response.data}",
        )
        self.assertEqual(detail_response.data["id"], trial.id)
        self.assertEqual(detail_response.data["suspect"], self.suspect_under_trial.id)
        self.assertEqual(detail_response.data["case"], self.case_ready.id)

    def test_non_judge_cannot_create_trial_record(self):
        token = self.login(self.detective_user, self.detective_password)
        self.auth(token)

        response = self.client.post(
            self.trial_list_url(self.suspect_under_trial.id),
            {
                "verdict": "guilty",
                "punishment_title": "Attempted Sentence",
                "punishment_description": "This actor is not authorized.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=f"Expected 403 for non-judge trial creation: {response.data}",
        )
        self.assertIn("detail", response.data)
        self.assertEqual(
            Trial.objects.filter(suspect_id=self.suspect_under_trial.id).count(),
            0,
        )

    def test_guilty_verdict_requires_punishment_fields(self):
        token = self.login(self.judge_user, self.judge_password)
        self.auth(token)
        url = self.trial_list_url(self.suspect_under_trial.id)

        missing_both = self.client.post(
            url,
            {"verdict": "guilty"},
            format="json",
        )
        self.assertEqual(
            missing_both.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Expected 400 for missing guilty punishment fields: {missing_both.data}",
        )
        self.assertIn("punishment_title", missing_both.data)

        missing_description = self.client.post(
            url,
            {"verdict": "guilty", "punishment_title": "Sentence Without Description"},
            format="json",
        )
        self.assertEqual(
            missing_description.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Expected 400 for missing punishment description: {missing_description.data}",
        )
        self.assertIn("punishment_description", missing_description.data)

    def test_trial_creation_requires_under_trial_state_then_succeeds_after_transition(self):
        judge_token = self.login(self.judge_user, self.judge_password)
        self.auth(judge_token)

        trial_payload = {"verdict": "innocent"}
        first_attempt = self.client.post(
            self.trial_list_url(self.suspect_not_under_trial.id),
            trial_payload,
            format="json",
        )
        self.assertIn(
            first_attempt.status_code,
            (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT),
            msg=f"Expected 400/409 before UNDER_TRIAL state: {first_attempt.data}",
        )

        captain_token = self.login(self.captain_user, self.captain_password)
        self.auth(captain_token)
        transition_response = self.client.post(
            reverse("suspect-transition-status", kwargs={"pk": self.suspect_not_under_trial.id}),
            {
                "new_status": SuspectStatus.UNDER_TRIAL,
                "reason": "Captain forwards suspect to judiciary for trial.",
            },
            format="json",
        )
        self.assertEqual(
            transition_response.status_code,
            status.HTTP_200_OK,
            msg=f"Transition to under_trial failed during setup: {transition_response.data}",
        )
        self.assertEqual(transition_response.data["status"], SuspectStatus.UNDER_TRIAL)

        self.auth(judge_token)
        second_attempt = self.client.post(
            self.trial_list_url(self.suspect_not_under_trial.id),
            trial_payload,
            format="json",
        )
        self.assertEqual(
            second_attempt.status_code,
            status.HTTP_201_CREATED,
            msg=f"Expected 201 after moving suspect to UNDER_TRIAL: {second_attempt.data}",
        )
        self.assertEqual(second_attempt.data["verdict"], "innocent")
        self.assertEqual(second_attempt.data["punishment_title"], "")
        self.assertEqual(second_attempt.data["punishment_description"], "")

        self.suspect_not_under_trial.refresh_from_db()
        self.assertEqual(self.suspect_not_under_trial.status, SuspectStatus.ACQUITTED)
