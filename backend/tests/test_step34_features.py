"""
Tests for step-34: Notification formatting, Dashboard noauth,
Coroner case scope, and Crime-scene approval hierarchy enforcement.

Coverage
--------
1. NotificationService safe payload formatting (unit tests)
2. DashboardStatsView anonymous access (integration test)
3. CASE_SCOPE_RULES coroner filtering (DB integration)
4. approve_crime_scene_case rank hierarchy enforcement (DB integration)
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
from core.domain.notifications import NotificationService, _EVENT_TEMPLATES
from evidence.models import BiologicalEvidence, EvidenceType

User = get_user_model()


# ═══════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════

def _make_role(name: str, hierarchy_level: int) -> Role:
    role, _ = Role.objects.get_or_create(
        name=name,
        defaults={
            "description": f"Test role: {name}",
            "hierarchy_level": hierarchy_level,
        },
    )
    if role.hierarchy_level != hierarchy_level:
        role.hierarchy_level = hierarchy_level
        role.save(update_fields=["hierarchy_level"])
    return role


def _grant(role: Role, codename: str, app_label: str) -> None:
    perm = Permission.objects.get(
        codename=codename,
        content_type__app_label=app_label,
    )
    role.permissions.add(perm)


# ═══════════════════════════════════════════════════════════════════
#  1. Notification Formatting — Unit Tests
# ═══════════════════════════════════════════════════════════════════

class TestNotificationServiceFormatting(TestCase):
    """Integration tests for NotificationService.create with payload formatting."""

    @classmethod
    def setUpTestData(cls):
        cls.role = _make_role("Detective", 7)
        cls.actor = User.objects.create_user(
            username="notif_fmt_actor",
            password="N0tif!Actor1",
            email="notif_fmt_actor@test.com",
            phone_number="09140001001",
            national_id="5000001001",
            first_name="Cole",
            last_name="Phelps",
            role=cls.role,
        )
        cls.recipient = User.objects.create_user(
            username="notif_fmt_recipient",
            password="N0tif!Recip1",
            email="notif_fmt_recipient@test.com",
            phone_number="09140001002",
            national_id="5000001002",
            first_name="Stefan",
            last_name="Bekowsky",
            role=cls.role,
        )

    def test_payload_values_in_message(self):
        """Payload dict values should appear in the notification message."""
        notifications = NotificationService.create(
            actor=self.actor,
            recipients=self.recipient,
            event_type="bounty_tip_verified",
            payload={"unique_code": "ABC-123", "reward_amount": "500"},
        )
        self.assertEqual(len(notifications), 1)
        notif = notifications[0]
        self.assertIn("ABC-123", notif.message)
        self.assertIn("500", notif.message)

    def test_missing_keys_raises_keyerror(self):
        """Should raise KeyError if payload does not have all expected keys."""
        with self.assertRaises(KeyError):
            NotificationService.create(
                actor=self.actor,
                recipients=self.recipient,
                event_type="bounty_tip_verified",
                payload={"unique_code": "ABC-123"},  # missing reward_amount
            )

    def test_no_crash_with_none_payload(self):
        """Should not crash if payload is None."""
        notifications = NotificationService.create(
            actor=self.actor,
            recipients=self.recipient,
            event_type="case_approved",
            payload=None,
        )
        self.assertEqual(len(notifications), 1)

    def test_unknown_event_type_uses_fallback(self):
        """Unknown event types should not crash, use the raw event_type as title."""
        notifications = NotificationService.create(
            actor=self.actor,
            recipients=self.recipient,
            event_type="totally_unknown_event",
            payload={"foo": "bar"},
        )
        self.assertEqual(len(notifications), 1)
        notif = notifications[0]
        self.assertEqual(notif.title, "Totally Unknown Event")


# ═══════════════════════════════════════════════════════════════════
#  2. Dashboard Anonymous Access
# ═══════════════════════════════════════════════════════════════════

class TestDashboardAnonymousAccess(TestCase):
    """Test that the dashboard endpoint allows anonymous access."""

    @classmethod
    def setUpTestData(cls):
        cls.role = _make_role("Captain", 9)
        _grant(cls.role, "can_scope_all_cases", "cases")
        cls.user = User.objects.create_user(
            username="dash_anon_creator",
            password="D@sh!Anon1",
            email="dash_anon@test.com",
            phone_number="09140002001",
            national_id="5000002001",
            first_name="Test",
            last_name="Creator",
            role=cls.role,
        )
        Case.objects.create(
            title="Dashboard Anon Test Case",
            description="Test case for anonymous dashboard access.",
            crime_level=CrimeLevel.LEVEL_2,
            status=CaseStatus.OPEN,
            creation_type=CaseCreationType.CRIME_SCENE,
            created_by=cls.user,
        )

    def setUp(self):
        self.client = APIClient()
        self.dashboard_url = reverse("core:dashboard-stats")

    def test_anonymous_request_returns_200(self):
        """GET /api/core/dashboard/ without auth should return 200."""
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_returns_aggregate_stats(self):
        """Anonymous dashboard returns department-wide aggregates."""
        response = self.client.get(self.dashboard_url)
        data = response.data
        self.assertIn("total_cases", data)
        self.assertGreaterEqual(data["total_cases"], 1)
        self.assertIn("active_cases", data)
        self.assertIn("total_evidence", data)

    def test_no_user_specific_data_leaked(self):
        """Response should not contain user-specific data fields."""
        response = self.client.get(self.dashboard_url)
        data = response.data
        # Should not contain any user-identifying info
        self.assertNotIn("user", data)
        self.assertNotIn("username", data)
        self.assertNotIn("email", data)


# ═══════════════════════════════════════════════════════════════════
#  3. Coroner Case Scope Filtering
# ═══════════════════════════════════════════════════════════════════

class TestCoronerCaseScope(TestCase):
    """Test that CASE_SCOPE_RULES includes coroner bio-evidence filtering."""

    @classmethod
    def setUpTestData(cls):
        cls.officer_role = _make_role("Police Officer", 6)
        cls.coroner_role = _make_role("Coroner", 3)

        # Grant coroner the coroner scope permission
        _grant(cls.coroner_role, "can_scope_coroner_cases", "cases")
        _grant(cls.coroner_role, "can_verify_evidence", "evidence")
        _grant(cls.coroner_role, "view_case", "cases")

        cls.officer = User.objects.create_user(
            username="scope_officer",
            password="0fficer!Scope1",
            email="scope_officer@test.com",
            phone_number="09140003001",
            national_id="5000003001",
            first_name="Officer",
            last_name="Scope",
            role=cls.officer_role,
        )
        cls.coroner = User.objects.create_user(
            username="scope_coroner",
            password="C0roner!Scope1",
            email="scope_coroner@test.com",
            phone_number="09140003002",
            national_id="5000003002",
            first_name="Coroner",
            last_name="Scope",
            role=cls.coroner_role,
        )

        # Case WITH unverified bio evidence (coroner should see this)
        cls.case_with_bio = Case.objects.create(
            title="Case With Unverified Bio",
            description="Has unverified biological evidence.",
            crime_level=CrimeLevel.LEVEL_2,
            status=CaseStatus.OPEN,
            creation_type=CaseCreationType.CRIME_SCENE,
            created_by=cls.officer,
        )
        BiologicalEvidence.objects.create(
            case=cls.case_with_bio,
            title="Blood Sample",
            description="Blood sample from crime scene.",
            evidence_type=EvidenceType.BIOLOGICAL,
            registered_by=cls.officer,
            is_verified=False,
        )

        # Case WITH verified bio evidence (coroner should NOT see this)
        cls.case_with_verified_bio = Case.objects.create(
            title="Case With Verified Bio",
            description="Has verified biological evidence.",
            crime_level=CrimeLevel.LEVEL_1,
            status=CaseStatus.INVESTIGATION,
            creation_type=CaseCreationType.CRIME_SCENE,
            created_by=cls.officer,
        )
        BiologicalEvidence.objects.create(
            case=cls.case_with_verified_bio,
            title="Hair Sample",
            description="Hair strand from suspect.",
            evidence_type=EvidenceType.BIOLOGICAL,
            registered_by=cls.officer,
            is_verified=True,
            verified_by=cls.coroner,
        )

        # Case WITHOUT any bio evidence (coroner should NOT see this)
        cls.case_without_bio = Case.objects.create(
            title="Case Without Bio Evidence",
            description="No biological evidence at all.",
            crime_level=CrimeLevel.LEVEL_3,
            status=CaseStatus.OPEN,
            creation_type=CaseCreationType.CRIME_SCENE,
            created_by=cls.officer,
        )

    def test_coroner_scope_returns_cases_with_unverified_bio(self):
        """Coroner should see cases containing unverified biological evidence."""
        from cases.services import CASE_SCOPE_RULES
        from core.domain.access import apply_permission_scope

        qs = apply_permission_scope(
            Case.objects.all(),
            self.coroner,
            scope_rules=CASE_SCOPE_RULES,
        )
        case_ids = set(qs.values_list("id", flat=True))
        self.assertIn(self.case_with_bio.id, case_ids)

    def test_coroner_scope_excludes_verified_only_cases(self):
        """Coroner should NOT see cases where all bio evidence is verified."""
        from cases.services import CASE_SCOPE_RULES
        from core.domain.access import apply_permission_scope

        qs = apply_permission_scope(
            Case.objects.all(),
            self.coroner,
            scope_rules=CASE_SCOPE_RULES,
        )
        case_ids = set(qs.values_list("id", flat=True))
        self.assertNotIn(self.case_with_verified_bio.id, case_ids)

    def test_coroner_scope_excludes_cases_without_bio(self):
        """Coroner should NOT see cases with no bio evidence."""
        from cases.services import CASE_SCOPE_RULES
        from core.domain.access import apply_permission_scope

        qs = apply_permission_scope(
            Case.objects.all(),
            self.coroner,
            scope_rules=CASE_SCOPE_RULES,
        )
        case_ids = set(qs.values_list("id", flat=True))
        self.assertNotIn(self.case_without_bio.id, case_ids)


# ═══════════════════════════════════════════════════════════════════
#  4. Crime-Scene Approval Hierarchy
# ═══════════════════════════════════════════════════════════════════

class TestApproveCrimeSceneHierarchy(TestCase):
    """Test rank hierarchy enforcement in approve_crime_scene_case."""

    @classmethod
    def setUpTestData(cls):
        cls.chief_role = _make_role("Police Chief", 10)
        cls.captain_role = _make_role("Captain", 9)
        cls.officer_role = _make_role("Police Officer", 6)
        cls.sergeant_role = _make_role("Sergeant", 8)

        # Grant permissions
        for role in (cls.captain_role, cls.chief_role):
            _grant(role, "can_approve_case", "cases")

        for role in (cls.officer_role, cls.captain_role, cls.chief_role, cls.sergeant_role):
            _grant(role, "can_create_crime_scene", "cases")
            _grant(role, "add_case", "cases")

        _grant(cls.chief_role, "can_auto_approve_crime_scene", "cases")
        _grant(cls.chief_role, "can_change_case_status", "cases")

        cls.passwords = {
            "chief": "Ch!ef!Hier99",
            "captain": "C@ptain!Hier99",
            "officer": "0fficer!Hier99",
            "sergeant": "S3rgeant!Hier99",
        }

        cls.chief = User.objects.create_user(
            username="hier_chief",
            password=cls.passwords["chief"],
            email="hier_chief@test.com",
            phone_number="09140004001",
            national_id="5000004001",
            first_name="Chief",
            last_name="Hierarchy",
            role=cls.chief_role,
        )
        cls.captain = User.objects.create_user(
            username="hier_captain",
            password=cls.passwords["captain"],
            email="hier_captain@test.com",
            phone_number="09140004002",
            national_id="5000004002",
            first_name="Captain",
            last_name="Hierarchy",
            role=cls.captain_role,
        )
        cls.officer = User.objects.create_user(
            username="hier_officer",
            password=cls.passwords["officer"],
            email="hier_officer@test.com",
            phone_number="09140004003",
            national_id="5000004003",
            first_name="Officer",
            last_name="Hierarchy",
            role=cls.officer_role,
        )
        cls.sergeant = User.objects.create_user(
            username="hier_sergeant",
            password=cls.passwords["sergeant"],
            email="hier_sergeant@test.com",
            phone_number="09140004004",
            national_id="5000004004",
            first_name="Sergeant",
            last_name="Hierarchy",
            role=cls.sergeant_role,
        )

    def _create_pending_case(self, creator) -> Case:
        """Helper: create a PENDING_APPROVAL crime-scene case."""
        return Case.objects.create(
            title="Hierarchy Test Case",
            description="Testing rank hierarchy for crime-scene approval.",
            crime_level=CrimeLevel.LEVEL_2,
            status=CaseStatus.PENDING_APPROVAL,
            creation_type=CaseCreationType.CRIME_SCENE,
            created_by=creator,
        )

    def test_captain_can_approve_officer_case(self):
        """Captain (rank 9) can approve case created by Officer (rank 6)."""
        from cases.services import CaseWorkflowService

        case = self._create_pending_case(self.officer)
        result = CaseWorkflowService.approve_crime_scene_case(case, self.captain)
        self.assertEqual(result.status, CaseStatus.OPEN)
        self.assertEqual(result.approved_by, self.captain)

    def test_captain_can_approve_captain_case(self):
        """Captain (rank 9) can approve case created by another Captain (rank 9) — equal rank."""
        from cases.services import CaseWorkflowService

        other_captain = User.objects.create_user(
            username="hier_captain_2",
            password="C@ptainH!er2",
            email="hier_captain2@test.com",
            phone_number="09140004010",
            national_id="5000004010",
            first_name="Other",
            last_name="Captain",
            role=self.captain_role,
        )
        case = self._create_pending_case(other_captain)
        result = CaseWorkflowService.approve_crime_scene_case(case, self.captain)
        self.assertEqual(result.status, CaseStatus.OPEN)

    def test_captain_cannot_approve_chief_case(self):
        """Captain (rank 9) CANNOT approve case created by Chief (rank 10) — lower rank."""
        from cases.services import CaseWorkflowService
        from core.domain.exceptions import PermissionDenied

        case = self._create_pending_case(self.chief)
        with self.assertRaises(PermissionDenied):
            CaseWorkflowService.approve_crime_scene_case(case, self.captain)

    def test_chief_can_approve_any_case(self):
        """Chief (rank 10) can approve cases created by any lower rank."""
        from cases.services import CaseWorkflowService

        case = self._create_pending_case(self.captain)
        result = CaseWorkflowService.approve_crime_scene_case(case, self.chief)
        self.assertEqual(result.status, CaseStatus.OPEN)

    def test_officer_without_permission_cannot_approve(self):
        """Officer without CAN_APPROVE_CASE permission is blocked."""
        from cases.services import CaseWorkflowService
        from core.domain.exceptions import PermissionDenied

        case = self._create_pending_case(self.officer)
        # Sergeant has higher rank (8) than officer (6) but no CAN_APPROVE_CASE
        with self.assertRaises(PermissionDenied):
            CaseWorkflowService.approve_crime_scene_case(case, self.sergeant)

    def test_chief_auto_approves_on_creation(self):
        """Chief-created crime-scene cases should auto-approve to OPEN status."""
        from cases.services import CaseCreationService

        case = CaseCreationService.create_crime_scene_case(
            validated_data={
                "title": "Chief Auto-Approve",
                "description": "Chief creates crime-scene; auto-opens.",
                "crime_level": CrimeLevel.LEVEL_1,
                "incident_date": "2026-01-15T10:00:00Z",
                "location": "123 Main St",
            },
            requesting_user=self.chief,
        )
        self.assertEqual(case.status, CaseStatus.OPEN)
        self.assertEqual(case.approved_by, self.chief)

    def test_non_crime_scene_case_rejected(self):
        """approve_crime_scene_case rejects non-crime-scene cases."""
        from cases.services import CaseWorkflowService
        from core.domain.exceptions import DomainError

        case = Case.objects.create(
            title="Complaint Case",
            description="Not a crime-scene case.",
            crime_level=CrimeLevel.LEVEL_2,
            status=CaseStatus.PENDING_APPROVAL,
            creation_type=CaseCreationType.COMPLAINT,
            created_by=self.officer,
        )
        with self.assertRaises(DomainError):
            CaseWorkflowService.approve_crime_scene_case(case, self.captain)

    def test_wrong_status_is_rejected(self):
        """approve_crime_scene_case rejects cases not in PENDING_APPROVAL."""
        from cases.services import CaseWorkflowService
        from core.domain.exceptions import InvalidTransition

        case = Case.objects.create(
            title="Open Case",
            description="Already open.",
            crime_level=CrimeLevel.LEVEL_2,
            status=CaseStatus.OPEN,
            creation_type=CaseCreationType.CRIME_SCENE,
            created_by=self.officer,
        )
        with self.assertRaises(InvalidTransition):
            CaseWorkflowService.approve_crime_scene_case(case, self.captain)
