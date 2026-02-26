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
        cls.base_user_role = _make_role("Base User", hierarchy_level=1)

        _grant(cls.judge_role, "can_judge_trial", "suspects")
        _grant(cls.judge_role, "view_evidence", "evidence")
        _grant(cls.judge_role, "can_be_assigned_judge", "cases")
        _grant(cls.judge_role, "can_scope_judiciary_cases", "cases")
        _grant(cls.judge_role, "can_view_case_report", "cases")
        _grant(cls.judge_role, "view_case", "cases")
        _grant(cls.judge_role, "view_suspect", "suspects")
        _grant(cls.judge_role, "can_scope_all_suspects", "suspects")
        _grant(cls.captain_role, "can_render_verdict", "suspects")
        _grant(cls.captain_role, "can_forward_to_judiciary", "cases")
        _grant(cls.captain_role, "can_change_case_status", "cases")
        _grant(cls.captain_role, "add_casecomplainant", "cases")
        _grant(cls.captain_role, "add_evidence", "evidence")
        _grant(cls.captain_role, "can_scope_all_cases", "cases")
        _grant(cls.captain_role, "view_case", "cases")
        _grant(cls.captain_role, "can_assign_detective", "cases")
        _grant(cls.detective_role, "can_be_assigned_detective", "cases")

        cls.judge_password = "Judge!Pass9901"
        cls.detective_password = "Det!Pass9902"
        cls.captain_password = "Cap!Pass9903"
        cls.complainant_password = "User!Pass9904"
        cls.unrelated_password = "User!Pass9905"

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
        cls.complainant_user = User.objects.create_user(
            username="judiciary_complainant",
            password=cls.complainant_password,
            email="judiciary_complainant@lapd.test",
            phone_number="09141000004",
            national_id="4100000004",
            first_name="Nora",
            last_name="Complainant",
            role=cls.base_user_role,
        )
        cls.unrelated_user = User.objects.create_user(
            username="judiciary_unrelated",
            password=cls.unrelated_password,
            email="judiciary_unrelated@lapd.test",
            phone_number="09141000005",
            national_id="4100000005",
            first_name="Una",
            last_name="Related",
            role=cls.base_user_role,
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

    def case_detail_url(self, case_id: int) -> str:
        return reverse("case-detail", kwargs={"pk": case_id})

    def case_status_log_url(self, case_id: int) -> str:
        return reverse("case-status-log", kwargs={"pk": case_id})

    def case_assign_judge_url(self, case_id: int) -> str:
        return reverse("case-assign-judge", kwargs={"pk": case_id})

    def case_complainants_url(self, case_id: int) -> str:
        return reverse("case-complainants", kwargs={"pk": case_id})

    def case_witnesses_url(self, case_id: int) -> str:
        return reverse("case-witnesses", kwargs={"pk": case_id})

    def case_transition_url(self, case_id: int) -> str:
        return reverse("case-transition", kwargs={"pk": case_id})

    def case_report_url(self, case_id: int) -> str:
        return reverse("case-report", kwargs={"pk": case_id})

    def build_rich_judiciary_case_via_api(self) -> dict:
        case = Case.objects.create(
            title="Judiciary Full File Case",
            description="Case fixture for scenario 8.2 full-file retrieval checks.",
            crime_level=CrimeLevel.LEVEL_1,
            creation_type=CaseCreationType.CRIME_SCENE,
            status=CaseStatus.JUDICIARY,
            created_by=self.captain_user,
            assigned_detective=self.detective_user,
            assigned_captain=self.captain_user,
        )

        captain_token = self.login(self.captain_user, self.captain_password)
        self.auth(captain_token)

        assign_judge_response = self.client.post(
            self.case_assign_judge_url(case.id),
            {"user_id": self.judge_user.id},
            format="json",
        )
        self.assertEqual(
            assign_judge_response.status_code,
            status.HTTP_200_OK,
            msg=f"Assign judge failed in setup: {assign_judge_response.data}",
        )
        case.refresh_from_db()
        self.assertEqual(case.assigned_judge_id, self.judge_user.id)

        complainant_response = self.client.post(
            self.case_complainants_url(case.id),
            {"user_id": self.complainant_user.id},
            format="json",
        )
        self.assertEqual(
            complainant_response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Adding complainant failed in setup: {complainant_response.data}",
        )

        witness_response = self.client.post(
            self.case_witnesses_url(case.id),
            {
                "full_name": "Julia Witness",
                "phone_number": "+12135550178",
                "national_id": "6200000001",
            },
            format="json",
        )
        self.assertEqual(
            witness_response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Adding witness failed in setup: {witness_response.data}",
        )

        evidence_response = self.client.post(
            reverse("evidence-list"),
            {
                "evidence_type": "other",
                "case": case.id,
                "title": "Knife from alley",
                "description": "Recovered from scene perimeter; tagged and bagged.",
            },
            format="json",
        )
        self.assertEqual(
            evidence_response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Adding evidence failed in setup: {evidence_response.data}",
        )

        suspect = Suspect.objects.create(
            case=case,
            full_name="Full File Suspect",
            national_id="6200000002",
            description="Suspect included for judiciary file retrieval.",
            status=SuspectStatus.WANTED,
            identified_by=self.detective_user,
            sergeant_approval_status="approved",
        )

        transition_response = self.client.post(
            self.case_transition_url(case.id),
            {
                "target_status": CaseStatus.CLOSED,
                "message": "Closing case after judiciary package finalization.",
            },
            format="json",
        )
        self.assertEqual(
            transition_response.status_code,
            status.HTTP_200_OK,
            msg=f"Case transition setup failed: {transition_response.data}",
        )

        case.refresh_from_db()
        self.assertEqual(case.status, CaseStatus.CLOSED)

        return {
            "case": case,
            "complainant_id": complainant_response.data["id"],
            "witness_id": witness_response.data["id"],
            "evidence_id": evidence_response.data["id"],
            "suspect_id": suspect.id,
        }

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

    def test_judge_can_retrieve_full_case_file_sections(self):
        rich = self.build_rich_judiciary_case_via_api()
        case = rich["case"]

        judge_token = self.login(self.judge_user, self.judge_password)
        self.auth(judge_token)

        case_detail_response = self.client.get(self.case_detail_url(case.id), format="json")
        self.assertEqual(
            case_detail_response.status_code,
            status.HTTP_200_OK,
            msg=f"Judge could not fetch case detail: {case_detail_response.data}",
        )
        self.assertEqual(case_detail_response.data["id"], case.id)
        self.assertEqual(case_detail_response.data["assigned_judge"], self.judge_user.id)
        self.assertEqual(case_detail_response.data["assigned_captain"], self.captain_user.id)
        self.assertEqual(case_detail_response.data["assigned_detective"], self.detective_user.id)
        self.assertIn("complainants", case_detail_response.data)
        self.assertIn("witnesses", case_detail_response.data)
        self.assertIn("status_logs", case_detail_response.data)
        self.assertIn("status", case_detail_response.data)
        self.assertNotIn("password", case_detail_response.data)
        self.assertTrue(
            any(item["id"] == rich["complainant_id"] for item in case_detail_response.data["complainants"])
        )
        self.assertTrue(
            any(item["id"] == rich["witness_id"] for item in case_detail_response.data["witnesses"])
        )

        evidence_response = self.client.get(
            reverse("evidence-list"),
            {"case": case.id},
            format="json",
        )
        self.assertEqual(
            evidence_response.status_code,
            status.HTTP_200_OK,
            msg=f"Judge could not fetch evidence list: {evidence_response.data}",
        )
        if evidence_response.data:
            self.assertTrue(
                any(item["id"] == rich["evidence_id"] for item in evidence_response.data),
                msg=f"Expected evidence id {rich['evidence_id']} in list: {evidence_response.data}",
            )

        suspects_response = self.client.get(
            reverse("suspect-list"),
            {"case": case.id},
            format="json",
        )
        self.assertEqual(
            suspects_response.status_code,
            status.HTTP_200_OK,
            msg=f"Judge could not fetch suspects list: {suspects_response.data}",
        )
        self.assertTrue(
            any(item["id"] == rich["suspect_id"] for item in suspects_response.data),
            msg=f"Expected suspect id {rich['suspect_id']} in list: {suspects_response.data}",
        )

        status_log_response = self.client.get(self.case_status_log_url(case.id), format="json")
        self.assertEqual(
            status_log_response.status_code,
            status.HTTP_200_OK,
            msg=f"Judge could not fetch case status log: {status_log_response.data}",
        )
        self.assertGreaterEqual(len(status_log_response.data), 1)

        report_response = self.client.get(self.case_report_url(case.id), format="json")
        self.assertEqual(
            report_response.status_code,
            status.HTTP_200_OK,
            msg=f"Judge could not fetch full case report: {report_response.data}",
        )
        self.assertIn("case", report_response.data)
        self.assertIn("personnel", report_response.data)
        self.assertIn("evidence", report_response.data)
        self.assertIn("suspects", report_response.data)
        self.assertIn("status_history", report_response.data)
        self.assertTrue(
            any(item["id"] == rich["evidence_id"] for item in report_response.data["evidence"]),
            msg=f"Expected evidence id {rich['evidence_id']} in full case report: {report_response.data}",
        )

    def test_unrelated_normal_user_cannot_access_full_case_file(self):
        rich = self.build_rich_judiciary_case_via_api()
        case = rich["case"]

        normal_token = self.login(self.unrelated_user, self.unrelated_password)
        self.auth(normal_token)

        case_detail_response = self.client.get(self.case_detail_url(case.id), format="json")
        self.assertIn(
            case_detail_response.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND),
            msg=f"Unrelated user unexpectedly accessed case detail: {case_detail_response.data}",
        )

        evidence_response = self.client.get(
            reverse("evidence-list"),
            {"case": case.id},
            format="json",
        )
        self.assertIn(
            evidence_response.status_code,
            (status.HTTP_403_FORBIDDEN, status.HTTP_200_OK),
            msg=f"Unexpected evidence list status for unrelated user: {evidence_response.data}",
        )
        if evidence_response.status_code == status.HTTP_200_OK:
            self.assertEqual(evidence_response.data, [])

        suspects_response = self.client.get(
            reverse("suspect-list"),
            {"case": case.id},
            format="json",
        )
        self.assertEqual(
            suspects_response.status_code,
            status.HTTP_200_OK,
            msg=f"Unexpected suspects list status for unrelated user: {suspects_response.data}",
        )
        self.assertEqual(suspects_response.data, [])

        report_response = self.client.get(self.case_report_url(case.id), format="json")
        self.assertEqual(
            report_response.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=f"Unrelated user unexpectedly accessed full case report: {report_response.data}",
        )
