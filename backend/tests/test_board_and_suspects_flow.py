"""
Integration tests — Detective Board & Suspects Flow (Scenarios 6.1–6.8).

Business-flow reference : md-files/project-doc.md  §4.4, §4.5, §4.7
API endpoint reference  : md-files/swagger_documentation_report.md  §3.5, §3.3
Board service impl      : backend/board/services.py

All scenarios share ONE class so fixtures are created once via setUpTestData
and each test is isolated inside its own DB transaction (auto-rollback by
Django's TestCase).

Run with:
    python manage.py test tests.test_board_and_suspects_flow

Test map
--------
  6.1  Detective creates a board for an existing case
         A  POST /api/boards/ as Detective → 201 Created
         B  Response contains id, case (FK), and detective (FK = requesting user)
         C  GET /api/boards/{id}/ re-asserts ownership and linkage
         D  Unauthenticated POST → 401 Unauthorized
         E  Duplicate board for same case → 400 Bad Request
         F  Cadet (non-detective role) attempts to create board → 403 Forbidden
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role
from board.models import DetectiveBoard
from cases.models import Case, CaseCreationType, CrimeLevel, CaseStatus

User = get_user_model()


# ═══════════════════════════════════════════════════════════════════
#  Module-level helpers (reused across scenarios appended later)
# ═══════════════════════════════════════════════════════════════════

def _make_role(name: str, hierarchy_level: int) -> Role:
    """Get-or-create a Role by name (idempotent)."""
    role, _ = Role.objects.get_or_create(
        name=name,
        defaults={
            "description": f"Test role: {name}",
            "hierarchy_level": hierarchy_level,
        },
    )
    return role


def _assign_permission_to_role(
    role: Role,
    codename: str,
    app_label: str,
) -> None:
    """
    Attach a Django permission to a role, no-op if already assigned.

    The permission must already exist in the DB (populated by ``manage.py migrate``).
    """
    perm = Permission.objects.get(
        codename=codename,
        content_type__app_label=app_label,
    )
    role.permissions.add(perm)


def _make_open_case(created_by: "User", assigned_detective: "User | None" = None) -> Case:  # type: ignore[name-defined]
    """
    Create a Case in OPEN status directly in the DB.

    Board-creation in the service layer has no case-status guard, so any
    status works; OPEN is the most representative for active investigation.
    """
    return Case.objects.create(
        title="The Red Lipstick Murder",
        description="A homicide at Pershing Square. Multiple witnesses.",
        crime_level=CrimeLevel.LEVEL_1,
        status=CaseStatus.OPEN,
        creation_type=CaseCreationType.CRIME_SCENE,
        location="Pershing Square, Downtown LA",
        created_by=created_by,
        assigned_detective=assigned_detective or created_by,
    )


# ═══════════════════════════════════════════════════════════════════
#  Shared test class
# ═══════════════════════════════════════════════════════════════════


class TestBoardAndSuspectsFlow(TestCase):
    """
    End-to-end integration tests for the Detective Board and Suspects flow.

    Each *scenario* (6.1, 6.2, …) is a separate group of test methods.
    All tests share the same setUpTestData fixtures for performance, and
    each test is isolated via Django's per-test transaction rollback.

    Endpoint reference: swagger_documentation_report.md §3.5
    Board URL names (drf-nested-routers, basename="detective-board"):
        detective-board-list   →  POST  /api/boards/
        detective-board-detail →  GET   /api/boards/{id}/
    """

    # ── Reusable client payload ──────────────────────────────────────

    @classmethod
    def setUpTestData(cls) -> None:
        """
        Seed roles and users once for the entire class.

        All *actions* (HTTP calls) happen inside individual test methods.
        Direct DB creation is allowed here per the test constraints.

        Hierarchy levels follow project-doc.md §3.1 and setup_rbac.py:
            Police Chief = 10, Captain = 9, Sergeant = 8, Detective = 7,
            Police Officer = 6, Patrol Officer = 5, Cadet = 1.
        """
        # ── Roles ────────────────────────────────────────────────────
        cls.detective_role = _make_role("Detective", hierarchy_level=7)
        cls.sergeant_role  = _make_role("Sergeant",  hierarchy_level=8)
        cls.cadet_role     = _make_role("Cadet",      hierarchy_level=1)
        cls.officer_role   = _make_role("Police Officer", hierarchy_level=6)

        # Assign standard board CRUD permissions to the Detective role.
        # These match what setup_rbac.py configures in production.
        for codename in (
            "view_detectiveboard",
            "add_detectiveboard",
            "change_detectiveboard",
            "delete_detectiveboard",
        ):
            _assign_permission_to_role(cls.detective_role, codename, "board")

        # Sergeants can view boards (read-only supervisory access)
        _assign_permission_to_role(cls.sergeant_role, "view_detectiveboard", "board")

        # ── Users ────────────────────────────────────────────────────

        # Detective — the primary actor for Scenario 6.x board tests
        cls.detective_password = "D3tect!vePass99"
        cls.detective_user = User.objects.create_user(
            username="test_detective_board",
            password=cls.detective_password,
            email="detective_board@lapd.test",
            phone_number="09130000020",
            national_id="3000000020",
            first_name="Cole",
            last_name="Phelps",
            role=cls.detective_role,
        )

        # Sergeant — supervisor role used in later scenarios
        cls.sergeant_password = "Sgt!PassW0rd99"
        cls.sergeant_user = User.objects.create_user(
            username="test_sergeant_board",
            password=cls.sergeant_password,
            email="sergeant_board@lapd.test",
            phone_number="09130000021",
            national_id="3000000021",
            first_name="Tom",
            last_name="Biggs",
            role=cls.sergeant_role,
        )

        # Cadet — low-privilege role for negative permission tests
        cls.cadet_password = "C@det!PassW0rd9"
        cls.cadet_user = User.objects.create_user(
            username="test_cadet_board",
            password=cls.cadet_password,
            email="cadet_board@lapd.test",
            phone_number="09130000022",
            national_id="3000000022",
            first_name="Bob",
            last_name="Cadet",
            role=cls.cadet_role,
        )

        # ── Seed case for board-creation tests ──────────────────────
        # Created in OPEN status; assigned_detective = detective_user so
        # _is_assigned_to_case() returns True for the board owner.
        cls.case = _make_open_case(
            created_by=cls.detective_user,
            assigned_detective=cls.detective_user,
        )

    def setUp(self) -> None:
        """Fresh APIClient before each test; no auth header applied yet."""
        self.client = APIClient()

    # ─────────────────────────────────────────────────────────────────
    #  Helpers
    # ─────────────────────────────────────────────────────────────────

    def _login(self, username: str, password: str) -> str:
        """
        POST /api/accounts/auth/login/ → return JWT access token.

        Payload:  {"identifier": <username>, "password": <str>}
        Response: {"access": <str>, "refresh": <str>}
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
        """Set HTTP Authorization: Bearer <token> on the shared client."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _login_as(self, username: str, password: str) -> None:
        """Login and immediately authenticate the client (convenience)."""
        token = self._login(username, password)
        self._auth(token)

    def _create_board(self, case_pk: int | None = None) -> "rest_framework.response.Response":  # type: ignore[name-defined]
        """
        POST /api/boards/ with a case FK payload.

        Reference: swagger_documentation_report.md §3.5 — DetectiveBoardViewSet.create
        Request schema: DetectiveBoardCreateUpdateSerializer → {"case": <int>}
        """
        payload = {"case": case_pk if case_pk is not None else self.case.pk}
        return self.client.post(
            reverse("detective-board-list"),
            payload,
            format="json",
        )

    def _get_board(self, board_id: int) -> "rest_framework.response.Response":  # type: ignore[name-defined]
        """
        GET /api/boards/{id}/ — retrieve board detail.

        Reference: swagger_documentation_report.md §3.5 — DetectiveBoardViewSet.retrieve
        """
        return self.client.get(
            reverse("detective-board-detail", kwargs={"pk": board_id}),
            format="json",
        )

    # ─────────────────────────────────────────────────────────────────
    #  Scenario 6.1 — Detective creates a board for an existing case
    # ─────────────────────────────────────────────────────────────────

    # ── 6.1-A: happy path — 201 Created ─────────────────────────────

    def test_6_1_a_detective_creates_board_returns_201(self) -> None:
        """
        Scenario 6.1-A: POST /api/boards/ as Detective → HTTP 201 Created.

        Reference:
          - project-doc.md §4.4   — "The Detective has a 'Detective Board'"
          - swagger_doc §3.5      — DetectiveBoardViewSet.create → 201
          - board/services.py     — BoardWorkspaceService.create_board
        """
        self._login_as(self.detective_user.username, self.detective_password)
        response = self._create_board()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=(
                f"Expected HTTP 201 Created when Detective POSTs /api/boards/ "
                f"for an open case, but got {response.status_code}: {response.data}"
            ),
        )

    # ── 6.1-B: response body contains id, case, and detective ───────

    def test_6_1_b_created_board_response_contains_id_case_detective(self) -> None:
        """
        Scenario 6.1-B: Response JSON must contain 'id', 'case', and 'detective'.

        Field definitions:
          - 'id'         → PK of the new DetectiveBoard
          - 'case'       → FK integer pointing to cls.case
          - 'detective'  → FK integer pointing to the requesting user
            (set automatically by BoardWorkspaceService.create_board)

        Reference:
          - board/serializers.py  — DetectiveBoardListSerializer.fields
          - swagger_doc §3.5      — create 201 response schema
        """
        self._login_as(self.detective_user.username, self.detective_password)
        response = self._create_board()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertIn("id", response.data, msg="Response must include 'id'.")
        self.assertIn("case", response.data, msg="Response must include 'case'.")
        self.assertIn("detective", response.data, msg="Response must include 'detective'.")

        # Board must be linked to the correct case
        self.assertEqual(
            response.data["case"],
            self.case.pk,
            msg=(
                f"Board 'case' field should be {self.case.pk} "
                f"but got {response.data.get('case')}."
            ),
        )

    def test_6_1_b_created_board_detective_field_equals_requesting_user(self) -> None:
        """
        Scenario 6.1-B (ownership): 'detective' in response must equal the
        requesting user's PK — not any user supplied in the payload.

        The service sets detective = request.user unconditionally.
        Reference: board/services.py — create_board validated_data["detective"] = requesting_user
        """
        self._login_as(self.detective_user.username, self.detective_password)
        response = self._create_board()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["detective"],
            self.detective_user.pk,
            msg=(
                f"Board must be owned by the requesting detective (pk={self.detective_user.pk}), "
                f"but 'detective' field returned {response.data.get('detective')}."
            ),
        )

    # ── 6.1-C: GET board detail re-asserts ownership and linkage ────

    def test_6_1_c_get_board_detail_returns_correct_case_and_detective(self) -> None:
        """
        Scenario 6.1-C: After creation, GET /api/boards/{id}/ should return the
        same case and detective FK values.

        Reference:
          - swagger_doc §3.5 — DetectiveBoardViewSet.retrieve
          - board/serializers.py — DetectiveBoardListSerializer
        """
        self._login_as(self.detective_user.username, self.detective_password)

        # Create the board first
        create_response = self._create_board()
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        board_id = create_response.data["id"]

        # Retrieve the board
        get_response = self._get_board(board_id)
        self.assertEqual(
            get_response.status_code,
            status.HTTP_200_OK,
            msg=f"GET /api/boards/{board_id}/ failed: {get_response.data}",
        )

        self.assertEqual(
            get_response.data["id"],
            board_id,
            msg="Retrieved board id must match created board id.",
        )
        self.assertEqual(
            get_response.data["case"],
            self.case.pk,
            msg="Retrieved board 'case' FK must match the original case.",
        )
        self.assertEqual(
            get_response.data["detective"],
            self.detective_user.pk,
            msg="Retrieved board 'detective' FK must match the creating detective.",
        )

    def test_6_1_c_get_board_detail_persists_in_db(self) -> None:
        """
        Scenario 6.1-C (DB check): board created via API must be persisted
        and queryable via ORM.
        """
        self._login_as(self.detective_user.username, self.detective_password)

        create_response = self._create_board()
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        board_id = create_response.data["id"]

        # Verify DB record exists with correct relations
        board = DetectiveBoard.objects.get(pk=board_id)
        self.assertEqual(board.case_id, self.case.pk)
        self.assertEqual(board.detective_id, self.detective_user.pk)

    # ── 6.1-D: unauthenticated POST → 401 ───────────────────────────

    def test_6_1_d_unauthenticated_create_board_returns_401(self) -> None:
        """
        Scenario 6.1-D: POST /api/boards/ without Authorization header → 401.

        The view uses permission_classes = [IsAuthenticated].  Any request
        lacking a valid JWT is rejected before reaching the service layer.

        Reference: board/views.py — DetectiveBoardViewSet.permission_classes
        """
        # No _auth() call — client has no credentials
        response = self._create_board()

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
            msg=(
                f"Expected 401 Unauthorized for unauthenticated board creation, "
                f"but got {response.status_code}: {response.data}"
            ),
        )

    # ── 6.1-E: duplicate board for same case → 400 ──────────────────

    def test_6_1_e_duplicate_board_for_same_case_returns_400(self) -> None:
        """
        Scenario 6.1-E: Creating a second board for the same case must fail.

        The serializer's validate_case() raises a ValidationError when a
        board already exists for the given case, which DRF converts to 400.

        Reference:
          - board/serializers.py — DetectiveBoardCreateUpdateSerializer.validate_case
          - board/services.py    — BoardWorkspaceService.create_board (DomainError guard)
        """
        self._login_as(self.detective_user.username, self.detective_password)

        # First creation — must succeed
        first_response = self._create_board()
        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
            msg=f"First board creation should succeed: {first_response.data}",
        )

        # Second creation for the same case — must fail
        second_response = self._create_board()
        self.assertEqual(
            second_response.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=(
                f"Expected 400 Bad Request for duplicate board creation, "
                f"but got {second_response.status_code}: {second_response.data}"
            ),
        )

    # ── 6.1-F: non-detective (Cadet) creates board ───────────────────

    def test_6_1_f_cadet_creates_board_returns_403(self) -> None:
        """
        Scenario 6.1-F: Cadet (low-privilege role) attempts POST /api/boards/
        → HTTP 403 Forbidden.

        Reference:
          - project-doc.md §4.4 — boards belong to the Detective; only
            Detectives (and supervisory ranks) may open one.
          - board/services.py   — BoardWorkspaceService.create_board calls
            _can_create_board() and raises PermissionDenied for ineligible roles.
        """
        self._login_as(self.cadet_user.username, self.cadet_password)
        response = self._create_board()

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=(
                f"Expected 403 Forbidden when a Cadet attempts to create a board, "
                f"but got {response.status_code}: {response.data}"
            ),
        )
