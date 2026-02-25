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

  6.2  Get full board state
         A  Empty board → 200 with id/case/detective/items/connections/notes keys; all lists are []
         B  After adding a note the items and notes lists are non-empty and conform to schema
         C  After adding a connection the connections list is non-empty and conforms to schema
         D  Unrelated user (not assigned to the case) → 403 Forbidden

  6.3  Add board item (pin) referencing an Evidence object
         A  Detective pins an Evidence object → 201 with full item schema
         B  Response content_object_summary has required discovery fields
         C  Pinned item visible in GET /boards/{id}/full/ items list
         D  Duplicate pin of the same object → 400 Bad Request
         E  Invalid object_id (non-existent) → 400
         F  Invalid content_type_id (non-existent) → 400
         G  Disallowed content_type (e.g. accounts.user) → 400
         H  Unrelated user (Cadet, not assigned) tries to pin → 403

  6.4  Create a connection (red string) between two board items
         A  POST /boards/{id}/connections/ → 201 with id, from_item, to_item, label
         B  Created connection visible in GET /boards/{id}/full/ connections list
         C  Self-loop connection (from_item == to_item) → 400
         D  Item belonging to a different board → 400 (cross-board guard)
         E  Unrelated user tries to create connection → 403

  6.5  Batch update item coordinates (drag-and-drop save)
         A  PATCH /boards/{id}/items/batch-coordinates/ with 2 items → 200; response lists both
         B  Updated coordinates persist: GET /boards/{id}/full/ reflects new positions
         C  Payload includes item from a different board → 400
         D  Duplicate item IDs in same batch → 400 (serializer guard)
         E  Unrelated user (Cadet) → 403
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from django.contrib.contenttypes.models import ContentType

