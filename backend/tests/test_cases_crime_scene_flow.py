"""
Integration tests — Crime-Scene Case Creation Flow (Scenarios 4.1–4.5).

Business-flow reference : md-files/project-doc.md  §4.2.2
API endpoint reference  : md-files/swagger_documentation_report.md  §3.2
Service implementation  : md-files/cases_services_crime_scene_flow_report.md

All scenarios share this single class so fixtures are created once and
the whole file can be run as one suite:

    python manage.py test tests.test_cases_crime_scene_flow

Test map
--------
  4.1  Officer creates crime-scene case → status "pending_approval"
  4.2  Superior (Captain) approves crime-scene case → status "open"
  4.3  Police Chief creates crime-scene case → status "open" (auto-approved)
  4.4  Cadet attempts to create crime-scene case → 403 Forbidden
  4.5  Witnesses embedded at creation are persisted correctly
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role
from cases.models import Case, CaseStatus, CaseStatusLog

User = get_user_model()


# ═══════════════════════════════════════════════════════════════════
#  Helpers — shared across scenarios inside this module
# ═══════════════════════════════════════════════════════════════════

def _make_role(name: str, hierarchy_level: int) -> Role:
    """
    Get or create a Role by name.

    Uses get_or_create so the method is safe to call multiple times
    (idempotent within a single test-database transaction).
    """
    role, _ = Role.objects.get_or_create(
        name=name,
        defaults={
            "description": f"Test role: {name}",
            "hierarchy_level": hierarchy_level,
        },
    )
    return role


def _assign_permission_to_role(role: Role, codename: str, app_label: str = "cases") -> None:
    """
    Attach a single Django permission to a role (no-op if already assigned).

    Permissions must already exist in the DB (populated by migrate).
    """
    perm = Permission.objects.get(codename=codename, content_type__app_label=app_label)
    role.permissions.add(perm)


# ═══════════════════════════════════════════════════════════════════
#  Test class
# ═══════════════════════════════════════════════════════════════════

class TestCrimeSceneCaseFlow(TestCase):
    """
    End-to-end integration tests for the crime-scene case creation path.

    Reference: project-doc.md §4.2.2 — "Case Creation via Crime Scene Registration"

    Approval rules implemented in cases/services.py:
      - Police Chief creator  → OPEN immediately (auto-approved)
      - Any rank below Chief  → PENDING_APPROVAL (one superior must approve)
      - Cadet / Base User     → 403 Forbidden

    All HTTP interactions go through real endpoints via APIClient.
    Users / roles are seeded in setUpTestData via the DB/model layer
    (permitted by the test constraints).
    """

    # ── Shared payload for a valid crime-scene case ─────────────────
    _VALID_PAYLOAD: dict = {
        "creation_type": "crime_scene",
        "title": "Armed Robbery at 5th Avenue",
        "description": "Two armed suspects robbed a jewelry store at gunpoint.",
        "crime_level": 2,           # Level 2 (Medium) — see CrimeLevel.LEVEL_2
        "incident_date": "2026-02-23T14:30:00Z",
        "location": "5th Avenue, Downtown LA",
        "witnesses": [
            {
                "full_name": "John Smith",
                "phone_number": "+12025551234",
                "national_id": "1234567890",
            }
        ],
    }

    @classmethod
    def setUpTestData(cls) -> None:
        """
        Create roles and users once for the entire test class.

        DB/model creation is allowed in setUpTestData.
        All scenario *actions* are performed via endpoints in each test.

        Roles and hierarchy levels follow project-doc.md §3.1 and
        the setup_rbac management command in accounts/management/commands/setup_rbac.py.
        """
        # ── Roles ────────────────────────────────────────────────────
        cls.chief_role    = _make_role("Police Chief",   hierarchy_level=10)
        cls.captain_role  = _make_role("Captain",        hierarchy_level=9)
        cls.officer_role  = _make_role("Police Officer", hierarchy_level=6)
        cls.cadet_role    = _make_role("Cadet",          hierarchy_level=1)
        cls.base_role     = _make_role("Base User",      hierarchy_level=0)

        # Grant the minimum permissions needed for case creation and approval.
        # Permission codenames are defined in core/permissions_constants.py.
        #
        # Police Officer and Captain need "add_case" so IsAuthenticated + service
        # role-name check passes.  Captain additionally needs "can_approve_case"
        # to run approve-crime-scene.
        #
        # The service layer does NOT check Django permissions for crime-scene
        # creation — it checks the role *name* only (see cases/services.py
        # `_CRIME_SCENE_FORBIDDEN_ROLES`).  We still attach "add_case" to
        # officer/captain/chief for completeness and realistic RBAC parity.
        for role in (cls.officer_role, cls.captain_role, cls.chief_role):
            _assign_permission_to_role(role, "add_case", app_label="cases")
            _assign_permission_to_role(role, "view_case", app_label="cases")

        # Captain and Chief can approve crime-scene cases.
        # Reference: cases_services_crime_scene_flow_report.md §1 "Who Can Approve?"
        for role in (cls.captain_role, cls.chief_role):
            _assign_permission_to_role(role, "can_approve_case", app_label="cases")

        # ── Users ────────────────────────────────────────────────────
        cls.officer_password = "0fficer!Pass99"
        cls.captain_password = "C@ptain!Pass99"
        cls.chief_password   = "Ch!ef!Pass9999"
        cls.cadet_password   = "C@det!Pass9999"

        cls.officer_user = User.objects.create_user(
            username="test_officer",
            password=cls.officer_password,
            email="officer@lapd.test",
            phone_number="09130000001",
            national_id="1000000001",
            first_name="John",
            last_name="Officer",
            role=cls.officer_role,
        )
        cls.captain_user = User.objects.create_user(
            username="test_captain",
            password=cls.captain_password,
            email="captain@lapd.test",
            phone_number="09130000002",
            national_id="1000000002",
            first_name="Jane",
            last_name="Captain",
            role=cls.captain_role,
        )
        cls.chief_user = User.objects.create_user(
            username="test_chief",
            password=cls.chief_password,
            email="chief@lapd.test",
            phone_number="09130000003",
            national_id="1000000003",
            first_name="James",
            last_name="Chief",
            role=cls.chief_role,
        )
        cls.cadet_user = User.objects.create_user(
            username="test_cadet",
            password=cls.cadet_password,
            email="cadet@lapd.test",
            phone_number="09130000004",
            national_id="1000000004",
            first_name="Jake",
            last_name="Cadet",
            role=cls.cadet_role,
        )

    def setUp(self) -> None:
        """Instantiate a fresh APIClient before every test method."""
        self.client = APIClient()

    # ────────────────────────────────────────────────────────────────
    #  Helpers
    # ────────────────────────────────────────────────────────────────

    def _login(self, username: str, password: str) -> str:
        """
        Log in via POST /api/accounts/auth/login/ and return the JWT access token.

        Login endpoint: accounts/urls.py → path("auth/login/", ...)
        Payload schema: {"identifier": <username|national_id|phone|email>, "password": <str>}
        Response schema: {"access": <str>, "refresh": <str>, ...}
        Reference: swagger_documentation_report.md §3.1 — LoginView.post
        """
        url = reverse("accounts:login")
        response = self.client.post(
            url,
            {"identifier": username, "password": password},
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Login failed for '{username}': {response.data}",
        )
        return response.data["access"]

    def _auth(self, token: str) -> None:
        """
        Set the Bearer token on the shared APIClient.

        Scheme: Authorization: Bearer <token>
        Reference: swagger_documentation_report.md §3.1 — SimpleJWT
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _login_as(self, username: str, password: str) -> None:
        """Convenience: login and immediately authenticate the client."""
        token = self._login(username, password)
        self._auth(token)

    def _create_crime_scene_case(self, payload: dict | None = None) -> "rest_framework.response.Response":  # type: ignore[name-defined]
        """
        POST the given payload to POST /api/cases/.

        If no payload is provided, _VALID_PAYLOAD is used.
        Reference: swagger_documentation_report.md §3.2 — CaseViewSet.create
        """
        data = payload if payload is not None else self._VALID_PAYLOAD
        return self.client.post(reverse("case-list"), data, format="json")

    # ────────────────────────────────────────────────────────────────
    #  Scenario 4.1 — Officer creates crime-scene case
    # ────────────────────────────────────────────────────────────────

    def test_officer_creates_crime_scene_case_returns_201(self) -> None:
        """
        Scenario 4.1 (step A): POST /api/cases/ as Police Officer returns HTTP 201.

        Reference:
          - project-doc.md §4.2.2 — "a police rank (other than Cadet) can
            register a crime scene"
          - cases_services_crime_scene_flow_report.md §4.1 Officer Path
          - swagger_documentation_report.md §3.2 — CaseViewSet.create → 201
        """
        self._login_as(self.officer_user.username, self.officer_password)
        response = self._create_crime_scene_case()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Expected 201 Created but got {response.status_code}: {response.data}",
        )

    def test_officer_crime_scene_case_has_id_in_response(self) -> None:
        """
        Scenario 4.1 (step B): Response body must include a case 'id' field.

        Reference: swagger_documentation_report.md §3.2 — CaseDetailSerializer fields
        """
        self._login_as(self.officer_user.username, self.officer_password)
        response = self._create_crime_scene_case()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(
            "id",
            response.data,
            msg="Response JSON must contain 'id' for the created case.",
        )
        self.assertIsNotNone(response.data["id"])

    def test_officer_crime_scene_case_initial_status_is_pending_approval(self) -> None:
        """
        Scenario 4.1 (core assertion): Initial status MUST be "pending_approval".

        Logic in cases/services.py CaseCreationService.create_crime_scene_case:
          - creator role != "police_chief" → CaseStatus.PENDING_APPROVAL
          - "pending_approval" is the exact enum value from CaseStatus.PENDING_APPROVAL

        Reference:
          - project-doc.md §4.2.2 — "only one superior rank needs to approve"
          - cases_services_crime_scene_flow_report.md §1 Approval Rules Table
          - cases/models.py CaseStatus.PENDING_APPROVAL = "pending_approval"
        """
        self._login_as(self.officer_user.username, self.officer_password)
        response = self._create_crime_scene_case()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data.get("status"),
            CaseStatus.PENDING_APPROVAL,   # "pending_approval"
            msg=(
                f"Expected status='pending_approval' for officer-created crime-scene case, "
                f"got '{response.data.get('status')}' instead."
            ),
        )

    def test_officer_crime_scene_case_persisted_fields_match(self) -> None:
        """
        Scenario 4.1 (persistence check): Fetch GET /api/cases/{id}/ and assert
        all submitted fields are correctly stored in the database.

        Reference:
          - swagger_documentation_report.md §3.2 — CaseViewSet.retrieve → 200
          - cases/serializers.py CaseDetailSerializer fields
        """
        self._login_as(self.officer_user.username, self.officer_password)
        create_response = self._create_crime_scene_case()
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        case_id = create_response.data["id"]
        detail_url = reverse("case-detail", kwargs={"pk": case_id})
        get_response = self.client.get(detail_url)

        self.assertEqual(
            get_response.status_code,
            status.HTTP_200_OK,
            msg=f"GET /api/cases/{case_id}/ failed: {get_response.data}",
        )

        data = get_response.data
        payload = self._VALID_PAYLOAD

        # Core fields
        self.assertEqual(data["title"],         payload["title"])
        self.assertEqual(data["description"],   payload["description"])
        self.assertEqual(data["crime_level"],   payload["crime_level"])
        self.assertEqual(data["location"],      payload["location"])
        self.assertEqual(data["creation_type"], "crime_scene")

        # Status persisted correctly
        self.assertEqual(
            data["status"],
            CaseStatus.PENDING_APPROVAL,
            msg="Persisted status in DB must be 'pending_approval'.",
        )

        # created_by must point to the Officer
        self.assertEqual(
            data["created_by"],
            self.officer_user.pk,
            msg="created_by must be set to the officer who submitted the case.",
        )

        # approved_by must be null for pending-approval cases
        self.assertIsNone(
            data.get("approved_by"),
            msg="approved_by must be None when case is pending approval.",
        )

    def test_officer_crime_scene_case_witness_persisted(self) -> None:
        """
        Scenario 4.1 (witness persistence): Witness supplied at creation
        must appear in the case detail response under 'witnesses'.

        Reference:
          - cases_services_crime_scene_flow_report.md §3 Witness Validation Rules
          - cases/serializers.py CaseWitnessSerializer
        """
        self._login_as(self.officer_user.username, self.officer_password)
        create_response = self._create_crime_scene_case()
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        case_id = create_response.data["id"]
        detail_url = reverse("case-detail", kwargs={"pk": case_id})
        get_response = self.client.get(detail_url)

        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        witnesses = get_response.data.get("witnesses", [])
        self.assertEqual(
            len(witnesses),
            1,
            msg="One witness was included in the payload; it must be persisted.",
        )
        witness = witnesses[0]
        expected_witness = self._VALID_PAYLOAD["witnesses"][0]
        self.assertEqual(witness["full_name"],    expected_witness["full_name"])
        self.assertEqual(witness["phone_number"], expected_witness["phone_number"])
        self.assertEqual(witness["national_id"],  expected_witness["national_id"])

    def test_officer_crime_scene_case_status_log_created(self) -> None:
        """
        Scenario 4.1 (audit trail): A CaseStatusLog entry must be created
        on case creation with to_status="pending_approval".

        Reference:
          - cases/services.py CaseCreationService.create_crime_scene_case
            (creates CaseStatusLog with from_status="" and to_status=PENDING_APPROVAL)
          - swagger_documentation_report.md §3.2 — CaseViewSet.status_log
        """
        self._login_as(self.officer_user.username, self.officer_password)
        create_response = self._create_crime_scene_case()
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        case_id = create_response.data["id"]

        # Verify via the status-log sub-resource endpoint
        log_url = reverse("case-status-log", kwargs={"pk": case_id})
        log_response = self.client.get(log_url)

        self.assertEqual(
            log_response.status_code,
            status.HTTP_200_OK,
            msg=f"GET /api/cases/{case_id}/status-log/ failed: {log_response.data}",
        )

        logs = log_response.data
        self.assertGreaterEqual(
            len(logs),
            1,
            msg="At least one status log entry must exist after case creation.",
        )

        # The initial log entry must record the transition to pending_approval
        creation_log = logs[0]
        self.assertEqual(
            creation_log["to_status"],
            CaseStatus.PENDING_APPROVAL,
            msg="First status-log entry must have to_status='pending_approval'.",
        )

        # Also verify directly in the ORM as a belt-and-suspenders check
        exists_in_db = CaseStatusLog.objects.filter(
            case_id=case_id,
            to_status=CaseStatus.PENDING_APPROVAL,
        ).exists()
        self.assertTrue(
            exists_in_db,
            msg="CaseStatusLog row with to_status='pending_approval' must exist in DB.",
        )

    def test_officer_crime_scene_case_without_witnesses_returns_201(self) -> None:
        """
        Scenario 4.1 (optional witnesses): Creating a crime-scene case with an
        empty witnesses list must still succeed with status 201.

        Reference: CrimeSceneCaseCreateSerializer — witnesses is required=False
        """
        self._login_as(self.officer_user.username, self.officer_password)
        payload = {
            **self._VALID_PAYLOAD,
            "witnesses": [],
        }
        response = self._create_crime_scene_case(payload)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Crime-scene case without witnesses must still be accepted: {response.data}",
        )
        self.assertEqual(response.data.get("status"), CaseStatus.PENDING_APPROVAL)

    def test_officer_crime_scene_case_missing_required_field_returns_400(self) -> None:
        """
        Scenario 4.1 (negative/validation): Omitting a required field
        (incident_date) must produce HTTP 400 Bad Request.

        Reference:
          - cases/serializers.py CrimeSceneCaseCreateSerializer
            incident_date is required=True for crime_scene path
        """
        self._login_as(self.officer_user.username, self.officer_password)
        payload = {
            "creation_type": "crime_scene",
            "title": "Test Missing Date",
            "description": "No incident_date supplied.",
            "crime_level": 1,
            "location": "Somewhere",
            # incident_date intentionally omitted
        }
        response = self._create_crime_scene_case(payload)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg="Missing required 'incident_date' must cause 400 Bad Request.",
        )

    def test_unauthenticated_request_returns_401(self) -> None:
        """
        Scenario 4.1 (auth guard): Unauthenticated POST /api/cases/ must
        return HTTP 401 Unauthorized.

        Reference:
          - cases/views.py CaseViewSet permission_classes = [IsAuthenticated]
        """
        # Do NOT call _auth — client is anonymous
        response = self._create_crime_scene_case()

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
            msg="Unauthenticated request must return 401.",
        )

    # ────────────────────────────────────────────────────────────────
    #  Scenario 4.2 — Approve pending_approval case (Captain / Chief)
    # ────────────────────────────────────────────────────────────────
    #
    # Business rule (project-doc.md §4.2.2):
    #   "In this scenario, only one superior rank needs to approve the
    #    case; if the Police Chief registers it, no one's approval is needed."
    #
    # Implementation (cases/services.py ALLOWED_TRANSITIONS):
    #   (PENDING_APPROVAL, OPEN): {CasesPerms.CAN_APPROVE_CASE}
    #
    # Endpoint: POST /api/cases/{id}/approve-crime-scene/
    #   No request body required (request=None per swagger decorator).
    #   Response: 200 + CaseDetailSerializer
    #
    # Approvers: Captain ✅  Chief ✅  (both have can_approve_case in setUpTestData)
    # Blocked:   Officer ❌  (can_approve_case NOT assigned to officer role)
    #
    # Ref: swagger_documentation_report.md §3.2 — CaseViewSet.approve_crime_scene
    # Ref: cases_services_crime_scene_flow_report.md §1 "Who Can Approve?"

    def _create_pending_case_as_officer(self) -> int:
        """
        Helper: login as Officer, create a crime-scene case, confirm 201 +
        pending_approval, and return the case's primary key.

        Used by all 4.2 tests to obtain a fresh PENDING_APPROVAL case.
        """
        self._login_as(self.officer_user.username, self.officer_password)
        response = self._create_crime_scene_case()
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Setup failed: could not create officer case: {response.data}",
        )
        self.assertEqual(
            response.data["status"],
            CaseStatus.PENDING_APPROVAL,
            msg="Setup sanity-check: newly created officer case must be pending_approval.",
        )
        return response.data["id"]

    def _approve_url(self, case_id: int) -> str:
        """Return the reverse URL for POST /api/cases/{id}/approve-crime-scene/."""
        return reverse("case-approve-crime-scene", kwargs={"pk": case_id})

    # ── Test A: Captain approves ──────────────────────────────────

    def test_captain_approves_pending_case_returns_200(self) -> None:
        """
        Scenario 4.2 — Test A (HTTP status): Captain POSTs to
        /api/cases/{id}/approve-crime-scene/ and receives HTTP 200.

        Reference:
          - swagger_documentation_report.md §3.2 — approve_crime_scene → 200
          - cases_services_crime_scene_flow_report.md §1 "Who Can Approve?"
        """
        case_id = self._create_pending_case_as_officer()

        # Re-authenticate as Captain
        self._login_as(self.captain_user.username, self.captain_password)
        response = self.client.post(self._approve_url(case_id))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Captain approval must return 200, got {response.status_code}: {response.data}",
        )

    def test_captain_approves_pending_case_status_becomes_open(self) -> None:
        """
        Scenario 4.2 — Test A (core assertion): After Captain approval,
        case status must be exactly "open".

        Reference:
          - cases/models.py CaseStatus.OPEN = "open"
          - cases/services.py ALLOWED_TRANSITIONS: PENDING_APPROVAL → OPEN
        """
        case_id = self._create_pending_case_as_officer()

        self._login_as(self.captain_user.username, self.captain_password)
        response = self.client.post(self._approve_url(case_id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data.get("status"),
            CaseStatus.OPEN,   # "open"
            msg=f"Case status after Captain approval must be 'open', got '{response.data.get('status')}'.",
        )

    def test_captain_approves_pending_case_approved_by_is_set(self) -> None:
        """
        Scenario 4.2 — Test A (approved_by): After Captain approval,
        approved_by in the response must be set to the Captain's user PK.

        Reference:
          - cases/services.py approve_crime_scene_case:
            "case.approved_by = requesting_user" before transitioning
          - cases/models.py Case.approved_by FK
        """
        case_id = self._create_pending_case_as_officer()

        self._login_as(self.captain_user.username, self.captain_password)
        response = self.client.post(self._approve_url(case_id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data.get("approved_by"),
            self.captain_user.pk,
            msg="approved_by must be set to the Captain's PK after approval.",
        )

    def test_captain_approves_pending_case_status_log_records_transition(self) -> None:
        """
        Scenario 4.2 — Test A (audit trail): GET /api/cases/{id}/status-log/
        must contain an entry with from_status="pending_approval" and
        to_status="open" after Captain approval.

        Reference:
          - cases/services.py transition_state: creates CaseStatusLog entry
          - swagger_documentation_report.md §3.2 — CaseViewSet.status_log
        """
        case_id = self._create_pending_case_as_officer()

        self._login_as(self.captain_user.username, self.captain_password)
        self.client.post(self._approve_url(case_id))

        # Re-authenticate as Officer to read the status log (has view_case perm)
        self._login_as(self.officer_user.username, self.officer_password)
        log_url = reverse("case-status-log", kwargs={"pk": case_id})
        log_response = self.client.get(log_url)

        self.assertEqual(log_response.status_code, status.HTTP_200_OK)

        approval_entries = [
            entry for entry in log_response.data
            if entry.get("from_status") == CaseStatus.PENDING_APPROVAL
            and entry.get("to_status") == CaseStatus.OPEN
        ]
        self.assertEqual(
            len(approval_entries),
            1,
            msg=(
                "Status log must contain exactly one PENDING_APPROVAL→OPEN entry "
                f"after Captain approval. Found: {log_response.data}"
            ),
        )

    def test_captain_approves_persisted_in_db(self) -> None:
        """
        Scenario 4.2 — Test A (persistence): GET /api/cases/{id}/ after
        approval must reflect status="open" and approved_by=captain stored in DB.
        """
        case_id = self._create_pending_case_as_officer()

        self._login_as(self.captain_user.username, self.captain_password)
        self.client.post(self._approve_url(case_id))

        # Read back via detail endpoint (Officer still has view_case)
        self._login_as(self.officer_user.username, self.officer_password)
        detail = self.client.get(reverse("case-detail", kwargs={"pk": case_id}))

        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data["status"], CaseStatus.OPEN)
        self.assertEqual(detail.data["approved_by"], self.captain_user.pk)

    # ── Test B: Chief approves ────────────────────────────────────

    def test_chief_approves_pending_case_returns_200_and_open(self) -> None:
        """
        Scenario 4.2 — Test B: Police Chief POSTs to approve-crime-scene/
        on a PENDING_APPROVAL case created by an Officer; expects 200 and
        status="open".

        Note: This is different from the Chief *creating* a case (Scenario 4.3
        where it auto-approves). Here the Chief is approving someone else's case.

        Reference:
          - cases_services_crime_scene_flow_report.md §1 "Who Can Approve?" → Chief ✅
          - cases/services.py ALLOWED_TRANSITIONS: PENDING_APPROVAL → OPEN
            requires CAN_APPROVE_CASE — Chief role has this in setUpTestData.
        """
        case_id = self._create_pending_case_as_officer()

        self._login_as(self.chief_user.username, self.chief_password)
        response = self.client.post(self._approve_url(case_id))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Chief approval must return 200, got {response.status_code}: {response.data}",
        )
        self.assertEqual(
            response.data.get("status"),
            CaseStatus.OPEN,
            msg="Case status after Chief approval must be 'open'.",
        )

    def test_chief_approves_pending_case_approved_by_is_chief(self) -> None:
        """
        Scenario 4.2 — Test B (approved_by): After Chief approval,
        approved_by must be the Chief's PK.

        Reference:
          - cases/services.py approve_crime_scene_case:
            case.approved_by = requesting_user (Chief in this case)
        """
        case_id = self._create_pending_case_as_officer()

        self._login_as(self.chief_user.username, self.chief_password)
        response = self.client.post(self._approve_url(case_id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data.get("approved_by"),
            self.chief_user.pk,
            msg="approved_by must be set to the Chief's PK when Chief approves.",
        )

    # ── Negative test: Officer cannot approve ─────────────────────

    def test_officer_cannot_approve_pending_case_returns_403(self) -> None:
        """
        Scenario 4.2 — Negative test: A Police Officer (who lacks
        can_approve_case permission) tries to approve a PENDING_APPROVAL
        case → must receive HTTP 403.

        Business rule: Only roles with can_approve_case may approve.
        Officer role was intentionally NOT granted can_approve_case in
        setUpTestData (see cases_services_crime_scene_flow_report.md §1).

        The domain PermissionDenied exception is mapped to 403 by the
        registered exception handler in:
          backend/backend/settings.py EXCEPTION_HANDLER →
          core.domain.exception_handler.domain_exception_handler
        """
        case_id = self._create_pending_case_as_officer()

        # Same Officer who created the case tries to approve it — not allowed
        # (Officer role has add_case but not can_approve_case)
        # Client is already authenticated as Officer from _create_pending_case_as_officer
        response = self.client.post(self._approve_url(case_id))

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=(
                f"Officer must receive 403 when attempting to approve a case. "
                f"Got {response.status_code}: {response.data}"
            ),
        )

    def test_approving_already_open_case_returns_error(self) -> None:
        """
        Scenario 4.2 — Negative test (idempotency): Attempting to approve
        a case that is already OPEN must fail with a non-2xx status (409 or 400).

        Reference:
          - cases/services.py approve_crime_scene_case:
              if case.status != PENDING_APPROVAL → raise InvalidTransition → 409
          - core.domain.exception_handler: InvalidTransition → 409
        """
        case_id = self._create_pending_case_as_officer()

        # First approval (valid — Captain)
        self._login_as(self.captain_user.username, self.captain_password)
        first = self.client.post(self._approve_url(case_id))
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        # Second approval attempt on the now-OPEN case
        second = self.client.post(self._approve_url(case_id))
        self.assertIn(
            second.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT],
            msg=(
                f"Approving an already-open case must return 400 or 409, "
                f"got {second.status_code}: {second.data}"
            ),
        )

    # ────────────────────────────────────────────────────────────────
    #  Scenario 4.3 — Police Chief creates crime-scene case (auto-open)
    # ────────────────────────────────────────────────────────────────
    #
    # Business rule (project-doc.md §4.2.2):
    #   "if the Police Chief registers it, no one's approval is needed."
    #
    # Implementation (cases/services.py CaseCreationService.create_crime_scene_case):
    #   _CHIEF_ROLE = "police_chief"
    #   get_user_role_name → role.name.lower().replace(" ", "_")
    #   "Police Chief" → "police_chief" == _CHIEF_ROLE  → True
    #   is_chief = True
    #   initial_status = CaseStatus.OPEN          (skips PENDING_APPROVAL)
    #   validated_data["approved_by"] = requesting_user  (Chief set as approver)
    #
    # Expected: 201 Created, status="open", approved_by=chief.pk
    # No call to approve-crime-scene/ is required or needed.
    #
    # Ref: swagger_documentation_report.md §3.2 — CaseViewSet.create → 201
    # Ref: cases_services_crime_scene_flow_report.md §4.2 Chief Path

    def test_chief_creates_crime_scene_case_returns_201(self) -> None:
        """
        Scenario 4.3 (step A): POST /api/cases/ as Police Chief returns HTTP 201.

        Reference: swagger_documentation_report.md §3.2 — CaseViewSet.create
        """
        self._login_as(self.chief_user.username, self.chief_password)
        response = self._create_crime_scene_case()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Chief case creation must return 201, got {response.status_code}: {response.data}",
        )

    def test_chief_creates_crime_scene_case_status_is_open(self) -> None:
        """
        Scenario 4.3 (core assertion): Case created by Police Chief must have
        status="open" immediately — no pending_approval step.

        Key logic in cases/services.py:
          is_chief = (get_user_role_name(user) == "police_chief")
          initial_status = CaseStatus.OPEN if is_chief else CaseStatus.PENDING_APPROVAL

        Reference:
          - project-doc.md §4.2.2 — "if the Police Chief registers it,
            no one's approval is needed"
          - cases/models.py CaseStatus.OPEN = "open"
        """
        self._login_as(self.chief_user.username, self.chief_password)
        response = self._create_crime_scene_case()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data.get("status"),
            CaseStatus.OPEN,    # "open" — NOT "pending_approval"
            msg=(
                f"Chief-created crime-scene case must have status='open', "
                f"got '{response.data.get('status')}'. "
                "Chief cases are auto-approved per project-doc.md §4.2.2."
            ),
        )

    def test_chief_creates_crime_scene_case_not_pending_approval(self) -> None:
        """
        Scenario 4.3 (explicit negative): The returned status must NOT be
        "pending_approval" when the creator is Police Chief.

        This assertion documents the contrast with Officer-created cases.
        """
        self._login_as(self.chief_user.username, self.chief_password)
        response = self._create_crime_scene_case()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(
            response.data.get("status"),
            CaseStatus.PENDING_APPROVAL,
            msg="Chief-created case must never be in 'pending_approval' status.",
        )

    def test_chief_creates_crime_scene_case_approved_by_is_chief(self) -> None:
        """
        Scenario 4.3 (auto-approved_by): approved_by in the creation response
        must be set to the Chief's PK.

        Logic in cases/services.py:
          if is_chief:
              validated_data["approved_by"] = requesting_user
          case = Case.objects.create(**validated_data)

        This means the Chief also serves as the approver of their own case,
        satisfying the approval requirement via auto-approval.

        Reference:
          - cases_services_crime_scene_flow_report.md §1 Approval Rules Table:
            "Police Chief → OPEN, Auto approved_by = Set to creator"
        """
        self._login_as(self.chief_user.username, self.chief_password)
        response = self._create_crime_scene_case()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data.get("approved_by"),
            self.chief_user.pk,
            msg=(
                f"approved_by must be set to Chief's PK ({self.chief_user.pk}) "
                f"on auto-approved creation, got '{response.data.get('approved_by')}'."
            ),
        )

    def test_chief_creates_crime_scene_case_detail_persisted(self) -> None:
        """
        Scenario 4.3 (persistence check): GET /api/cases/{id}/ confirms that
        status="open" and approved_by=chief are stored in the database.

        Reference: swagger_documentation_report.md §3.2 — CaseViewSet.retrieve
        """
        self._login_as(self.chief_user.username, self.chief_password)
        create_response = self._create_crime_scene_case()
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        case_id = create_response.data["id"]
        detail = self.client.get(reverse("case-detail", kwargs={"pk": case_id}))

        self.assertEqual(
            detail.status_code,
            status.HTTP_200_OK,
            msg=f"GET /api/cases/{case_id}/ failed: {detail.data}",
        )
        self.assertEqual(
            detail.data["status"],
            CaseStatus.OPEN,
            msg="Persisted status must be 'open' for Chief-created case.",
        )
        self.assertEqual(
            detail.data["approved_by"],
            self.chief_user.pk,
            msg="Persisted approved_by must be Chief's PK.",
        )
        self.assertEqual(
            detail.data["creation_type"],
            "crime_scene",
            msg="creation_type must be 'crime_scene'.",
        )

    def test_chief_creates_crime_scene_case_status_log_shows_open(self) -> None:
        """
        Scenario 4.3 (audit trail): GET /api/cases/{id}/status-log/ must show
        a direct creation log entry with to_status="open" (no pending_approval entry).

        Reference:
          - cases/services.py create_crime_scene_case:
              log_message = "Crime-scene case created and auto-approved (Police Chief)."
              CaseStatusLog.objects.create(from_status="", to_status=OPEN, ...)
        """
        self._login_as(self.chief_user.username, self.chief_password)
        create_response = self._create_crime_scene_case()
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        case_id = create_response.data["id"]
        log_url = reverse("case-status-log", kwargs={"pk": case_id})
        log_response = self.client.get(log_url)

        self.assertEqual(log_response.status_code, status.HTTP_200_OK)

        logs = log_response.data
        self.assertGreaterEqual(len(logs), 1, msg="At least one log entry must exist.")

        # The creation log must go directly to OPEN
        creation_log = logs[0]
        self.assertEqual(
            creation_log["to_status"],
            CaseStatus.OPEN,
            msg=(
                "Chief-created case log must show to_status='open' directly. "
                f"Got: {creation_log}"
            ),
        )

        # No entry must exist with to_status=PENDING_APPROVAL
        pending_entries = [
            e for e in logs if e.get("to_status") == CaseStatus.PENDING_APPROVAL
        ]
        self.assertEqual(
            len(pending_entries),
            0,
            msg=(
                "Chief-created case must have zero 'pending_approval' log entries. "
                f"Found: {pending_entries}"
            ),
        )

    def test_chief_case_approve_endpoint_returns_error(self) -> None:
        """
        Scenario 4.3 (no approval needed): Calling approve-crime-scene/ on a
        Chief-created case (already OPEN) must return a non-2xx error because
        the case is not in PENDING_APPROVAL status.

        This documents that the approval step is entirely skipped for Chief cases.

        Reference:
          - cases/services.py approve_crime_scene_case:
              if case.status != PENDING_APPROVAL → raise InvalidTransition → 409
          - project-doc.md §4.2.2: "if the Police Chief registers it,
            no one's approval is needed"
        """
        self._login_as(self.chief_user.username, self.chief_password)
        create_response = self._create_crime_scene_case()
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data["status"], CaseStatus.OPEN)

        case_id = create_response.data["id"]

        # Attempt to approve an already-open Chief case (Captain is the approver role)
        self._login_as(self.captain_user.username, self.captain_password)
        approve_response = self.client.post(self._approve_url(case_id))

        self.assertIn(
            approve_response.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT],
            msg=(
                "Calling approve-crime-scene/ on an already-open Chief case must "
                f"return 400 or 409, got {approve_response.status_code}: {approve_response.data}"
            ),
        )
