"""
Suspects app ViewSets.

Architecture: Views are intentionally thin.
Every view follows the strict three-step pattern:

    1. Parse / validate input via a serializer.
    2. Delegate all business logic to the appropriate service class.
    3. Serialize the result and return a DRF ``Response``.

No database queries, workflow logic, permission checks, or status
validation lives here.

ViewSets
--------
- ``SuspectViewSet``     — CRUD + workflow actions (approve, issue-warrant,
                           arrest, transition-status, most-wanted).
- ``InterrogationViewSet`` — Nested under suspects for interrogation CRUD.
- ``TrialViewSet``         — Nested under suspects for trial CRUD.
- ``BailViewSet``          — Nested under suspects for bail CRUD.
- ``BountyTipViewSet``     — Top-level and suspect-nested bounty tip
                             management with review/verify workflow actions.
"""

from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from core.domain.exceptions import DomainError, InvalidTransition, NotFound, PermissionDenied

from .models import (
    Bail,
    BountyTip,
    Interrogation,
    Suspect,
    Trial,
)
from .serializers import (
    ArrestPayloadSerializer,
    ArrestWarrantSerializer,
    BailCreateSerializer,
    BailDetailSerializer,
    BailListSerializer,
    BountyRewardLookupSerializer,
    BountyTipCreateSerializer,
    BountyTipDetailSerializer,
    BountyTipListSerializer,
    BountyTipReviewSerializer,
    BountyTipVerifySerializer,
    InterrogationCreateSerializer,
    InterrogationDetailSerializer,
    InterrogationListSerializer,
    MostWantedSerializer,
    SuspectApprovalSerializer,
    SuspectCreateSerializer,
    SuspectDetailSerializer,
    SuspectFilterSerializer,
    SuspectListSerializer,
    SuspectStatusTransitionSerializer,
    SuspectUpdateSerializer,
    TrialCreateSerializer,
    TrialDetailSerializer,
    TrialListSerializer,
)
from .services import (
    ArrestAndWarrantService,
    BailService,
    BountyTipService,
    InterrogationService,
    SuspectProfileService,
    TrialService,
)


# ═══════════════════════════════════════════════════════════════════
#  Suspect ViewSet
# ═══════════════════════════════════════════════════════════════════