from accounts.models import Role
from board.models import DetectiveBoard
from cases.models import Case, CaseCreationType, CrimeLevel, CaseStatus
from evidence.models import Evidence, EvidenceType

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

    # ─────────────────────────────────────────────────────────────────
    #  Scenario 6.2 helpers
    # ─────────────────────────────────────────────────────────────────

    def _get_full_state(self, board_id: int) -> "rest_framework.response.Response":  # type: ignore[name-defined]
        """
        GET /api/boards/{id}/full/ — full board graph.

        Returns: FullBoardStateSerializer payload:
            { id, case, detective, items[], connections[], notes[],
              created_at, updated_at }

        Reference: swagger_documentation_report.md §3.5
                   DetectiveBoardViewSet.full_state → GET /api/boards/{id}/full/
        """
        return self.client.get(
            reverse("detective-board-full-state", kwargs={"pk": board_id}),
            format="json",
        )

    def _add_note(self, board_id: int, title: str = "Test Note", content: str = "Body") -> "rest_framework.response.Response":  # type: ignore[name-defined]
        """
        POST /api/boards/{board_pk}/notes/ — create a sticky note.

        Side-effect: BoardNoteService.create_note also auto-pins the new
        note as a BoardItem (content_type=board.boardnote, object_id=note.pk)
        so the board's items list grows by 1 simultaneously.

        Reference: swagger_documentation_report.md §3.5 — BoardNoteViewSet.create
                   board/services.py — BoardNoteService.create_note
        """
        return self.client.post(
            reverse("board-note-list", kwargs={"board_pk": board_id}),
            {"title": title, "content": content},
            format="json",
        )

    def _add_connection(self, board_id: int, from_item_id: int, to_item_id: int, label: str = "related") -> "rest_framework.response.Response":  # type: ignore[name-defined]
        """
        POST /api/boards/{board_pk}/connections/ — draw a red-line connection.

        Reference: swagger_documentation_report.md §3.5
                   BoardConnectionViewSet.create
        """
        return self.client.post(
            reverse("board-connection-list", kwargs={"board_pk": board_id}),
            {"from_item": from_item_id, "to_item": to_item_id, "label": label},
            format="json",
        )

    # ─────────────────────────────────────────────────────────────────
    #  Scenario 6.2 — Get full board state
    # ─────────────────────────────────────────────────────────────────

    # ── 6.2-A: empty board returns correct top-level shape ───────────

    def test_6_2_a_empty_board_full_state_returns_200_with_correct_keys(self) -> None:
        """
        Scenario 6.2-A: GET /api/boards/{id}/full/ on a freshly created board
        → HTTP 200 with all required top-level keys; all sub-lists are empty.

        FullBoardStateSerializer fields (board/serializers.py):
            id, case, detective, items [], connections [], notes [],
            created_at, updated_at

        Reference:
          - swagger_documentation_report.md §3.5
            DetectiveBoardViewSet.full_state → 200, FullBoardStateSerializer
          - project-doc.md §4.4 — board must expose items, connections, notes
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id = self._create_board().data["id"]

        response = self._get_full_state(board_id)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Expected 200 from full-state endpoint, got {response.status_code}: {response.data}",
        )

        # Metadata keys
        for key in ("id", "case", "detective", "created_at", "updated_at"):
            self.assertIn(key, response.data, msg=f"Top-level key '{key}' missing from full-state response.")

        # Sub-lists must be present
        for key in ("items", "connections", "notes"):
            self.assertIn(key, response.data, msg=f"'{key}' list missing from full-state response.")
            self.assertIsInstance(response.data[key], list, msg=f"'{key}' must be a list.")

        # Empty board → all lists are []
        self.assertEqual(response.data["items"], [], msg="Fresh board must have no items.")
        self.assertEqual(response.data["connections"], [], msg="Fresh board must have no connections.")
        self.assertEqual(response.data["notes"], [], msg="Fresh board must have no notes.")

    def test_6_2_a_full_state_metadata_matches_board(self) -> None:
        """
        Scenario 6.2-A (metadata check): id, case, and detective in the
        full-state response must match the values returned at creation time.
        """
        self._login_as(self.detective_user.username, self.detective_password)
        create_resp = self._create_board()
        board_id = create_resp.data["id"]

        full_resp = self._get_full_state(board_id)
        self.assertEqual(full_resp.status_code, status.HTTP_200_OK)

        self.assertEqual(full_resp.data["id"], board_id)
        self.assertEqual(full_resp.data["case"], self.case.pk)
        self.assertEqual(full_resp.data["detective"], self.detective_user.pk)

    # ── 6.2-B: note in list; item auto-pinned ────────────────────────

    def test_6_2_b_added_note_appears_in_notes_list(self) -> None:
        """
        Scenario 6.2-B: After POST /api/boards/{id}/notes/, the full-state
        'notes' list contains the new note with the correct schema.

        BoardNoteInlineSerializer fields:
            id, title, content, created_by, created_at, updated_at

        Reference:
          - board/serializers.py — BoardNoteInlineSerializer
          - board/services.py    — BoardNoteService.create_note
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id = self._create_board().data["id"]

        note_resp = self._add_note(board_id, title="Witness Statement", content="Saw a blue car.")
        self.assertEqual(note_resp.status_code, status.HTTP_201_CREATED,
                         msg=f"Note creation failed: {note_resp.data}")

        full_resp = self._get_full_state(board_id)
        self.assertEqual(full_resp.status_code, status.HTTP_200_OK)

        notes = full_resp.data["notes"]
        self.assertEqual(len(notes), 1, msg=f"Expected 1 note, got {len(notes)}.")

        note = notes[0]
        for field in ("id", "title", "content", "created_by", "created_at", "updated_at"):
            self.assertIn(field, note, msg=f"Note field '{field}' missing from full-state notes list.")

        self.assertEqual(note["title"], "Witness Statement")
        self.assertEqual(note["content"], "Saw a blue car.")
        self.assertEqual(note["created_by"], self.detective_user.pk)

    def test_6_2_b_note_creation_auto_pins_item_on_board(self) -> None:
        """
        Scenario 6.2-B (auto-pin): BoardNoteService.create_note creates a
        corresponding BoardItem for the note, so 'items' list has 1 entry
        after a single note is created.

        BoardItemInlineSerializer fields:
            id, content_type, object_id, content_object_summary,
            position_x, position_y, created_at, updated_at

        Reference:
          - board/services.py — BoardNoteService.create_note → auto pins
            the note as a BoardItem via ContentType for board.BoardNote
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id = self._create_board().data["id"]
        self._add_note(board_id, title="Auto-pin note")

        full_resp = self._get_full_state(board_id)
        self.assertEqual(full_resp.status_code, status.HTTP_200_OK)

        items = full_resp.data["items"]
        self.assertEqual(len(items), 1, msg="One note should produce exactly one auto-pinned item.")

        item = items[0]
        for field in ("id", "content_type", "object_id", "position_x", "position_y",
                      "created_at", "updated_at"):
            self.assertIn(field, item, msg=f"Item field '{field}' missing.")

        # content_object_summary is populated by GenericObjectRelatedField
        self.assertIn("content_object_summary", item,
                      msg="'content_object_summary' must be present in item.")

    # ── 6.2-C: connection appears in connections list ────────────────

    def test_6_2_c_added_connection_appears_in_connections_list(self) -> None:
        """
        Scenario 6.2-C: After creating two notes (→ two auto-pinned items)
        and a connection between them, the full-state 'connections' list
        contains the connection with the correct schema.

        BoardConnectionInlineSerializer fields:
            id, from_item, to_item, label, created_at, updated_at

        Reference:
          - swagger_documentation_report.md §3.5
            BoardConnectionViewSet.create → POST /api/boards/{id}/connections/
          - board/serializers.py — BoardConnectionInlineSerializer
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id = self._create_board().data["id"]

        # Create two notes — each auto-pins one item
        self._add_note(board_id, title="Note A")
        self._add_note(board_id, title="Note B")

        # Get the auto-pinned item IDs from items list
        full_resp = self._get_full_state(board_id)
        items = full_resp.data["items"]
        self.assertEqual(len(items), 2, msg="Expected 2 auto-pinned items after two notes.")
        item_a_id = items[0]["id"]
        item_b_id = items[1]["id"]

        # Create a connection between the two items
        conn_resp = self._add_connection(board_id, item_a_id, item_b_id, label="connected clue")
        self.assertEqual(conn_resp.status_code, status.HTTP_201_CREATED,
                         msg=f"Connection creation failed: {conn_resp.data}")

        # Re-fetch full state and check connections
        full_resp2 = self._get_full_state(board_id)
        self.assertEqual(full_resp2.status_code, status.HTTP_200_OK)

        connections = full_resp2.data["connections"]
        self.assertEqual(len(connections), 1, msg=f"Expected 1 connection, got {len(connections)}.")

        conn = connections[0]
        for field in ("id", "from_item", "to_item", "label", "created_at", "updated_at"):
            self.assertIn(field, conn, msg=f"Connection field '{field}' missing.")

        self.assertEqual(conn["from_item"], item_a_id)
        self.assertEqual(conn["to_item"], item_b_id)
        self.assertEqual(conn["label"], "connected clue")

    def test_6_2_c_full_state_reflects_all_three_lists_simultaneously(self) -> None:
        """
        Scenario 6.2-C (combined): After adding two notes and a connection,
        a single GET /api/boards/{id}/full/ returns all three lists populated.
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id = self._create_board().data["id"]

        self._add_note(board_id, title="Hair sample analysis")
        self._add_note(board_id, title="Speakeasy matchbook")

        items = self._get_full_state(board_id).data["items"]
        self._add_connection(board_id, items[0]["id"], items[1]["id"], label="crime scene link")

        full_resp = self._get_full_state(board_id)
        self.assertEqual(full_resp.status_code, status.HTTP_200_OK)

        self.assertEqual(len(full_resp.data["items"]), 2)
        self.assertEqual(len(full_resp.data["notes"]), 2)
        self.assertEqual(len(full_resp.data["connections"]), 1)

    # ── 6.2-D: unrelated user cannot access full state ───────────────

    def test_6_2_d_unrelated_user_cannot_access_full_state_returns_403(self) -> None:
        """
        Scenario 6.2-D: A user who is not the board's detective, not a
        supervisor assigned to the case, and not an admin gets HTTP 403
        when requesting GET /api/boards/{id}/full/.

        Access check: board/services.py — _can_view_board()
          → grants access only to the board's detective, assigned supervisors,
            or admins.  Cadet is none of those.

        Reference:
          - board/services.py    — BoardWorkspaceService.get_board_snapshot
          - board_services_report.md §1 Read Access table
        """
        # Detective creates the board
        self._login_as(self.detective_user.username, self.detective_password)
        board_id = self._create_board().data["id"]

        # Cadet (unrelated, not assigned to the case) tries to read full state
        self._login_as(self.cadet_user.username, self.cadet_password)
        response = self._get_full_state(board_id)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=(
                f"Expected 403 Forbidden when an unrelated user accesses full board state, "
                f"but got {response.status_code}: {response.data}"
            ),
        )

    # ─────────────────────────────────────────────────────────────────
    #  Scenario 6.3 helpers
    # ─────────────────────────────────────────────────────────────────

    def _add_item(self, board_id: int, content_type_id: int, object_id: int,
                  position_x: float = 100.0, position_y: float = 200.0,
                  ) -> "rest_framework.response.Response":  # type: ignore[name-defined]
        """
        POST /api/boards/{board_pk}/items/ — pin a content object to the board.

        Payload schema (BoardItemCreateSerializer → GenericObjectRelatedField):
            {
              "content_object": {"content_type_id": <int>, "object_id": <int>},
              "position_x": <float>,
              "position_y": <float>
            }

        Reference: swagger_documentation_report.md §3.5
                   BoardItemViewSet.create → POST /api/boards/{board_pk}/items/
        """
        return self.client.post(
            reverse("board-item-list", kwargs={"board_pk": board_id}),
            {
                "content_object": {
                    "content_type_id": content_type_id,
                    "object_id": object_id,
                },
                "position_x": position_x,
                "position_y": position_y,
            },
            format="json",
        )

    def _make_evidence(self) -> Evidence:
        """
        Create an Evidence (type OTHER) linked to ``cls.case`` directly in DB.

        Direct DB creation is allowed for setup fixtures per the test constraints.
        Using EvidenceType.OTHER requires only the base Evidence table — no
        child sub-type is needed.
        """
        return Evidence.objects.create(
            case=self.case,
            evidence_type=EvidenceType.OTHER,
            title="Bloodstained Jacket",
            description="Found near the back entrance of the jazz club.",
            registered_by=self.detective_user,
        )

    # ─────────────────────────────────────────────────────────────────
    #  Scenario 6.3 — Add board item (pin) referencing an Evidence object
    # ─────────────────────────────────────────────────────────────────

    # ── 6.3-A: happy path — 201 and full item schema ─────────────────

    def test_6_3_a_detective_pins_evidence_returns_201(self) -> None:
        """
        Scenario 6.3-A: POST /api/boards/{board_id}/items/ with a valid
        evidence reference → HTTP 201 Created.

        Payload: {"content_object": {"content_type_id": <ct>, "object_id": <ev>},
                  "position_x": 150.0, "position_y": 250.0}

        Reference:
          - project-doc.md §4.4 — Detective places evidence on the board
          - swagger_doc §3.5    — BoardItemViewSet.create → 201
          - board/serializers.py — BoardItemCreateSerializer + GenericObjectRelatedField
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id = self._create_board().data["id"]
        evidence = self._make_evidence()
        ct = ContentType.objects.get(app_label="evidence", model="evidence")

        response = self._add_item(board_id, ct.pk, evidence.pk, 150.0, 250.0)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Expected 201 when pinning evidence, got {response.status_code}: {response.data}",
        )

    def test_6_3_a_pin_response_contains_required_fields(self) -> None:
        """
        Scenario 6.3-A (schema): BoardItemResponseSerializer fields:
            id, board, content_type, object_id, content_object_summary,
            position_x, position_y, created_at, updated_at

        Reference: board/serializers.py — BoardItemResponseSerializer
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id = self._create_board().data["id"]
        evidence = self._make_evidence()
        ct = ContentType.objects.get(app_label="evidence", model="evidence")

        response = self._add_item(board_id, ct.pk, evidence.pk, 150.0, 250.0)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        for field in ("id", "board", "content_type", "object_id",
                      "content_object_summary", "position_x", "position_y",
                      "created_at", "updated_at"):
            self.assertIn(field, response.data,
                          msg=f"BoardItem response missing field '{field}'.")

        self.assertEqual(response.data["board"], board_id)
        self.assertEqual(response.data["object_id"], evidence.pk)
        self.assertAlmostEqual(float(response.data["position_x"]), 150.0)
        self.assertAlmostEqual(float(response.data["position_y"]), 250.0)

    # ── 6.3-B: content_object_summary discovery fields ───────────────

    def test_6_3_b_content_object_summary_contains_discovery_fields(self) -> None:
        """
        Scenario 6.3-B: content_object_summary resolved by
        GenericObjectRelatedField.to_representation must contain:
            content_type_id, app_label, model, object_id, display_name, detail_url

        These let the frontend render the correct icon and lazy-load the
        full object if needed.

        Reference: board/serializers.py — GenericObjectRelatedField.to_representation
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id = self._create_board().data["id"]
        evidence = self._make_evidence()
        ct = ContentType.objects.get(app_label="evidence", model="evidence")

        response = self._add_item(board_id, ct.pk, evidence.pk)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        summary = response.data["content_object_summary"]
        self.assertIsNotNone(summary, msg="content_object_summary must not be None.")

        for field in ("content_type_id", "app_label", "model", "object_id",
                      "display_name", "detail_url"):
            self.assertIn(field, summary,
                          msg=f"content_object_summary missing field '{field}'.")

        self.assertEqual(summary["app_label"], "evidence")
        self.assertEqual(summary["model"], "evidence")
        self.assertEqual(summary["object_id"], evidence.pk)
        self.assertIn("/api/evidence/", summary["detail_url"],
                      msg="detail_url must point to /api/evidence/")
        self.assertEqual(summary["display_name"], str(evidence))

    # ── 6.3-C: pinned item visible in full board state ───────────────

    def test_6_3_c_pinned_item_appears_in_full_state_items_list(self) -> None:
        """
        Scenario 6.3-C: After pinning, GET /api/boards/{id}/full/ items list
        must contain the new item with matching object_id and position fields.

        Reference:
          - swagger_doc §3.5 — DetectiveBoardViewSet.full_state
          - board/serializers.py — BoardItemInlineSerializer
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id = self._create_board().data["id"]
        evidence = self._make_evidence()
        ct = ContentType.objects.get(app_label="evidence", model="evidence")

        pin_resp = self._add_item(board_id, ct.pk, evidence.pk, 111.0, 222.0)
        self.assertEqual(pin_resp.status_code, status.HTTP_201_CREATED)
        item_id = pin_resp.data["id"]

        full_resp = self._get_full_state(board_id)
        self.assertEqual(full_resp.status_code, status.HTTP_200_OK)

        items = full_resp.data["items"]
        self.assertEqual(len(items), 1, msg=f"Expected 1 item in full state, got {len(items)}.")

        item = items[0]
        self.assertEqual(item["id"], item_id)
        self.assertEqual(item["object_id"], evidence.pk)
        self.assertAlmostEqual(float(item["position_x"]), 111.0)
        self.assertAlmostEqual(float(item["position_y"]), 222.0)

    # ── 6.3-D: duplicate pin → 400 ───────────────────────────────────

    def test_6_3_d_duplicate_pin_of_same_evidence_returns_400(self) -> None:
        """
        Scenario 6.3-D: Pinning the same evidence object twice on the same
        board must fail with HTTP 400.

        The service guard:
            board/services.py — BoardItemService.add_item
            → raises DomainError("This object is already pinned to the board.")

        Reference: board/services.py — BoardItemService.add_item
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id = self._create_board().data["id"]
        evidence = self._make_evidence()
        ct = ContentType.objects.get(app_label="evidence", model="evidence")

        first = self._add_item(board_id, ct.pk, evidence.pk)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED,
                         msg=f"First pin must succeed: {first.data}")

        second = self._add_item(board_id, ct.pk, evidence.pk)
        self.assertEqual(
            second.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Expected 400 for duplicate pin, got {second.status_code}: {second.data}",
        )

    # ── 6.3-E: non-existent object_id → 400 ─────────────────────────

    def test_6_3_e_invalid_object_id_returns_400(self) -> None:
        """
        Scenario 6.3-E: Supplying a valid content_type_id but a non-existent
        object_id must return HTTP 400.

        GenericObjectRelatedField.to_internal_value raises ValidationError:
            "Object with id {object_id} does not exist for type '{key}'."

        Reference: board/serializers.py — GenericObjectRelatedField.to_internal_value
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id = self._create_board().data["id"]
        ct = ContentType.objects.get(app_label="evidence", model="evidence")

        response = self._add_item(board_id, ct.pk, object_id=99999999)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Expected 400 for non-existent object_id, got {response.status_code}: {response.data}",
        )

    # ── 6.3-F: non-existent content_type_id → 400 ───────────────────

    def test_6_3_f_invalid_content_type_id_returns_400(self) -> None:
        """
        Scenario 6.3-F: Supplying a content_type_id that does not exist in
        the ContentType table must return HTTP 400.

        GenericObjectRelatedField.to_internal_value raises ValidationError:
            "ContentType with id {content_type_id} does not exist."

        Reference: board/serializers.py — GenericObjectRelatedField.to_internal_value
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id = self._create_board().data["id"]

        response = self._add_item(board_id, content_type_id=99999999, object_id=1)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Expected 400 for invalid content_type_id, got {response.status_code}: {response.data}",
        )

    # ── 6.3-G: disallowed content type → 400 ────────────────────────

    def test_6_3_g_disallowed_content_type_returns_400(self) -> None:
        """
        Scenario 6.3-G: Supplying a content_type that exists in Django but is
        NOT in GenericObjectRelatedField.ALLOWED_CONTENT_TYPES must return 400.

        Example: accounts.user (auth_user) — valid ContentType but not on the
        allowed list for detective board pins.

        Allowed list (board/serializers.py — GenericObjectRelatedField):
            cases.case, suspects.suspect, evidence.evidence,
            evidence.testimonyevidence, evidence.biologicalevidence,
            evidence.vehicleevidence, evidence.identityevidence,
            board.boardnote

        Reference: board/serializers.py — ALLOWED_CONTENT_TYPES
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id = self._create_board().data["id"]
        # django.contrib.auth User model — exists in ContentType table but
        # is deliberately excluded from the board's allowed pin types.
        user_ct = ContentType.objects.get(app_label="accounts", model="user")

        response = self._add_item(board_id, user_ct.pk, self.detective_user.pk)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=(
                f"Expected 400 for disallowed content type 'accounts.user', "
                f"got {response.status_code}: {response.data}"
            ),
        )

    # ── 6.3-H: unrelated user tries to pin → 403 ────────────────────

    def test_6_3_h_unrelated_user_cannot_pin_item_returns_403(self) -> None:
        """
        Scenario 6.3-H: A user who has no edit rights on the board (not the
        detective, not a supervisor assigned to the case, not admin) receives
        HTTP 403 when attempting to pin an item.

        Service permission check:
            board/services.py — BoardItemService.add_item → _enforce_edit()
            → raises PermissionDenied for users who fail _can_edit_board()

        Reference:
          - board/services.py    — _can_edit_board / _enforce_edit
          - board_services_report.md §1 Write (Edit) Access table
        """
        # Detective creates the board
        self._login_as(self.detective_user.username, self.detective_password)
        board_id = self._create_board().data["id"]
        evidence = self._make_evidence()
        ct = ContentType.objects.get(app_label="evidence", model="evidence")

        # Cadet (not assigned to the case) tries to pin
        self._login_as(self.cadet_user.username, self.cadet_password)
        response = self._add_item(board_id, ct.pk, evidence.pk)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=(
                f"Expected 403 Forbidden when an unrelated user pins an item, "
                f"got {response.status_code}: {response.data}"
            ),
        )

    # ─────────────────────────────────────────────────────────────────
    #  Scenario 6.4 helpers
    # ─────────────────────────────────────────────────────────────────

    def _setup_board_with_two_items(self) -> tuple[int, int, int]:
        """
        Create a board (on cls.case) with two evidence items pinned and
        return (board_id, item1_id, item2_id).

        Used as arrange step for 6.4 tests; reuses existing helpers.
        The detective is already authenticated when this is called.
        """
        board_id = self._create_board().data["id"]
        ct = ContentType.objects.get(app_label="evidence", model="evidence")

        # Pin two distinct Evidence objects
        ev1 = Evidence.objects.create(
            case=self.case,
            evidence_type=EvidenceType.OTHER,
            title="Matchbook from the Blue Room",
            description="Found under the bar.",
            registered_by=self.detective_user,
        )
        ev2 = Evidence.objects.create(
            case=self.case,
            evidence_type=EvidenceType.OTHER,
            title="Lipstick-stained cigarette",
            description="On the victim's ashtray.",
            registered_by=self.detective_user,
        )

        item1_id = self._add_item(board_id, ct.pk, ev1.pk, 0.0, 0.0).data["id"]
        item2_id = self._add_item(board_id, ct.pk, ev2.pk, 100.0, 100.0).data["id"]
        return board_id, item1_id, item2_id

    # ─────────────────────────────────────────────────────────────────
    #  Scenario 6.4 — Create a connection (red string) between items
    # ─────────────────────────────────────────────────────────────────

    # ── 6.4-A: happy path — 201 and correct response schema ──────────

    def test_6_4_a_detective_creates_connection_returns_201(self) -> None:
        """
        Scenario 6.4-A: POST /api/boards/{id}/connections/ as Detective
        → HTTP 201 Created.

        Payload: {from_item: <int>, to_item: <int>, label: <str>}

        Reference:
          - project-doc.md §4.4 — 'connect related documents with a red line'
          - swagger_doc §3.5    — BoardConnectionViewSet.create → 201
          - board/serializers.py — BoardConnectionCreateSerializer
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id, item1_id, item2_id = self._setup_board_with_two_items()

        response = self._add_connection(board_id, item1_id, item2_id, label="shared timeline")

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Expected 201 when creating connection, got {response.status_code}: {response.data}",
        )

    def test_6_4_a_connection_response_contains_required_fields(self) -> None:
        """
        Scenario 6.4-A (schema): BoardConnectionResponseSerializer fields:
            id, board, from_item, to_item, label, created_at, updated_at

        Reference: board/serializers.py — BoardConnectionResponseSerializer
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id, item1_id, item2_id = self._setup_board_with_two_items()

        response = self._add_connection(board_id, item1_id, item2_id, label="motive link")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        for field in ("id", "board", "from_item", "to_item", "label",
                      "created_at", "updated_at"):
            self.assertIn(field, response.data,
                          msg=f"Connection response missing field '{field}'.")

        self.assertEqual(response.data["board"], board_id)
        self.assertEqual(response.data["from_item"], item1_id)
        self.assertEqual(response.data["to_item"], item2_id)
        self.assertEqual(response.data["label"], "motive link")

    # ── 6.4-B: connection visible in full board state ─────────────────

    def test_6_4_b_connection_appears_in_full_state_connections_list(self) -> None:
        """
        Scenario 6.4-B: After creating a connection,
        GET /api/boards/{id}/full/ connections list must contain it.

        BoardConnectionInlineSerializer fields:
            id, from_item, to_item, label, created_at, updated_at

        Reference:
          - swagger_doc §3.5 — DetectiveBoardViewSet.full_state
          - board/serializers.py — BoardConnectionInlineSerializer
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id, item1_id, item2_id = self._setup_board_with_two_items()

        conn_resp = self._add_connection(board_id, item1_id, item2_id, label="red string")
        self.assertEqual(conn_resp.status_code, status.HTTP_201_CREATED)
        conn_id = conn_resp.data["id"]

        full_resp = self._get_full_state(board_id)
        self.assertEqual(full_resp.status_code, status.HTTP_200_OK)

        connections = full_resp.data["connections"]
        self.assertEqual(len(connections), 1,
                         msg=f"Expected 1 connection in full state, got {len(connections)}.")

        conn = connections[0]
        self.assertEqual(conn["id"], conn_id)
        self.assertEqual(conn["from_item"], item1_id)
        self.assertEqual(conn["to_item"], item2_id)
        self.assertEqual(conn["label"], "red string")

        # Full state must still show both items alongside the connection
        self.assertEqual(len(full_resp.data["items"]), 2)

    # ── 6.4-C: self-loop connection → 400 ────────────────────────────

    def test_6_4_c_self_loop_connection_returns_400(self) -> None:
        """
        Scenario 6.4-C: A connection where from_item == to_item must be
        rejected with HTTP 400.

        Serializer-level guard:
            board/serializers.py — BoardConnectionCreateSerializer.validate
            → "A BoardItem cannot be connected to itself."

        Service-level guard (also):
            board/services.py — BoardConnectionService.create_connection
            → "A board item cannot be connected to itself."

        Reference: board/serializers.py — BoardConnectionCreateSerializer
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id, item1_id, _ = self._setup_board_with_two_items()

        response = self._add_connection(board_id, item1_id, item1_id, label="self loop")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=f"Expected 400 for self-loop connection, got {response.status_code}: {response.data}",
        )

    # ── 6.4-D: item from another board → 400 ─────────────────────────

    def test_6_4_d_item_from_different_board_returns_400(self) -> None:
        """
        Scenario 6.4-D: Providing a to_item that belongs to a **different**
        board must fail with HTTP 400.

        Service guard:
            board/services.py — BoardConnectionService.create_connection
            → "Both items must belong to the same board."

        Setup: create a second case + board, pin one item on it, then try
        to connect board-A's item with board-B's item via board-A's endpoint.
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_a_id, item_a_id, _ = self._setup_board_with_two_items()

        # Create a second independent case and board
        case_b = Case.objects.create(
            title="The Naked City Heist",
            description="A second independent case.",
            crime_level=CrimeLevel.LEVEL_2,
            status=CaseStatus.OPEN,
            creation_type=CaseCreationType.CRIME_SCENE,
            location="Bunker Hill, LA",
            created_by=self.detective_user,
            assigned_detective=self.detective_user,
        )
        board_b_id = self._create_board(case_pk=case_b.pk).data["id"]

        ct = ContentType.objects.get(app_label="evidence", model="evidence")
        ev_b = Evidence.objects.create(
            case=case_b,
            evidence_type=EvidenceType.OTHER,
            title="Foreign item from board B",
            description="Should not be connectable on board A.",
            registered_by=self.detective_user,
        )
        item_b_id = self._add_item(board_b_id, ct.pk, ev_b.pk).data["id"]

        # Try to connect board-A's item → board-B's item via board-A's endpoint
        response = self._add_connection(board_a_id, item_a_id, item_b_id, label="cross-board")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=(
                f"Expected 400 when to_item belongs to a different board, "
                f"got {response.status_code}: {response.data}"
            ),
        )

    # ── 6.4-E: unrelated user tries to connect → 403 ─────────────────

    def test_6_4_e_unrelated_user_cannot_create_connection_returns_403(self) -> None:
        """
        Scenario 6.4-E: A user without edit access on the board (not the
        detective, not an assigned supervisor, not admin) receives HTTP 403
        when posting to the connections endpoint.

        Service check:
            board/services.py — BoardConnectionService.create_connection
            → _enforce_edit() → PermissionDenied

        Reference:
          - board/services.py — _can_edit_board / _enforce_edit
          - board_services_report.md §1 Write (Edit) Access table
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id, item1_id, item2_id = self._setup_board_with_two_items()

        # Switch to Cadet — no access to this board
        self._login_as(self.cadet_user.username, self.cadet_password)
        response = self._add_connection(board_id, item1_id, item2_id, label="unauthorized")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=(
                f"Expected 403 Forbidden when unrelated user creates connection, "
                f"got {response.status_code}: {response.data}"
            ),
        )

    # ─────────────────────────────────────────────────────────────────
    # Scenario 6.5 — Batch update item coordinates (drag-and-drop save)
    # ─────────────────────────────────────────────────────────────────

    # ── helper ───────────────────────────────────────────────────────

    def _batch_update_coordinates(self, board_id: int, items: list) -> object:
        """
        PATCH /api/boards/{board_id}/items/batch-coordinates/

        Payload: {"items": [{"id": <int>, "position_x": <float>, "position_y": <float>}, ...]}
        Returns the raw APIClient response.
        """
        url = reverse(
            "board-item-batch-update-coordinates",
            kwargs={"board_pk": board_id},
        )
        return self.client.patch(url, {"items": items}, format="json")

    # ── 6.5-A: successful batch update → 200 ─────────────────────────

    def test_6_5_a_detective_batch_updates_coordinates_returns_200(self) -> None:
        """
        Scenario 6.5-A: PATCH /api/boards/{id}/items/batch-coordinates/ with
        two valid items returns HTTP 200 OK.

        Service: BoardItemService.update_batch_coordinates (bulk_update)
        Reference: board/services.py, board/serializers.py
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id, item1_id, item2_id = self._setup_board_with_two_items()

        payload = [
            {"id": item1_id, "position_x": 200.0, "position_y": 350.0},
            {"id": item2_id, "position_x": 450.5, "position_y": 80.25},
        ]
        response = self._batch_update_coordinates(board_id, payload)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=(
                f"Expected 200 OK for batch coordinate update, "
                f"got {response.status_code}: {response.data}"
            ),
        )

    def test_6_5_a_response_lists_both_updated_items_with_new_coordinates(self) -> None:
        """
        Scenario 6.5-A (schema): Response body must be a list containing both
        updated items.  Each entry must include 'id', 'position_x', and
        'position_y', and the coordinate values must match the submitted payload.

        Reference: board/serializers.py — BoardItemResponseSerializer
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id, item1_id, item2_id = self._setup_board_with_two_items()

        payload = [
            {"id": item1_id, "position_x": 200.0, "position_y": 350.0},
            {"id": item2_id, "position_x": 450.5, "position_y": 80.25},
        ]
        response = self._batch_update_coordinates(board_id, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertIsInstance(data, list, msg="Response must be a list of board items.")
        self.assertEqual(len(data), 2, msg="Response must contain exactly 2 items.")

        returned_map = {item["id"]: item for item in data}
        for expected in payload:
            item_id = expected["id"]
            self.assertIn(item_id, returned_map, msg=f"Item {item_id} missing from response.")
            self.assertAlmostEqual(
                float(returned_map[item_id]["position_x"]),
                expected["position_x"],
                places=2,
                msg=f"position_x mismatch for item {item_id} in response.",
            )
            self.assertAlmostEqual(
                float(returned_map[item_id]["position_y"]),
                expected["position_y"],
                places=2,
                msg=f"position_y mismatch for item {item_id} in response.",
            )

    # ── 6.5-B: coordinates persist in full state ──────────────────────

    def test_6_5_b_updated_coordinates_persist_in_full_state(self) -> None:
        """
        Scenario 6.5-B: After a successful batch update, GET /api/boards/{id}/full/
        must reflect the new (position_x, position_y) for every updated item,
        confirming that bulk_update actually wrote to the database.

        Reference: board/services.py — bulk_update(fields=["position_x","position_y"])
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id, item1_id, item2_id = self._setup_board_with_two_items()

        new_coords = {
            item1_id: (111.1, 222.2),
            item2_id: (333.3, 444.4),
        }
        payload = [
            {"id": k, "position_x": v[0], "position_y": v[1]}
            for k, v in new_coords.items()
        ]
        patch_response = self._batch_update_coordinates(board_id, payload)
        self.assertEqual(
            patch_response.status_code,
            status.HTTP_200_OK,
            msg=f"Batch update failed: {patch_response.data}",
        )

        full = self._get_full_state(board_id)
        self.assertEqual(full.status_code, status.HTTP_200_OK)

        items_in_full = {item["id"]: item for item in full.data["items"]}
        for item_id, (expected_x, expected_y) in new_coords.items():
            self.assertIn(
                item_id, items_in_full,
                msg=f"Item {item_id} missing from full-state items list.",
            )
            self.assertAlmostEqual(
                float(items_in_full[item_id]["position_x"]),
                expected_x,
                places=2,
                msg=f"Persisted position_x mismatch for item {item_id}.",
            )
            self.assertAlmostEqual(
                float(items_in_full[item_id]["position_y"]),
                expected_y,
                places=2,
                msg=f"Persisted position_y mismatch for item {item_id}.",
            )

    # ── 6.5-C: item from different board → 400 ───────────────────────

    def test_6_5_c_item_from_different_board_returns_400(self) -> None:
        """
        Scenario 6.5-C: Including an item ID that belongs to a *different*
        board in the batch payload must return HTTP 400.

        Service guard: BoardItemService.update_batch_coordinates
            → raises DomainError(
                "The following item IDs do not belong to this board: [...]")

        Reference: board/services.py — update_batch_coordinates, lines ~385-392
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_a_id, item_a_id, _ = self._setup_board_with_two_items()

        # Create a second board on a separate case and pin one item there
        case_b = _make_open_case(
            created_by=self.detective_user,
            assigned_detective=self.detective_user,
        )
        board_b_resp = self._create_board(case_pk=case_b.pk)
        self.assertEqual(board_b_resp.status_code, status.HTTP_201_CREATED)
        board_b_id = board_b_resp.data["id"]
        ev_b = self._make_evidence()
        ct = ContentType.objects.get_for_model(Evidence)
        item_b_resp = self._add_item(board_b_id, ct.pk, ev_b.pk)
        self.assertEqual(item_b_resp.status_code, status.HTTP_201_CREATED)
        item_b_id = item_b_resp.data["id"]

        # Batch payload for board-A that sneaks in board-B's item
        payload = [
            {"id": item_a_id, "position_x": 10.0, "position_y": 10.0},
            {"id": item_b_id, "position_x": 20.0, "position_y": 20.0},
        ]
        response = self._batch_update_coordinates(board_a_id, payload)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=(
                f"Expected 400 when payload contains item from a different board, "
                f"got {response.status_code}: {response.data}"
            ),
        )

    # ── 6.5-D: duplicate item IDs in batch → 400 ─────────────────────

    def test_6_5_d_duplicate_item_ids_in_batch_returns_400(self) -> None:
        """
        Scenario 6.5-D: When the same item ID appears more than once in the
        'items' array, the serializer must reject the request with HTTP 400.

        Serializer guard: BatchCoordinateUpdateSerializer.validate_items
            → ValidationError("Duplicate item IDs in batch.")

        Reference: board/serializers.py — BatchCoordinateUpdateSerializer
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id, item1_id, _ = self._setup_board_with_two_items()

        payload = [
            {"id": item1_id, "position_x": 10.0, "position_y": 10.0},
            {"id": item1_id, "position_x": 20.0, "position_y": 20.0},  # duplicate
        ]
        response = self._batch_update_coordinates(board_id, payload)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            msg=(
                f"Expected 400 for duplicate item IDs in batch, "
                f"got {response.status_code}: {response.data}"
            ),
        )

    # ── 6.5-E: unrelated user → 403 ──────────────────────────────────

    def test_6_5_e_unrelated_user_cannot_batch_update_returns_403(self) -> None:
        """
        Scenario 6.5-E: A user without edit access on the board receives
        HTTP 403 when calling the batch-coordinates endpoint.

        Service check:
            BoardItemService.update_batch_coordinates → _enforce_edit()
            → PermissionDenied("You do not have permission to modify this board.")

        Reference: board/services.py — _can_edit_board / _enforce_edit
        """
        self._login_as(self.detective_user.username, self.detective_password)
        board_id, item1_id, item2_id = self._setup_board_with_two_items()

        # Switch to Cadet — no edit access on this board
        self._login_as(self.cadet_user.username, self.cadet_password)
        payload = [
            {"id": item1_id, "position_x": 99.0, "position_y": 99.0},
        ]
        response = self._batch_update_coordinates(board_id, payload)

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=(
                f"Expected 403 Forbidden for unrelated user on batch-coordinates, "
                f"got {response.status_code}: {response.data}"
            ),
        )
