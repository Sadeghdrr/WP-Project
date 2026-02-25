"""
Integration tests — RBAC visibility scopes (Section 14 shared file).

Scope covered in this shared module:
- Case list visibility by role
- Evidence list scoping by permission + case access
- Board access rules (owner/supervisors vs others)
"""

from __future__ import annotations

from urllib.parse import urlsplit

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role
from cases.models import (
    Case,
    CaseComplainant,
    CaseCreationType,
    CaseStatus,
    ComplainantStatus,
    CrimeLevel,
)

User = get_user_model()


class TestRBACScopes(TestCase):
    """Shared RBAC scope suite and fixtures for Section 14."""

    @classmethod
    def setUpTestData(cls):
        call_command("setup_rbac", verbosity=0)

        cls.roles = {
            name: Role.objects.get(name=name)
            for name in (
                "Complainant",
                "Cadet",
                "Police Officer",
                "Detective",
                "Judge",
                "Sergeant",
                "Captain",
                "Police Chief",
            )
        }

        cls.passwords = {
            "complainant_a": "CompA!Pass9101",
            "complainant_b": "CompB!Pass9102",
            "cadet": "Cadet!Pass9103",
            "officer": "Officer!Pass9104",
            "detective_a": "DetA!Pass9105",
            "detective_b": "DetB!Pass9106",
            "judge": "Judge!Pass9107",
            "judge_other": "JudgeOther!Pass9108",
            "sergeant": "Sgt!Pass9109",
            "captain": "Captain!Pass9110",
            "chief": "Chief!Pass9111",
        }

        cls.complainant_a = cls._create_user(
            "rbac_scope_complainant_a",
            "9100000001",
            "09150000001",
            "compa@scope.test",
            "Ava",
            "Citizen",
            cls.roles["Complainant"],
            cls.passwords["complainant_a"],
        )
        cls.complainant_b = cls._create_user(
            "rbac_scope_complainant_b",
            "9100000002",
            "09150000002",
            "compb@scope.test",
            "Ben",
            "Citizen",
            cls.roles["Complainant"],
            cls.passwords["complainant_b"],
        )
        cls.cadet_user = cls._create_user(
            "rbac_scope_cadet",
            "9100000003",
            "09150000003",
            "cadet@scope.test",
            "Cora",
            "Cadet",
            cls.roles["Cadet"],
            cls.passwords["cadet"],
        )
        cls.officer_user = cls._create_user(
            "rbac_scope_officer",
            "9100000004",
            "09150000004",
            "officer@scope.test",
            "Owen",
            "Officer",
            cls.roles["Police Officer"],
            cls.passwords["officer"],
        )
        cls.detective_a = cls._create_user(
            "rbac_scope_detective_a",
            "9100000005",
            "09150000005",
            "deta@scope.test",
            "Dara",
            "Detective",
            cls.roles["Detective"],
            cls.passwords["detective_a"],
        )
        cls.detective_b = cls._create_user(
            "rbac_scope_detective_b",
            "9100000006",
            "09150000006",
            "detb@scope.test",
            "Duke",
            "Detective",
            cls.roles["Detective"],
            cls.passwords["detective_b"],
        )
        cls.judge_user = cls._create_user(
            "rbac_scope_judge",
            "9100000007",
            "09150000007",
            "judge@scope.test",
            "Jade",
            "Judge",
            cls.roles["Judge"],
            cls.passwords["judge"],
        )
        cls.judge_other = cls._create_user(
            "rbac_scope_judge_other",
            "9100000011",
            "09150000011",
            "judge.other@scope.test",
            "Jules",
            "Judge",
            cls.roles["Judge"],
            cls.passwords["judge_other"],
        )
        cls.sergeant_user = cls._create_user(
            "rbac_scope_sergeant",
            "9100000008",
            "09150000008",
            "sergeant@scope.test",
            "Sara",
            "Sergeant",
            cls.roles["Sergeant"],
            cls.passwords["sergeant"],
        )
        cls.captain_user = cls._create_user(
            "rbac_scope_captain",
            "9100000009",
            "09150000009",
            "captain@scope.test",
            "Carl",
            "Captain",
            cls.roles["Captain"],
            cls.passwords["captain"],
        )
        cls.chief_user = cls._create_user(
            "rbac_scope_chief",
            "9100000010",
            "09150000010",
            "chief@scope.test",
            "Pia",
            "Chief",
            cls.roles["Police Chief"],
            cls.passwords["chief"],
        )

        # Deterministic case fixtures.
        cls.case_c1 = cls._create_case_as_complainant_db(
            owner=cls.complainant_a,
            title="Case C1 - Early Complaint",
            status=CaseStatus.COMPLAINT_REGISTERED,
        )
        cls.case_c2 = cls._create_case_as_complainant_db(
            owner=cls.complainant_a,
            title="Case C2 - Investigation A",
            status=CaseStatus.OPEN,
        )
        cls.case_c3 = cls._create_case_as_complainant_db(
            owner=cls.complainant_b,
            title="Case C3 - Investigation B",
            status=CaseStatus.OPEN,
        )
        cls.case_c4 = cls._create_case_as_complainant_db(
            owner=cls.complainant_a,
            title="Case C4 - Voided",
            status=CaseStatus.VOIDED,
        )
        cls.case_c5 = cls._create_case_as_complainant_db(
            owner=cls.complainant_b,
            title="Case C5 - Judiciary Assigned Judge",
            status=CaseStatus.JUDICIARY,
        )
        cls.case_c6 = cls._create_case_as_complainant_db(
            owner=cls.complainant_b,
            title="Case C6 - Judiciary Control Unassigned",
            status=CaseStatus.CLOSED,
        )
        cls.case_c7 = cls._create_case_as_complainant_db(
            owner=cls.complainant_b,
            title="Case C7 - Closed Assigned Other Judge",
            status=CaseStatus.CLOSED,
        )

        # Supervisory assignments for board-access checks.
        cls.case_c2.assigned_sergeant = cls.sergeant_user
        cls.case_c2.assigned_captain = cls.captain_user
        cls.case_c2.save(update_fields=["assigned_sergeant", "assigned_captain", "updated_at"])

        # Assignment helpers are exercised through real endpoints.
        setup_client = APIClient()

        cls._assign_detective_for_setup(
            setup_client,
            case_id=cls.case_c2.id,
            detective_user=cls.detective_a,
            actor=cls.chief_user,
            actor_password=cls.passwords["chief"],
        )
        cls._assign_detective_for_setup(
            setup_client,
            case_id=cls.case_c3.id,
            detective_user=cls.detective_b,
            actor=cls.chief_user,
            actor_password=cls.passwords["chief"],
        )
        cls._assign_judge_for_setup(
            setup_client,
            case_id=cls.case_c5.id,
            judge_user=cls.judge_user,
            actor=cls.chief_user,
            actor_password=cls.passwords["chief"],
        )
        cls._assign_judge_for_setup(
            setup_client,
            case_id=cls.case_c7.id,
            judge_user=cls.judge_other,
            actor=cls.chief_user,
            actor_password=cls.passwords["chief"],
        )

        # Evidence fixtures via real API endpoints.
        cls.evidence_c2_id = cls._create_other_evidence_for_setup(
            setup_client,
            actor=cls.detective_a,
            actor_password=cls.passwords["detective_a"],
            case_id=cls.case_c2.id,
            title="Evidence C2",
        )
        cls.evidence_c3_id = cls._create_other_evidence_for_setup(
            setup_client,
            actor=cls.detective_b,
            actor_password=cls.passwords["detective_b"],
            case_id=cls.case_c3.id,
            title="Evidence C3",
        )

        # Board fixture via real API endpoint.
        cls.board_c2_id = cls._create_board_for_setup(
            setup_client,
            actor=cls.detective_a,
            actor_password=cls.passwords["detective_a"],
            case_id=cls.case_c2.id,
        )

    def setUp(self):
        self.client = APIClient()

    # ---------------------------------------------------------------------
    # Auth helpers (required shared helpers for this section)
    # ---------------------------------------------------------------------

    def login(self, user: User) -> str:
        response = self.client.post(
            reverse("accounts:login"),
            {
                "identifier": user.username,
                "password": self._password_for_user(user),
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

    def login_as(self, user: User) -> None:
        self.auth(self.login(user))

    def get_case_ids_for_current_user(self) -> set[int]:
        """
        Resolve case IDs from the case-list endpoint for the current auth user.

        Supports both paginated (`{"results": [...], "next": ...}`) and plain
        list responses.
        """
        next_url = reverse("case-list")
        case_ids: set[int] = set()

        while next_url:
            response = self.client.get(next_url, format="json")
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                msg=f"Case list request failed: {response.status_code} {response.data}",
            )
            payload = response.data

            if isinstance(payload, dict) and "results" in payload:
                case_ids.update(item["id"] for item in payload["results"])
                next_url = payload.get("next")
                if isinstance(next_url, str) and next_url:
                    next_url = self._to_relative_url(next_url)
            else:
                case_ids.update(item["id"] for item in payload)
                next_url = None

        return case_ids

    def create_case_as_complainant(
        self,
        owner: User,
        *,
        title: str,
        status_value: str = CaseStatus.COMPLAINT_REGISTERED,
    ) -> Case:
        """
        DB-backed helper for deterministic fixtures.

        This file intentionally uses DB setup for case seeds so role-scope
        expectations remain stable across all appended section-14 tests.
        """
        return self._create_case_as_complainant_db(owner, title, status_value)

    def transition_case_to_status(
        self,
        *,
        case_id: int,
        target_status: str,
        actor: User,
        message: str = "",
    ):
        self.login_as(actor)
        return self.client.post(
            reverse("case-transition", kwargs={"pk": case_id}),
            {
                "target_status": target_status,
                "message": message,
            },
            format="json",
        )

    def assign_detective(
        self,
        *,
        case_id: int,
        detective_user: User,
        actor: User,
    ):
        self.login_as(actor)
        return self.client.post(
            reverse("case-assign-detective", kwargs={"pk": case_id}),
            {"user_id": detective_user.id},
            format="json",
        )

    def assign_judge(
        self,
        *,
        case_id: int,
        judge_user: User,
        actor: User,
    ):
        self.login_as(actor)
        return self.client.post(
            reverse("case-assign-judge", kwargs={"pk": case_id}),
            {"user_id": judge_user.id},
            format="json",
        )

    # ---------------------------------------------------------------------
    # Case scope tests
    # ---------------------------------------------------------------------

    def test_case_list_requires_authentication(self):
        response = self.client.get(reverse("case-list"), format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_case_list_scope_for_complainant(self):
        self.login_as(self.complainant_a)
        case_ids = self.get_case_ids_for_current_user()
        self.assertIn(self.case_c1.id, case_ids)
        self.assertIn(self.case_c2.id, case_ids)
        self.assertIn(self.case_c4.id, case_ids)
        self.assertNotIn(self.case_c3.id, case_ids)
        self.assertNotIn(self.case_c5.id, case_ids)
        self.assertNotIn(self.case_c6.id, case_ids)
        self.assertNotIn(self.case_c7.id, case_ids)
        self.assertSetEqual(
            case_ids,
            {self.case_c1.id, self.case_c2.id, self.case_c4.id},
        )

    def test_case_list_scope_for_cadet(self):
        self.login_as(self.cadet_user)
        cadet_ids = self.get_case_ids_for_current_user()
        self.assertIn(self.case_c1.id, cadet_ids)
        self.assertNotIn(self.case_c2.id, cadet_ids)
        self.assertNotIn(self.case_c3.id, cadet_ids)
        self.assertNotIn(self.case_c4.id, cadet_ids)
        self.assertNotIn(self.case_c5.id, cadet_ids)
        self.assertSetEqual(cadet_ids, {self.case_c1.id})

    def test_case_list_scope_for_officer(self):
        self.login_as(self.officer_user)
        officer_ids = self.get_case_ids_for_current_user()
        self.assertIn(self.case_c2.id, officer_ids)
        self.assertIn(self.case_c3.id, officer_ids)
        self.assertIn(self.case_c5.id, officer_ids)
        self.assertIn(self.case_c6.id, officer_ids)
        self.assertIn(self.case_c7.id, officer_ids)
        self.assertNotIn(self.case_c1.id, officer_ids)
        self.assertNotIn(self.case_c4.id, officer_ids)

    def test_case_list_scope_for_detective(self):
        self.login_as(self.detective_a)
        detective_ids = self.get_case_ids_for_current_user()
        self.assertIn(self.case_c2.id, detective_ids)
        self.assertNotIn(self.case_c3.id, detective_ids)
        self.assertSetEqual(detective_ids, {self.case_c2.id})

    def test_case_list_scope_for_judge(self):
        self.login_as(self.judge_user)
        judge_ids = self.get_case_ids_for_current_user()
        self.assertIn(self.case_c5.id, judge_ids)
        self.assertNotIn(self.case_c1.id, judge_ids)
        self.assertNotIn(self.case_c2.id, judge_ids)
        self.assertNotIn(self.case_c3.id, judge_ids)
        self.assertNotIn(self.case_c4.id, judge_ids)
        self.assertNotIn(self.case_c6.id, judge_ids)
        self.assertNotIn(self.case_c7.id, judge_ids)
        self.assertSetEqual(judge_ids, {self.case_c5.id})

    # ---------------------------------------------------------------------
    # Evidence scope tests
    # ---------------------------------------------------------------------

    def test_evidence_list_scoped_to_detective_case_access(self):
        self.login_as(self.detective_a)
        det_a_response = self.client.get(reverse("evidence-list"), format="json")
        self.assertEqual(det_a_response.status_code, status.HTTP_200_OK)
        self.assertSetEqual(self._extract_ids(det_a_response.data), {self.evidence_c2_id})

        self.login_as(self.detective_b)
        det_b_response = self.client.get(reverse("evidence-list"), format="json")
        self.assertEqual(det_b_response.status_code, status.HTTP_200_OK)
        self.assertSetEqual(self._extract_ids(det_b_response.data), {self.evidence_c3_id})

    def test_evidence_list_requires_permission_and_case_visibility(self):
        # Complainant role lacks evidence.view_evidence permission.
        self.login_as(self.complainant_a)
        complainant_response = self.client.get(reverse("evidence-list"), format="json")
        self.assertEqual(complainant_response.status_code, status.HTTP_403_FORBIDDEN)

        # Judge has evidence view permission but should only see evidence from
        # cases they can access (C5/C6 in this fixture have no evidence).
        self.login_as(self.judge_user)
        judge_response = self.client.get(reverse("evidence-list"), format="json")
        self.assertEqual(judge_response.status_code, status.HTTP_200_OK)
        self.assertSetEqual(self._extract_ids(judge_response.data), set())

    # ---------------------------------------------------------------------
    # Board scope tests
    # ---------------------------------------------------------------------

    def test_board_access_owner_and_assigned_supervisors(self):
        self.login_as(self.detective_a)
        owner_list = self.client.get(reverse("detective-board-list"), format="json")
        self.assertEqual(owner_list.status_code, status.HTTP_200_OK)
        self.assertIn(self.board_c2_id, self._extract_ids(owner_list.data))

        owner_full = self.client.get(
            reverse("detective-board-full-state", kwargs={"pk": self.board_c2_id}),
            format="json",
        )
        self.assertEqual(owner_full.status_code, status.HTTP_200_OK)

        self.login_as(self.sergeant_user)
        sgt_list = self.client.get(reverse("detective-board-list"), format="json")
        self.assertEqual(sgt_list.status_code, status.HTTP_200_OK)
        self.assertIn(self.board_c2_id, self._extract_ids(sgt_list.data))

        sgt_full = self.client.get(
            reverse("detective-board-full-state", kwargs={"pk": self.board_c2_id}),
            format="json",
        )
        self.assertEqual(sgt_full.status_code, status.HTTP_200_OK)

        self.login_as(self.captain_user)
        captain_full = self.client.get(
            reverse("detective-board-full-state", kwargs={"pk": self.board_c2_id}),
            format="json",
        )
        self.assertEqual(captain_full.status_code, status.HTTP_200_OK)

    def test_board_access_denied_for_unrelated_roles(self):
        self.login_as(self.detective_b)
        det_b_list = self.client.get(reverse("detective-board-list"), format="json")
        self.assertEqual(det_b_list.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.board_c2_id, self._extract_ids(det_b_list.data))

        det_b_full = self.client.get(
            reverse("detective-board-full-state", kwargs={"pk": self.board_c2_id}),
            format="json",
        )
        self.assertEqual(det_b_full.status_code, status.HTTP_403_FORBIDDEN)

        self.login_as(self.cadet_user)
        cadet_full = self.client.get(
            reverse("detective-board-full-state", kwargs={"pk": self.board_c2_id}),
            format="json",
        )
        self.assertEqual(cadet_full.status_code, status.HTTP_403_FORBIDDEN)

        self.login_as(self.officer_user)
        officer_full = self.client.get(
            reverse("detective-board-full-state", kwargs={"pk": self.board_c2_id}),
            format="json",
        )
        self.assertEqual(officer_full.status_code, status.HTTP_403_FORBIDDEN)

    # ---------------------------------------------------------------------
    # Shared internals
    # ---------------------------------------------------------------------

    @classmethod
    def _create_user(
        cls,
        username: str,
        national_id: str,
        phone_number: str,
        email: str,
        first_name: str,
        last_name: str,
        role: Role,
        password: str,
    ) -> User:
        return User.objects.create_user(
            username=username,
            password=password,
            email=email,
            phone_number=phone_number,
            national_id=national_id,
            first_name=first_name,
            last_name=last_name,
            role=role,
        )

    @classmethod
    def _create_case_as_complainant_db(
        cls,
        owner: User,
        title: str,
        status: str,
    ) -> Case:
        case = Case.objects.create(
            title=title,
            description=f"Fixture for {title}",
            crime_level=CrimeLevel.LEVEL_1,
            creation_type=CaseCreationType.COMPLAINT,
            status=status,
            created_by=owner,
        )
        CaseComplainant.objects.create(
            case=case,
            user=owner,
            is_primary=True,
            status=ComplainantStatus.APPROVED,
        )
        return case

    def _password_for_user(self, user: User) -> str:
        lookup = {
            self.complainant_a.username: self.passwords["complainant_a"],
            self.complainant_b.username: self.passwords["complainant_b"],
            self.cadet_user.username: self.passwords["cadet"],
            self.officer_user.username: self.passwords["officer"],
            self.detective_a.username: self.passwords["detective_a"],
            self.detective_b.username: self.passwords["detective_b"],
            self.judge_user.username: self.passwords["judge"],
            self.judge_other.username: self.passwords["judge_other"],
            self.sergeant_user.username: self.passwords["sergeant"],
            self.captain_user.username: self.passwords["captain"],
            self.chief_user.username: self.passwords["chief"],
        }
        return lookup[user.username]

    @staticmethod
    def _to_relative_url(url: str) -> str:
        parsed = urlsplit(url)
        if parsed.query:
            return f"{parsed.path}?{parsed.query}"
        return parsed.path

    @staticmethod
    def _extract_ids(payload) -> set[int]:
        if isinstance(payload, dict) and "results" in payload:
            items = payload["results"]
        else:
            items = payload
        return {item["id"] for item in items}

    @classmethod
    def _setup_login_token(cls, client: APIClient, user: User, password: str) -> str:
        response = client.post(
            reverse("accounts:login"),
            {
                "identifier": user.username,
                "password": password,
            },
            format="json",
        )
        if response.status_code != status.HTTP_200_OK:
            raise AssertionError(
                f"Setup login failed for {user.username}: {response.status_code} {response.data}"
            )
        return response.data["access"]

    @classmethod
    def _setup_auth(cls, client: APIClient, token: str) -> None:
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    @classmethod
    def _assign_detective_for_setup(
        cls,
        client: APIClient,
        *,
        case_id: int,
        detective_user: User,
        actor: User,
        actor_password: str,
    ) -> None:
        token = cls._setup_login_token(client, actor, actor_password)
        cls._setup_auth(client, token)
        response = client.post(
            reverse("case-assign-detective", kwargs={"pk": case_id}),
            {"user_id": detective_user.id},
            format="json",
        )
        if response.status_code != status.HTTP_200_OK:
            raise AssertionError(
                "Setup assign-detective failed for "
                f"case={case_id}, detective={detective_user.id}: "
                f"{response.status_code} {response.data}"
            )

    @classmethod
    def _assign_judge_for_setup(
        cls,
        client: APIClient,
        *,
        case_id: int,
        judge_user: User,
        actor: User,
        actor_password: str,
    ) -> None:
        token = cls._setup_login_token(client, actor, actor_password)
        cls._setup_auth(client, token)
        response = client.post(
            reverse("case-assign-judge", kwargs={"pk": case_id}),
            {"user_id": judge_user.id},
            format="json",
        )
        if response.status_code != status.HTTP_200_OK:
            raise AssertionError(
                "Setup assign-judge failed for "
                f"case={case_id}, judge={judge_user.id}: "
                f"{response.status_code} {response.data}"
            )

    @classmethod
    def _create_other_evidence_for_setup(
        cls,
        client: APIClient,
        *,
        actor: User,
        actor_password: str,
        case_id: int,
        title: str,
    ) -> int:
        token = cls._setup_login_token(client, actor, actor_password)
        cls._setup_auth(client, token)
        response = client.post(
            reverse("evidence-list"),
            {
                "evidence_type": "other",
                "case": case_id,
                "title": title,
                "description": f"Fixture evidence for case {case_id}",
            },
            format="json",
        )
        if response.status_code != status.HTTP_201_CREATED:
            raise AssertionError(
                f"Setup evidence create failed for case={case_id}: "
                f"{response.status_code} {response.data}"
            )
        return response.data["id"]

    @classmethod
    def _create_board_for_setup(
        cls,
        client: APIClient,
        *,
        actor: User,
        actor_password: str,
        case_id: int,
    ) -> int:
        token = cls._setup_login_token(client, actor, actor_password)
        cls._setup_auth(client, token)
        response = client.post(
            reverse("detective-board-list"),
            {"case": case_id},
            format="json",
        )
        if response.status_code != status.HTTP_201_CREATED:
            raise AssertionError(
                f"Setup board create failed for case={case_id}: "
                f"{response.status_code} {response.data}"
            )
        return response.data["id"]