class SuspectViewSet(viewsets.ViewSet):
    """
    Central ViewSet for suspect management.

    Uses ``viewsets.ViewSet`` (not ``ModelViewSet``) so every action is
    explicitly defined, preventing accidental exposure of unintended
    CRUD operations.

    Permission Strategy
    -------------------
    The base permission is ``IsAuthenticated``.  Fine-grained permission
    checks (role-based, ownership-based) are enforced exclusively inside
    the service layer — never in the view.

    Endpoints
    ---------
    Standard CRUD:
        GET    /api/suspects/                    → list
        POST   /api/suspects/                    → create
        GET    /api/suspects/{id}/               → retrieve
        PATCH  /api/suspects/{id}/               → partial_update

    Workflow Actions:
        POST   /api/suspects/{id}/approve/              → approve/reject by Sergeant
        POST   /api/suspects/{id}/issue-warrant/        → Sergeant issues warrant
        POST   /api/suspects/{id}/arrest/               → execute arrest
        POST   /api/suspects/{id}/transition-status/    → generic status transition

    Special Listing:
        GET    /api/suspects/most-wanted/        → public Most Wanted page
    """

    permission_classes = [IsAuthenticated]

    # ── Helper Methods ───────────────────────────────────────────────

    def _get_suspect(self, pk: int) -> Suspect:
        """
        Retrieve a suspect by PK using the profile service.
        Raises HTTP 404 if not found.

        Implementation Contract
        -----------------------
        return SuspectProfileService.get_suspect_detail(pk)
        Wrap in try/except Suspect.DoesNotExist → raise Http404.
        """
        return SuspectProfileService.get_suspect_detail(pk)

    # ── Standard CRUD ────────────────────────────────────────────────

    def list(self, request: Request) -> Response:
        """
        GET /api/suspects/

        List suspects visible to the authenticated user, with optional
        query-parameter filtering.

        Steps
        -----
        1. Validate query params with
           ``SuspectFilterSerializer(data=request.query_params)``.
        2. If invalid, return HTTP 400 with errors.
        3. Get queryset via ``SuspectProfileService.get_filtered_queryset(
               request.user, filter_serializer.validated_data
           )``.
        4. Serialize with ``SuspectListSerializer(queryset, many=True)``.
        5. Return HTTP 200 with serialised data.

        Example Response
        ----------------
        ::

            [
                {
                    "id": 1,
                    "full_name": "Roy Earle",
                    "national_id": "1234567890",
                    "status": "wanted",
                    "status_display": "Wanted",
                    "case": 5,
                    "case_title": "Hollywood Murder",
                    "wanted_since": "2026-01-15T08:00:00Z",
                    "days_wanted": 38,
                    "is_most_wanted": true,
                    "identified_by": 12,
                    "identified_by_name": "Det. Cole Phelps",
                    "sergeant_approval_status": "approved",
                    "created_at": "2026-01-15T08:00:00Z",
                    "updated_at": "2026-01-15T08:00:00Z"
                }
            ]
        """
        filter_serializer = SuspectFilterSerializer(data=request.query_params)
        if not filter_serializer.is_valid():
            return Response(
                filter_serializer.errors, status=status.HTTP_400_BAD_REQUEST,
            )
        queryset = SuspectProfileService.get_filtered_queryset(
            request.user, filter_serializer.validated_data,
        )
        serializer = SuspectListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request: Request) -> Response:
        """
        POST /api/suspects/

        Identify a new suspect and link them to a case (Detective action).

        Steps
        -----
        1. Validate ``request.data`` with ``SuspectCreateSerializer``.
        2. If invalid, return HTTP 400.
        3. Delegate to ``SuspectProfileService.create_suspect(
               validated_data=serializer.validated_data,
               requesting_user=request.user,
           )``.
        4. Serialize result with ``SuspectDetailSerializer``.
        5. Return HTTP 201.

        Example Request Body
        --------------------
        ::

            {
                "case": 5,
                "full_name": "Roy Earle",
                "national_id": "1234567890",
                "phone_number": "+1-213-555-0147",
                "address": "742 S. Broadway, Los Angeles",
                "description": "Tall, dark hair, scar on left cheek."
            }

        Error Handling
        --------------
        - HTTP 400 if validation fails.
        - HTTP 403 if the user lacks ``CAN_IDENTIFY_SUSPECT`` (raised by service).
        """
        serializer = SuspectCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST,
            )
        suspect = SuspectProfileService.create_suspect(
            validated_data=serializer.validated_data,
            requesting_user=request.user,
        )
        output = SuspectDetailSerializer(suspect)
        return Response(output.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request: Request, pk: int = None) -> Response:
        """
        GET /api/suspects/{id}/

        Return the full suspect detail with nested interrogations,
        trials, bails, and computed ranking properties.

        Steps
        -----
        1. ``suspect = self._get_suspect(pk)``.
        2. Serialize with ``SuspectDetailSerializer(suspect)``.
        3. Return HTTP 200.

        Example Response
        ----------------
        ::

            {
                "id": 1,
                "full_name": "Roy Earle",
                "national_id": "1234567890",
                "status": "arrested",
                "status_display": "Arrested",
                "case": 5,
                "case_title": "Hollywood Murder",
                "days_wanted": 38,
                "is_most_wanted": true,
                "most_wanted_score": 152,
                "reward_amount": 1520000000,
                "interrogations": [...],
                "trials": [...],
                "bails": [...],
                "bounty_tip_count": 3,
                ...
            }
        """
        suspect = self._get_suspect(pk)
        serializer = SuspectDetailSerializer(suspect)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request: Request, pk: int = None) -> Response:
        """
        PATCH /api/suspects/{id}/

        Partially update a suspect's mutable profile fields.

        Steps
        -----
        1. ``suspect = self._get_suspect(pk)``.
        2. Validate ``request.data`` with ``SuspectUpdateSerializer(
               suspect, data=request.data, partial=True
           )``.
        3. If invalid, return HTTP 400.
        4. Delegate to ``SuspectProfileService.update_suspect(
               suspect, serializer.validated_data, request.user
           )``.
        5. Serialize result with ``SuspectDetailSerializer``.
        6. Return HTTP 200.

        Notes
        -----
        - Status changes use dedicated workflow action endpoints, not PATCH.
        - ``case``, ``identified_by``, and approval fields are immutable.
        """
        suspect = self._get_suspect(pk)
        serializer = SuspectUpdateSerializer(
            suspect, data=request.data, partial=True,
        )
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST,
            )
        updated = SuspectProfileService.update_suspect(
            suspect, serializer.validated_data, request.user,
        )
        output = SuspectDetailSerializer(updated)
        return Response(output.data, status=status.HTTP_200_OK)

    # ── Workflow @actions ─────────────────────────────────────────────

    @action(detail=False, methods=["get"], url_path="most-wanted")
    def most_wanted(self, request: Request) -> Response:
        """
        GET /api/suspects/most-wanted/

        Return the Most Wanted list — suspects wanted for > 30 days,
        ranked by their ``most_wanted_score``.

        Visible to all authenticated users (including base users)
        per project-doc §4.7.

        Steps
        -----
        1. Get queryset via ``SuspectProfileService.get_most_wanted_list()``.
        2. Serialize with ``MostWantedSerializer(queryset, many=True)``.
        3. Return HTTP 200.

        Example Response
        ----------------
        ::

            [
                {
                    "id": 1,
                    "full_name": "Roy Earle",
                    "photo": "/media/suspect_photos/2026/01/earle.jpg",
                    "description": "Tall, dark hair, scar on left cheek.",
                    "status": "wanted",
                    "wanted_since": "2026-01-15T08:00:00Z",
                    "days_wanted": 38,
                    "most_wanted_score": 152,
                    "reward_amount": 1520000000,
                    "case_title": "Hollywood Murder"
                }
            ]
        """
        queryset = SuspectProfileService.get_most_wanted_list()
        serializer = MostWantedSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/suspects/{id}/approve/

        **Sergeant approves or rejects a suspect identification.**

        Steps
        -----
        1. Validate ``request.data`` with ``SuspectApprovalSerializer``.
        2. If invalid, return HTTP 400.
        3. Delegate to ``ArrestAndWarrantService.approve_or_reject_suspect(
               suspect_id=pk,
               sergeant_user=request.user,
               decision=validated_data["decision"],
               rejection_message=validated_data.get("rejection_message", ""),
           )``.
        4. Serialize result with ``SuspectDetailSerializer``.
        5. Return HTTP 200.

        Error Handling
        --------------
        - HTTP 400 if validation fails.
        - HTTP 403 if lacking Sergeant permission (raised by service).
        - HTTP 400 if suspect is not in pending approval status.

        Example Request (Approve)
        -------------------------
        ::

            POST /api/suspects/12/approve/
            {"decision": "approve"}

        Example Request (Reject)
        ------------------------
        ::

            POST /api/suspects/12/approve/
            {
                "decision": "reject",
                "rejection_message": "Insufficient evidence."
            }
        """
        serializer = SuspectApprovalSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST,
            )
        suspect = ArrestAndWarrantService.approve_or_reject_suspect(
            suspect_id=pk,
            sergeant_user=request.user,
            decision=serializer.validated_data["decision"],
            rejection_message=serializer.validated_data.get(
                "rejection_message", "",
            ),
        )
        output = SuspectDetailSerializer(suspect)
        return Response(output.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="issue-warrant")
    def issue_warrant(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/suspects/{id}/issue-warrant/

        **Sergeant issues an arrest warrant for an approved suspect.**

        Steps
        -----
        1. Validate ``request.data`` with ``ArrestWarrantSerializer``.
        2. If invalid, return HTTP 400.
        3. Delegate to ``ArrestAndWarrantService.issue_arrest_warrant(
               suspect_id=pk,
               issuing_sergeant=request.user,
               warrant_reason=validated_data["warrant_reason"],
               priority=validated_data.get("priority", "normal"),
           )``.
        4. Serialize result with ``SuspectDetailSerializer``.
        5. Return HTTP 200.

        Error Handling
        --------------
        - HTTP 400 if suspect is not approved or not in WANTED status.
        - HTTP 403 if lacking ``CAN_ISSUE_ARREST_WARRANT`` permission.

        Example Request
        ---------------
        ::

            POST /api/suspects/12/issue-warrant/
            {
                "warrant_reason": "Strong forensic evidence.",
                "priority": "high"
            }
        """
        serializer = ArrestWarrantSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            suspect = ArrestAndWarrantService.issue_arrest_warrant(
                suspect_id=pk,
                issuing_sergeant=request.user,
                warrant_reason=serializer.validated_data["warrant_reason"],
                priority=serializer.validated_data.get("priority", "normal"),
            )
        except PermissionDenied as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN,
            )
        except (DomainError, InvalidTransition) as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST,
            )
        output = SuspectDetailSerializer(suspect)
        return Response(output.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="arrest")
    def arrest(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/suspects/{id}/arrest/

        **Execute the arrest of a suspect — transition to In Custody.**

        This is the most critical endpoint in the suspects app.  It
        requires strict permission checks, warrant validation, and
        creates a full audit trail.

        Steps
        -----
        1. Validate ``request.data`` with ``ArrestPayloadSerializer``.
        2. If invalid, return HTTP 400.
        3. Delegate to ``ArrestAndWarrantService.execute_arrest(
               suspect_id=pk,
               arresting_officer=request.user,
               arrest_location=validated_data["arrest_location"],
               arrest_notes=validated_data.get("arrest_notes", ""),
               warrant_override_justification=validated_data.get(
                   "warrant_override_justification", ""
               ),
           )``.
        4. Serialize result with ``SuspectDetailSerializer``.
        5. Return HTTP 200.

        Error Handling
        --------------
        - HTTP 400 if suspect is not WANTED or not approved.
        - HTTP 400 if no warrant and no override justification.
        - HTTP 403 if lacking arrest permission.

        Example Request (With Warrant)
        ------------------------------
        ::

            POST /api/suspects/12/arrest/
            {
                "arrest_location": "742 S. Broadway, Los Angeles",
                "arrest_notes": "Apprehended without resistance."
            }

        Example Request (Without Warrant — Override)
        ---------------------------------------------
        ::

            POST /api/suspects/12/arrest/
            {
                "arrest_location": "Corner of 5th and Main",
                "arrest_notes": "Suspect caught fleeing crime scene.",
                "warrant_override_justification": "Caught in the act."
            }
        """
        serializer = ArrestPayloadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            suspect = ArrestAndWarrantService.execute_arrest(
                suspect_id=pk,
                arresting_officer=request.user,
                arrest_location=serializer.validated_data["arrest_location"],
                arrest_notes=serializer.validated_data.get(
                    "arrest_notes", "",
                ),
                warrant_override_justification=serializer.validated_data.get(
                    "warrant_override_justification", "",
                ),
            )
        except PermissionDenied as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN,
            )
        except (DomainError, InvalidTransition) as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST,
            )
        output = SuspectDetailSerializer(suspect)
        return Response(output.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="transition-status")
    def transition_status(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/suspects/{id}/transition-status/

        **Generic status transition for non-arrest lifecycle changes.**

        Steps
        -----
        1. Validate ``request.data`` with ``SuspectStatusTransitionSerializer``.
        2. If invalid, return HTTP 400.
        3. Delegate to ``ArrestAndWarrantService.transition_status(
               suspect_id=pk,
               requesting_user=request.user,
               new_status=validated_data["new_status"],
               reason=validated_data["reason"],
           )``.
        4. Serialize result with ``SuspectDetailSerializer``.
        5. Return HTTP 200.

        Error Handling
        --------------
        - HTTP 400 if the transition is not allowed from current status.
        - HTTP 403 if lacking the permission for the specific transition.

        Example Request
        ---------------
        ::

            POST /api/suspects/12/transition-status/
            {
                "new_status": "under_interrogation",
                "reason": "Suspect arrested, beginning interrogation."
            }
        """
        serializer = SuspectStatusTransitionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            suspect = ArrestAndWarrantService.transition_status(
                suspect_id=pk,
                requesting_user=request.user,
                new_status=serializer.validated_data["new_status"],
                reason=serializer.validated_data["reason"],
            )
        except PermissionDenied as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN,
            )
        except (DomainError, InvalidTransition) as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST,
            )
        output = SuspectDetailSerializer(suspect)
        return Response(output.data, status=status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════════════════
#  Interrogation ViewSet (Nested under Suspects)
# ═══════════════════════════════════════════════════════════════════


class InterrogationViewSet(viewsets.ViewSet):
    """
    Manages interrogation sessions for a specific suspect.

    Nested under ``/api/suspects/{suspect_pk}/interrogations/``.

    Permission Strategy
    -------------------
    Base: ``IsAuthenticated``.
    Fine-grained checks in the service layer (``CAN_CONDUCT_INTERROGATION``).

    Endpoints
    ---------
        GET    /api/suspects/{suspect_pk}/interrogations/       → list
        POST   /api/suspects/{suspect_pk}/interrogations/       → create
        GET    /api/suspects/{suspect_pk}/interrogations/{id}/  → retrieve
    """

    permission_classes = [IsAuthenticated]

    def list(self, request: Request, suspect_pk: int = None) -> Response:
        """
        GET /api/suspects/{suspect_pk}/interrogations/

        List all interrogation sessions for the given suspect.

        Steps
        -----
        1. Get queryset via ``InterrogationService.get_interrogations_for_suspect(
               suspect_id=suspect_pk,
               requesting_user=request.user,
           )``.
        2. Serialize with ``InterrogationListSerializer(queryset, many=True)``.
        3. Return HTTP 200.
        """
        raise NotImplementedError

    def create(self, request: Request, suspect_pk: int = None) -> Response:
        """
        POST /api/suspects/{suspect_pk}/interrogations/

        Create a new interrogation session for the suspect.

        Steps
        -----
        1. Validate ``request.data`` with ``InterrogationCreateSerializer``.
        2. If invalid, return HTTP 400.
        3. Delegate to ``InterrogationService.create_interrogation(
               suspect_id=suspect_pk,
               validated_data=serializer.validated_data,
               requesting_user=request.user,
           )``.
        4. Serialize result with ``InterrogationDetailSerializer``.
        5. Return HTTP 201.

        Example Request
        ---------------
        ::

            POST /api/suspects/12/interrogations/
            {
                "detective_guilt_score": 8,
                "sergeant_guilt_score": 7,
                "notes": "Suspect showed signs of deception."
            }
        """
        raise NotImplementedError

    def retrieve(
        self, request: Request, suspect_pk: int = None, pk: int = None,
    ) -> Response:
        """
        GET /api/suspects/{suspect_pk}/interrogations/{id}/

        Retrieve a single interrogation session detail.

        Steps
        -----
        1. Fetch interrogation via service or direct lookup.
        2. Serialize with ``InterrogationDetailSerializer``.
        3. Return HTTP 200.
        """
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════
#  Trial ViewSet (Nested under Suspects)
# ═══════════════════════════════════════════════════════════════════


class TrialViewSet(viewsets.ViewSet):
    """
    Manages trial records for a specific suspect.

    Nested under ``/api/suspects/{suspect_pk}/trials/``.

    Permission Strategy
    -------------------
    Base: ``IsAuthenticated``.
    Fine-grained checks in service (``CAN_JUDGE_TRIAL``, ``CAN_RENDER_VERDICT``).

    Endpoints
    ---------
        GET    /api/suspects/{suspect_pk}/trials/       → list
        POST   /api/suspects/{suspect_pk}/trials/       → create
        GET    /api/suspects/{suspect_pk}/trials/{id}/  → retrieve
    """

    permission_classes = [IsAuthenticated]

    def list(self, request: Request, suspect_pk: int = None) -> Response:
        """
        GET /api/suspects/{suspect_pk}/trials/

        List all trial records for the given suspect.

        Steps
        -----
        1. Get queryset via ``TrialService.get_trials_for_suspect(
               suspect_id=suspect_pk,
               requesting_user=request.user,
           )``.
        2. Serialize with ``TrialListSerializer(queryset, many=True)``.
        3. Return HTTP 200.
        """
        raise NotImplementedError

    def create(self, request: Request, suspect_pk: int = None) -> Response:
        """
        POST /api/suspects/{suspect_pk}/trials/

        Create a trial record for the suspect (Judge action).

        Steps
        -----
        1. Validate ``request.data`` with ``TrialCreateSerializer``.
        2. If invalid, return HTTP 400.
        3. Delegate to ``TrialService.create_trial(
               suspect_id=suspect_pk,
               validated_data=serializer.validated_data,
               requesting_user=request.user,
           )``.
        4. Serialize result with ``TrialDetailSerializer``.
        5. Return HTTP 201.

        Example Request
        ---------------
        ::

            POST /api/suspects/12/trials/
            {
                "verdict": "guilty",
                "punishment_title": "Murder",
                "punishment_description": "25 years without parole."
            }
        """
        raise NotImplementedError

    def retrieve(
        self, request: Request, suspect_pk: int = None, pk: int = None,
    ) -> Response:
        """
        GET /api/suspects/{suspect_pk}/trials/{id}/

        Retrieve a single trial record detail.

        Steps
        -----
        1. Fetch trial via service or direct lookup.
        2. Serialize with ``TrialDetailSerializer``.
        3. Return HTTP 200.
        """
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════
#  Bail ViewSet (Nested under Suspects)
# ═══════════════════════════════════════════════════════════════════


class BailViewSet(viewsets.ViewSet):
    """
    Manages bail/fine records for a specific suspect.

    Nested under ``/api/suspects/{suspect_pk}/bails/``.

    Permission Strategy
    -------------------
    Base: ``IsAuthenticated``.
    Fine-grained checks in service (``CAN_SET_BAIL_AMOUNT``).

    Endpoints
    ---------
        GET    /api/suspects/{suspect_pk}/bails/              → list
        POST   /api/suspects/{suspect_pk}/bails/              → create
        GET    /api/suspects/{suspect_pk}/bails/{id}/         → retrieve
        POST   /api/suspects/{suspect_pk}/bails/{id}/pay/     → process payment
    """

    permission_classes = [IsAuthenticated]

    def list(self, request: Request, suspect_pk: int = None) -> Response:
        """
        GET /api/suspects/{suspect_pk}/bails/

        List all bail records for the given suspect.

        Steps
        -----
        1. Get queryset via ``BailService.get_bails_for_suspect(
               suspect_id=suspect_pk,
               requesting_user=request.user,
           )``.
        2. Serialize with ``BailListSerializer(queryset, many=True)``.
        3. Return HTTP 200.
        """
        raise NotImplementedError

    def create(self, request: Request, suspect_pk: int = None) -> Response:
        """
        POST /api/suspects/{suspect_pk}/bails/

        Create a bail record for the suspect (Sergeant action).

        Steps
        -----
        1. Validate ``request.data`` with ``BailCreateSerializer``.
        2. If invalid, return HTTP 400.
        3. Delegate to ``BailService.create_bail(
               suspect_id=suspect_pk,
               validated_data=serializer.validated_data,
               requesting_user=request.user,
           )``.
        4. Serialize result with ``BailDetailSerializer``.
        5. Return HTTP 201.

        Example Request
        ---------------
        ::

            POST /api/suspects/12/bails/
            {"amount": 50000000}
        """
        raise NotImplementedError

    def retrieve(
        self, request: Request, suspect_pk: int = None, pk: int = None,
    ) -> Response:
        """
        GET /api/suspects/{suspect_pk}/bails/{id}/

        Retrieve a single bail record detail.

        Steps
        -----
        1. Fetch bail via service or direct lookup.
        2. Serialize with ``BailDetailSerializer``.
        3. Return HTTP 200.
        """
        raise NotImplementedError

    @action(detail=True, methods=["post"], url_path="pay")
    def pay(self, request: Request, suspect_pk: int = None, pk: int = None) -> Response:
        """
        POST /api/suspects/{suspect_pk}/bails/{id}/pay/

        Process bail payment via payment gateway callback.

        Steps
        -----
        1. Extract ``payment_reference`` from ``request.data``.
        2. Delegate to ``BailService.process_bail_payment(
               bail_id=pk,
               payment_reference=request.data.get("payment_reference", ""),
               requesting_user=request.user,
           )``.
        3. Serialize result with ``BailDetailSerializer``.
        4. Return HTTP 200.

        Example Request
        ---------------
        ::

            POST /api/suspects/12/bails/5/pay/
            {"payment_reference": "ZP-TXN-20260222-001"}
        """
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════
#  Bounty Tip ViewSet
# ═══════════════════════════════════════════════════════════════════


class BountyTipViewSet(viewsets.ViewSet):
    """
    Manages bounty tips — citizen submissions about suspects/cases.

    Registered at both top-level (``/api/bounty-tips/``) for creation
    and listing, and provides workflow actions for officer review and
    detective verification.

    Permission Strategy
    -------------------
    Base: ``IsAuthenticated``.
    Fine-grained checks in service:
    - Any authenticated user can submit tips.
    - ``CAN_REVIEW_BOUNTY_TIP`` for officer review.
    - ``CAN_VERIFY_BOUNTY_TIP`` for detective verification.

    Endpoints
    ---------
        GET    /api/bounty-tips/                    → list
        POST   /api/bounty-tips/                    → create (citizen)
        GET    /api/bounty-tips/{id}/               → retrieve
        POST   /api/bounty-tips/{id}/review/        → officer review
        POST   /api/bounty-tips/{id}/verify/        → detective verify
        POST   /api/bounty-tips/lookup-reward/      → reward lookup
    """

    permission_classes = [IsAuthenticated]

    def list(self, request: Request) -> Response:
        """
        GET /api/bounty-tips/

        List bounty tips visible to the authenticated user.

        Steps
        -----
        1. Get queryset via ``BountyTipService.get_bounty_tips(
               requesting_user=request.user,
           )``.
        2. Serialize with ``BountyTipListSerializer(queryset, many=True)``.
        3. Return HTTP 200.
        """
        raise NotImplementedError

    def create(self, request: Request) -> Response:
        """
        POST /api/bounty-tips/

        Citizen submits a bounty tip.

        Steps
        -----
        1. Validate ``request.data`` with ``BountyTipCreateSerializer``.
        2. If invalid, return HTTP 400.
        3. Delegate to ``BountyTipService.submit_tip(
               validated_data=serializer.validated_data,
               requesting_user=request.user,
           )``.
        4. Serialize result with ``BountyTipDetailSerializer``.
        5. Return HTTP 201.

        Example Request
        ---------------
        ::

            POST /api/bounty-tips/
            {
                "suspect": 12,
                "case": 5,
                "information": "Saw the suspect at the docks at 3 AM."
            }
        """
        raise NotImplementedError

    def retrieve(self, request: Request, pk: int = None) -> Response:
        """
        GET /api/bounty-tips/{id}/

        Retrieve a single bounty tip detail.

        Steps
        -----
        1. Fetch tip by PK.
        2. Serialize with ``BountyTipDetailSerializer``.
        3. Return HTTP 200.
        """
        raise NotImplementedError

    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/bounty-tips/{id}/review/

        **Police Officer reviews a bounty tip.**

        Steps
        -----
        1. Validate ``request.data`` with ``BountyTipReviewSerializer``.
        2. If invalid, return HTTP 400.
        3. Delegate to ``BountyTipService.officer_review_tip(
               tip_id=pk,
               officer_user=request.user,
               decision=validated_data["decision"],
               review_notes=validated_data.get("review_notes", ""),
           )``.
        4. Serialize result with ``BountyTipDetailSerializer``.
        5. Return HTTP 200.

        Example Request
        ---------------
        ::

            POST /api/bounty-tips/7/review/
            {"decision": "accept", "review_notes": "Information appears credible."}
        """
        raise NotImplementedError

    @action(detail=True, methods=["post"], url_path="verify")
    def verify(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/bounty-tips/{id}/verify/

        **Detective verifies a bounty tip.**

        Upon verification, a unique reward code is generated for the
        informant.

        Steps
        -----
        1. Validate ``request.data`` with ``BountyTipVerifySerializer``.
        2. If invalid, return HTTP 400.
        3. Delegate to ``BountyTipService.detective_verify_tip(
               tip_id=pk,
               detective_user=request.user,
               decision=validated_data["decision"],
               verification_notes=validated_data.get("verification_notes", ""),
           )``.
        4. Serialize result with ``BountyTipDetailSerializer``.
        5. Return HTTP 200.

        Example Request
        ---------------
        ::

            POST /api/bounty-tips/7/verify/
            {"decision": "verify", "verification_notes": "Info confirmed by field check."}
        """
        raise NotImplementedError

    @action(detail=False, methods=["post"], url_path="lookup-reward")
    def lookup_reward(self, request: Request) -> Response:
        """
        POST /api/bounty-tips/lookup-reward/

        **Look up bounty reward using citizen's national ID and unique code.**

        Any police rank can use this to verify a reward claim at the
        station (project-doc §4.8).

        Steps
        -----
        1. Validate ``request.data`` with ``BountyRewardLookupSerializer``.
        2. If invalid, return HTTP 400.
        3. Delegate to ``BountyTipService.lookup_reward(
               national_id=validated_data["national_id"],
               unique_code=validated_data["unique_code"],
               requesting_user=request.user,
           )``.
        4. Return HTTP 200 with the reward info dict.

        Example Request
        ---------------
        ::

            POST /api/bounty-tips/lookup-reward/
            {"national_id": "1234567890", "unique_code": "A1B2C3D4E5F6"}

        Example Response
        ----------------
        ::

            {
                "tip_id": 7,
                "informant_name": "John Citizen",
                "informant_national_id": "1234567890",
                "reward_amount": 1520000000,
                "is_claimed": false,
                "suspect_name": "Roy Earle",
                "case_id": 5
            }
        """
        raise NotImplementedError
