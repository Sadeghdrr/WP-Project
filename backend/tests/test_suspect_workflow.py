"""
Integration tests — Suspect workflow scenarios 7.1–7.6 (shared file).
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
from suspects.models import Interrogation, Suspect, SuspectStatus, SuspectStatusLog, Warrant

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
        _grant(cls.detective_role, "can_score_guilt", "suspects")
        _grant(cls.sergeant_role, "can_approve_suspect", "suspects")
        _grant(cls.sergeant_role, "can_issue_arrest_warrant", "suspects")
        _grant(cls.sergeant_role, "can_conduct_interrogation", "suspects")
        _grant(cls.sergeant_role, "can_score_guilt", "suspects")
        _grant(cls.captain_role, "can_render_verdict", "suspects")

        _grant(cls.chief_role, "can_assign_detective", "cases")
        _grant(cls.chief_role, "view_case", "cases")
        _grant(cls.chief_role, "can_approve_critical_case", "cases")
        _grant(cls.chief_role, "can_scope_all_cases", "cases")

        # ── New scope / assignment permissions (permission-based RBAC) ──
        _grant(cls.detective_role, "can_be_assigned_detective", "cases")
        _grant(cls.detective_role, "can_scope_assigned_cases", "cases")
        _grant(cls.detective_role, "can_scope_assigned_suspects", "suspects")
        _grant(cls.sergeant_role, "view_suspect", "suspects")
        _grant(cls.sergeant_role, "can_scope_supervised_suspects", "suspects")
        _grant(cls.captain_role, "view_suspect", "suspects")
        _grant(cls.captain_role, "can_scope_all_suspects", "suspects")

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

    def create_case(
        self,
        *,
        status_value: str = CaseStatus.OPEN,
        crime_level: str = CrimeLevel.LEVEL_2,
    ) -> Case:
        return Case.objects.create(
            title="Scenario 7.x Extra Case",
            description="Generated by test helper.",
            crime_level=crime_level,
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

    def approve_suspect_as_sergeant(self, suspect_id: int) -> dict:
        sergeant_token = self.login(self.sergeant_user, self.sergeant_password)
        self.auth(sergeant_token)
        approve_url = reverse("suspect-approve", kwargs={"pk": suspect_id})
        response = self.client.post(approve_url, {"decision": "approve"}, format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Suspect approval setup failed: {response.data}",
        )
        return response.data

    def arrest_as_user(
        self,
        suspect_id: int,
        *,
        user: User | None = None,
        password: str | None = None,
        arrest_location: str = "742 S. Broadway, Los Angeles",
        arrest_notes: str = "Arrested during coordinated operation.",
        warrant_override_justification: str | None = None,
    ):
        actor = user or self.sergeant_user
        actor_password = password or self.sergeant_password
        token = self.login(actor, actor_password)
        self.auth(token)

        payload = {
            "arrest_location": arrest_location,
            "arrest_notes": arrest_notes,
        }
        if warrant_override_justification is not None:
            payload["warrant_override_justification"] = warrant_override_justification

        arrest_url = reverse("suspect-arrest", kwargs={"pk": suspect_id})
        return self.client.post(arrest_url, payload, format="json")

    def create_arrested_suspect(self, *, full_name: str = "Interrogation Candidate") -> int:
        suspect_id = self.create_suspect_as_detective(full_name=full_name)["id"]
        self.approve_suspect_as_sergeant(suspect_id)
        # Warrant is auto-created on sergeant approval — proceed to arrest
        arrest_response = self.arrest_as_user(
            suspect_id,
            arrest_location="Central Station",
            arrest_notes="Arrest completed for interrogation setup.",
        )
        self.assertIn(
            arrest_response.status_code,
            (status.HTTP_200_OK, status.HTTP_201_CREATED),
            msg=f"Arrest setup failed: {arrest_response.data}",
        )
        return suspect_id

    def create_interrogated_suspect(
        self,
        *,
        crime_level: str,
        full_name: str,
    ) -> int:
        case = self.create_case(crime_level=crime_level)
        suspect_id = self.create_suspect_as_detective(case=case, full_name=full_name)["id"]
        self.approve_suspect_as_sergeant(suspect_id)
        # Warrant is auto-created on sergeant approval — proceed to arrest

        arrest_response = self.arrest_as_user(
            suspect_id,
            arrest_location="Grand Ave, Los Angeles",
            arrest_notes="Arrested for verdict gate setup.",
        )
        self.assertIn(
            arrest_response.status_code,
            (status.HTTP_200_OK, status.HTTP_201_CREATED),
            msg=f"Arrest setup failed for verdict flow: {arrest_response.data}",
        )

        sergeant_token = self.login(self.sergeant_user, self.sergeant_password)
        self.auth(sergeant_token)
        interrogation_url = reverse("suspect-interrogation-list", kwargs={"suspect_pk": suspect_id})
        interrogation_payload = {
            "detective_guilt_score": 8,
            "sergeant_guilt_score": 7,
            "notes": "Prepared for captain verdict workflow.",
        }
        interrogation_response = self.client.post(
            interrogation_url,
            interrogation_payload,
            format="json",
        )
        self.assertEqual(
            interrogation_response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Interrogation setup failed for verdict flow: {interrogation_response.data}",
        )
        return suspect_id

    def transition_suspect_status(
        self,
        suspect_id: int,
        *,
        user: User,
        password: str,
        new_status: str,
        reason: str,
    ):
        token = self.login(user, password)
        self.auth(token)
        transition_url = reverse("suspect-transition-status", kwargs={"pk": suspect_id})
        return self.client.post(
            transition_url,
            {"new_status": new_status, "reason": reason},
            format="json",
        )

    def submit_captain_verdict(
        self,
        suspect_id: int,
        *,
        user: User | None = None,
        password: str | None = None,
        verdict: str = "guilty",
        notes: str = "Captain reviewed evidence and interrogation scores.",
    ):
        actor = user or self.captain_user
        actor_password = password or self.captain_password
        token = self.login(actor, actor_password)
        self.auth(token)
        captain_verdict_url = reverse("suspect-captain-verdict", kwargs={"pk": suspect_id})
        return self.client.post(
            captain_verdict_url,
            {"verdict": verdict, "notes": notes},
            format="json",
        )

    def submit_chief_approval(
        self,
        suspect_id: int,
        *,
        user: User | None = None,
        password: str | None = None,
        decision: str,
        notes: str = "Chief reviewed captain verdict and approves.",
    ):
        actor = user or self.chief_user
        actor_password = password or self.chief_password
        token = self.login(actor, actor_password)
        self.auth(token)
        chief_approval_url = reverse("suspect-chief-approval", kwargs={"pk": suspect_id})
        return self.client.post(
            chief_approval_url,
            {"decision": decision, "notes": notes},
            format="json",
        )

    def create_pending_captain_verdict_suspect(
        self,
        *,
        crime_level: str,
        full_name: str,
    ) -> int:
        suspect_id = self.create_interrogated_suspect(
            crime_level=crime_level,
            full_name=full_name,
        )
        transition_response = self.transition_suspect_status(
            suspect_id,
            user=self.sergeant_user,
            password=self.sergeant_password,
            new_status=SuspectStatus.PENDING_CAPTAIN_VERDICT,
            reason="Interrogation complete; sending to captain for verdict.",
        )
        self.assertEqual(
            transition_response.status_code,
            status.HTTP_200_OK,
            msg=f"Transition to pending captain verdict failed: {transition_response.data}",
        )
        self.assertEqual(
            transition_response.data["status"],
            SuspectStatus.PENDING_CAPTAIN_VERDICT,
        )
        return suspect_id

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

    def test_auto_warrant_created_on_sergeant_approval(self):
        """Approving a suspect auto-creates an active arrest warrant."""
        suspect_id = self.create_suspect_as_detective(full_name="Auto Warrant Candidate")["id"]
        self.approve_suspect_as_sergeant(suspect_id)

        warrants = Warrant.objects.filter(suspect_id=suspect_id)
        self.assertEqual(warrants.count(), 1)
        warrant = warrants.first()
        self.assertEqual(warrant.status, Warrant.WarrantStatus.ACTIVE)
        self.assertEqual(warrant.issued_by_id, self.sergeant_user.id)

    def test_arrest_with_warrant_succeeds(self):
        suspect_id = self.create_suspect_as_detective(full_name="Arrest With Warrant")["id"]
        self.approve_suspect_as_sergeant(suspect_id)
        # Warrant is auto-created on approval

        arrest_response = self.arrest_as_user(
            suspect_id,
            arrest_location="Hollywood Blvd, Los Angeles",
            arrest_notes="Suspect detained without resistance.",
        )
        self.assertIn(
            arrest_response.status_code,
            (status.HTTP_200_OK, status.HTTP_201_CREATED),
            msg=f"Expected 200/201 for arrest with warrant. Body: {arrest_response.data}",
        )
        self.assertEqual(arrest_response.data["status"], SuspectStatus.ARRESTED)

        detail_url = reverse("suspect-detail", kwargs={"pk": suspect_id})
        detail_response = self.client.get(detail_url, format="json")
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["status"], SuspectStatus.ARRESTED)

        suspect = Suspect.objects.get(pk=suspect_id)
        self.assertEqual(suspect.status, SuspectStatus.ARRESTED)
        self.assertIsNotNone(suspect.arrested_at)

        warrant = Warrant.objects.get(suspect_id=suspect_id)
        self.assertEqual(warrant.status, Warrant.WarrantStatus.EXECUTED)

        arrest_log = SuspectStatusLog.objects.filter(
            suspect_id=suspect_id,
            to_status=SuspectStatus.ARRESTED,
        ).latest("created_at")
        self.assertIn("Arrest location: Hollywood Blvd, Los Angeles", arrest_log.notes)
        self.assertIn("Warrant", arrest_log.notes)

    def test_arrest_unapproved_suspect_fails(self):
        """Attempting to arrest a suspect that hasn't been approved should fail."""
        suspect_id = self.create_suspect_as_detective(full_name="Unapproved Arrest Candidate")["id"]
        # No approval → no auto-warrant → arrest must fail

        response = self.arrest_as_user(
            suspect_id,
            arrest_location="Downtown LA",
            arrest_notes="Attempting without approval.",
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT),
            msg=f"Expected 400/409 for unapproved suspect arrest. Body: {response.data}",
        )
        suspect = Suspect.objects.get(pk=suspect_id)
        self.assertEqual(suspect.status, SuspectStatus.WANTED)
        self.assertIsNone(suspect.arrested_at)

    def test_non_authorized_role_cannot_arrest_suspect(self):
        suspect_id = self.create_suspect_as_detective(full_name="Unauthorized Arrest Attempt")["id"]
        self.approve_suspect_as_sergeant(suspect_id)
        # Warrant is auto-created on approval

        response = self.arrest_as_user(
            suspect_id,
            user=self.captain_user,
            password=self.captain_password,
            arrest_location="Sunset Blvd",
            arrest_notes="Captain attempt should be forbidden.",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=f"Expected 403 for unauthorized arrest role. Body: {response.data}",
        )
        suspect = Suspect.objects.get(pk=suspect_id)
        self.assertEqual(suspect.status, SuspectStatus.WANTED)
        self.assertIsNone(suspect.arrested_at)

    def test_cannot_arrest_already_arrested_suspect(self):
        suspect_id = self.create_suspect_as_detective(full_name="Double Arrest Candidate")["id"]
        self.approve_suspect_as_sergeant(suspect_id)
        # Warrant is auto-created on approval

        first_arrest = self.arrest_as_user(
            suspect_id,
            arrest_location="Main St",
            arrest_notes="Initial arrest.",
        )
        self.assertIn(first_arrest.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))

        second_arrest = self.arrest_as_user(
            suspect_id,
            arrest_location="Main St",
            arrest_notes="Second arrest should fail.",
        )
        self.assertIn(
            second_arrest.status_code,
            (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT),
            msg=f"Expected 400/409 for already-arrested suspect. Body: {second_arrest.data}",
        )
        self.assertEqual(
            SuspectStatusLog.objects.filter(
                suspect_id=suspect_id,
                to_status=SuspectStatus.ARRESTED,
            ).count(),
            1,
            msg="Second arrest attempt must not create another arrested transition log.",
        )

    def test_create_interrogation_with_valid_scores_succeeds(self):
        suspect_id = self.create_arrested_suspect(full_name="Valid Interrogation Suspect")

        sergeant_token = self.login(self.sergeant_user, self.sergeant_password)
        self.auth(sergeant_token)
        interrogation_url = reverse("suspect-interrogation-list", kwargs={"suspect_pk": suspect_id})
        payload = {
            "detective_guilt_score": 7,
            "sergeant_guilt_score": 6,
            "notes": "Suspect statements conflicted with timeline.",
        }
        response = self.client.post(interrogation_url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Expected 201 for valid interrogation creation. Body: {response.data}",
        )
        self.assertIn("id", response.data)
        self.assertEqual(response.data["suspect"], suspect_id)
        self.assertEqual(response.data["detective_guilt_score"], 7)
        self.assertEqual(response.data["sergeant_guilt_score"], 6)

        interrogation = Interrogation.objects.get(pk=response.data["id"])
        self.assertEqual(interrogation.suspect_id, suspect_id)
        self.assertEqual(interrogation.detective_guilt_score, 7)
        self.assertEqual(interrogation.sergeant_guilt_score, 6)

        suspect = Suspect.objects.get(pk=suspect_id)
        self.assertEqual(suspect.status, SuspectStatus.UNDER_INTERROGATION)

    def test_interrogation_rejects_out_of_range_detective_score(self):
        suspect_id = self.create_arrested_suspect(full_name="Detective Score Out Of Range")

        sergeant_token = self.login(self.sergeant_user, self.sergeant_password)
        self.auth(sergeant_token)
        interrogation_url = reverse("suspect-interrogation-list", kwargs={"suspect_pk": suspect_id})
        payload = {
            "detective_guilt_score": 0,
            "sergeant_guilt_score": 6,
            "notes": "Invalid detective score test.",
        }
        response = self.client.post(interrogation_url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Expected 400 for out-of-range detective score. Body: {response.data}",
        )
        self.assertIn("detective_guilt_score", response.data)
        self.assertEqual(Interrogation.objects.filter(suspect_id=suspect_id).count(), 0)

    def test_interrogation_rejects_out_of_range_sergeant_score(self):
        suspect_id = self.create_arrested_suspect(full_name="Sergeant Score Out Of Range")

        sergeant_token = self.login(self.sergeant_user, self.sergeant_password)
        self.auth(sergeant_token)
        interrogation_url = reverse("suspect-interrogation-list", kwargs={"suspect_pk": suspect_id})
        payload = {
            "detective_guilt_score": 7,
            "sergeant_guilt_score": 11,
            "notes": "Invalid sergeant score test.",
        }
        response = self.client.post(interrogation_url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Expected 400 for out-of-range sergeant score. Body: {response.data}",
        )
        self.assertIn("sergeant_guilt_score", response.data)
        self.assertEqual(Interrogation.objects.filter(suspect_id=suspect_id).count(), 0)

    def test_unauthorized_role_cannot_create_interrogation(self):
        suspect_id = self.create_arrested_suspect(full_name="Unauthorized Interrogation")

        captain_token = self.login(self.captain_user, self.captain_password)
        self.auth(captain_token)
        interrogation_url = reverse("suspect-interrogation-list", kwargs={"suspect_pk": suspect_id})
        payload = {
            "detective_guilt_score": 7,
            "sergeant_guilt_score": 6,
            "notes": "Captain should not be able to create this interrogation.",
        }
        response = self.client.post(interrogation_url, payload, format="json")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=f"Expected 403 for unauthorized interrogation creation. Body: {response.data}",
        )
        self.assertEqual(Interrogation.objects.filter(suspect_id=suspect_id).count(), 0)

    def test_cannot_create_interrogation_when_suspect_not_arrested(self):
        suspect_id = self.create_suspect_as_detective(full_name="Not Arrested Interrogation")["id"]
        self.approve_suspect_as_sergeant(suspect_id)

        sergeant_token = self.login(self.sergeant_user, self.sergeant_password)
        self.auth(sergeant_token)
        interrogation_url = reverse("suspect-interrogation-list", kwargs={"suspect_pk": suspect_id})
        payload = {
            "detective_guilt_score": 7,
            "sergeant_guilt_score": 6,
            "notes": "Suspect is still wanted, not arrested.",
        }
        response = self.client.post(interrogation_url, payload, format="json")

        self.assertIn(
            response.status_code,
            (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT),
            msg=f"Expected 400/409 when suspect is not arrested. Body: {response.data}",
        )
        self.assertEqual(Interrogation.objects.filter(suspect_id=suspect_id).count(), 0)
        suspect = Suspect.objects.get(pk=suspect_id)
        self.assertEqual(suspect.status, SuspectStatus.WANTED)

    def test_move_to_pending_captain_verdict_successfully(self):
        suspect_id = self.create_interrogated_suspect(
            crime_level=CrimeLevel.LEVEL_2,
            full_name="Pending Captain Transition",
        )
        response = self.transition_suspect_status(
            suspect_id,
            user=self.sergeant_user,
            password=self.sergeant_password,
            new_status=SuspectStatus.PENDING_CAPTAIN_VERDICT,
            reason="Scores submitted to captain for final verdict.",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Expected 200 transitioning to pending captain verdict. Body: {response.data}",
        )
        self.assertEqual(response.data["status"], SuspectStatus.PENDING_CAPTAIN_VERDICT)

        detail_url = reverse("suspect-detail", kwargs={"pk": suspect_id})
        detail_response = self.client.get(detail_url, format="json")
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["status"], SuspectStatus.PENDING_CAPTAIN_VERDICT)

        suspect = Suspect.objects.get(pk=suspect_id)
        self.assertEqual(suspect.status, SuspectStatus.PENDING_CAPTAIN_VERDICT)

    def test_captain_verdict_non_critical_case_moves_directly_to_under_trial(self):
        suspect_id = self.create_pending_captain_verdict_suspect(
            crime_level=CrimeLevel.LEVEL_2,
            full_name="Non Critical Verdict Candidate",
        )
        response = self.submit_captain_verdict(
            suspect_id,
            verdict="guilty",
            notes="Non-critical case can move directly to judiciary.",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Expected 200 for captain verdict on non-critical case. Body: {response.data}",
        )
        self.assertEqual(response.data["status"], SuspectStatus.UNDER_TRIAL)

        detail_url = reverse("suspect-detail", kwargs={"pk": suspect_id})
        detail_response = self.client.get(detail_url, format="json")
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["status"], SuspectStatus.UNDER_TRIAL)

        suspect = Suspect.objects.get(pk=suspect_id)
        self.assertEqual(suspect.status, SuspectStatus.UNDER_TRIAL)

    def test_captain_verdict_critical_case_moves_to_pending_chief_approval(self):
        suspect_id = self.create_pending_captain_verdict_suspect(
            crime_level=CrimeLevel.CRITICAL,
            full_name="Critical Verdict Candidate",
        )
        response = self.submit_captain_verdict(
            suspect_id,
            verdict="guilty",
            notes="Critical case requires chief gate before trial.",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Expected 200 for captain verdict on critical case. Body: {response.data}",
        )
        self.assertEqual(response.data["status"], SuspectStatus.PENDING_CHIEF_APPROVAL)

        detail_url = reverse("suspect-detail", kwargs={"pk": suspect_id})
        detail_response = self.client.get(detail_url, format="json")
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["status"], SuspectStatus.PENDING_CHIEF_APPROVAL)

        suspect = Suspect.objects.get(pk=suspect_id)
        self.assertEqual(suspect.status, SuspectStatus.PENDING_CHIEF_APPROVAL)

    def test_chief_approval_accept_for_critical_case_moves_to_under_trial(self):
        suspect_id = self.create_pending_captain_verdict_suspect(
            crime_level=CrimeLevel.CRITICAL,
            full_name="Critical Chief Approve Candidate",
        )
        captain_response = self.submit_captain_verdict(
            suspect_id,
            verdict="guilty",
            notes="Escalating critical case for chief approval.",
        )
        self.assertEqual(captain_response.status_code, status.HTTP_200_OK)
        self.assertEqual(captain_response.data["status"], SuspectStatus.PENDING_CHIEF_APPROVAL)

        chief_response = self.submit_chief_approval(
            suspect_id,
            decision="approve",
            notes="Chief approves captain verdict for trial.",
        )
        self.assertEqual(
            chief_response.status_code,
            status.HTTP_200_OK,
            msg=f"Expected 200 for chief approval on critical case. Body: {chief_response.data}",
        )
        self.assertEqual(chief_response.data["status"], SuspectStatus.UNDER_TRIAL)

        detail_url = reverse("suspect-detail", kwargs={"pk": suspect_id})
        detail_response = self.client.get(detail_url, format="json")
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["status"], SuspectStatus.UNDER_TRIAL)

        suspect = Suspect.objects.get(pk=suspect_id)
        self.assertEqual(suspect.status, SuspectStatus.UNDER_TRIAL)

    def test_chief_approval_reject_for_critical_case_returns_to_under_interrogation(self):
        suspect_id = self.create_pending_captain_verdict_suspect(
            crime_level=CrimeLevel.CRITICAL,
            full_name="Critical Chief Reject Candidate",
        )
        captain_response = self.submit_captain_verdict(
            suspect_id,
            verdict="guilty",
            notes="Requesting chief review due critical crime level.",
        )
        self.assertEqual(captain_response.status_code, status.HTTP_200_OK)
        self.assertEqual(captain_response.data["status"], SuspectStatus.PENDING_CHIEF_APPROVAL)

        chief_response = self.submit_chief_approval(
            suspect_id,
            decision="reject",
            notes="Evidence gap found; return for further interrogation.",
        )
        self.assertEqual(
            chief_response.status_code,
            status.HTTP_200_OK,
            msg=f"Expected 200 for chief rejection on critical case. Body: {chief_response.data}",
        )
        self.assertEqual(chief_response.data["status"], SuspectStatus.UNDER_INTERROGATION)

        detail_url = reverse("suspect-detail", kwargs={"pk": suspect_id})
        detail_response = self.client.get(detail_url, format="json")
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["status"], SuspectStatus.UNDER_INTERROGATION)

        suspect = Suspect.objects.get(pk=suspect_id)
        self.assertEqual(suspect.status, SuspectStatus.UNDER_INTERROGATION)

    def test_non_captain_cannot_submit_captain_verdict(self):
        suspect_id = self.create_pending_captain_verdict_suspect(
            crime_level=CrimeLevel.LEVEL_2,
            full_name="Captain Permission Guard",
        )
        response = self.submit_captain_verdict(
            suspect_id,
            user=self.sergeant_user,
            password=self.sergeant_password,
            verdict="guilty",
            notes="Sergeant should not be allowed to submit this verdict.",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=f"Expected 403 for non-captain verdict submission. Body: {response.data}",
        )
        suspect = Suspect.objects.get(pk=suspect_id)
        self.assertEqual(suspect.status, SuspectStatus.PENDING_CAPTAIN_VERDICT)

    def test_captain_verdict_when_not_in_reviewable_state_is_rejected(self):
        suspect_id = self.create_suspect_as_detective(full_name="Wrong Verdict State")["id"]
        response = self.submit_captain_verdict(
            suspect_id,
            verdict="guilty",
            notes="Verdict should fail when suspect is still wanted.",
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT),
            msg=f"Expected 400/409 for verdict on invalid state. Body: {response.data}",
        )
        suspect = Suspect.objects.get(pk=suspect_id)
        self.assertEqual(suspect.status, SuspectStatus.WANTED)

    def test_non_chief_cannot_process_chief_approval(self):
        suspect_id = self.create_pending_captain_verdict_suspect(
            crime_level=CrimeLevel.CRITICAL,
            full_name="Chief Permission Guard",
        )
        captain_response = self.submit_captain_verdict(
            suspect_id,
            verdict="guilty",
            notes="Critical case pending chief approval.",
        )
        self.assertEqual(captain_response.status_code, status.HTTP_200_OK)
        self.assertEqual(captain_response.data["status"], SuspectStatus.PENDING_CHIEF_APPROVAL)

        response = self.submit_chief_approval(
            suspect_id,
            user=self.captain_user,
            password=self.captain_password,
            decision="approve",
            notes="Captain cannot process chief approval endpoint.",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=f"Expected 403 for non-chief chief-approval action. Body: {response.data}",
        )
        suspect = Suspect.objects.get(pk=suspect_id)
        self.assertEqual(suspect.status, SuspectStatus.PENDING_CHIEF_APPROVAL)

    def test_chief_approval_for_non_critical_case_is_rejected(self):
        suspect_id = self.create_pending_captain_verdict_suspect(
            crime_level=CrimeLevel.LEVEL_2,
            full_name="Chief Non Critical Guard",
        )
        captain_response = self.submit_captain_verdict(
            suspect_id,
            verdict="guilty",
            notes="Non-critical case should bypass chief gate.",
        )
        self.assertEqual(captain_response.status_code, status.HTTP_200_OK)
        self.assertEqual(captain_response.data["status"], SuspectStatus.UNDER_TRIAL)

        response = self.submit_chief_approval(
            suspect_id,
            decision="approve",
            notes="Chief approval should not apply once already under trial.",
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT),
            msg=f"Expected 400/409 for chief approval on non-critical path. Body: {response.data}",
        )
        suspect = Suspect.objects.get(pk=suspect_id)
        self.assertEqual(suspect.status, SuspectStatus.UNDER_TRIAL)
