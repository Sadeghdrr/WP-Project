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

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
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
    CaptainVerdictSerializer,
    ChiefApprovalSerializer,
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
    VerdictService,
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
    @extend_schema(
        summary="List suspects",
        description=(
            "List suspects visible to the authenticated user with optional "
            "query-parameter filtering. Requires authentication."
        ),
        parameters=[
            OpenApiParameter(name="status", type=str, location=OpenApiParameter.QUERY, description="Filter by suspect status."),
            OpenApiParameter(name="case", type=int, location=OpenApiParameter.QUERY, description="Filter by associated case PK."),
            OpenApiParameter(name="national_id", type=str, location=OpenApiParameter.QUERY, description="Exact match on national ID."),
            OpenApiParameter(name="search", type=str, location=OpenApiParameter.QUERY, description="Free-text search on name/aliases/description."),
            OpenApiParameter(name="most_wanted", type=bool, location=OpenApiParameter.QUERY, description="If true, only suspects wanted > 30 days."),
            OpenApiParameter(name="approval_status", type=str, location=OpenApiParameter.QUERY, description="Filter by approval: pending, approved, rejected."),
        ],
        responses={
            200: OpenApiResponse(response=SuspectListSerializer(many=True), description="List of suspects."),
        },
        tags=["Suspects"],
    )
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

    @extend_schema(
        summary="Identify a new suspect",
        description=(
            "Create a new suspect and link them to a case. "
            "Requires Detective role (CAN_IDENTIFY_SUSPECT permission)."
        ),
        request=SuspectCreateSerializer,
        responses={
            201: OpenApiResponse(response=SuspectDetailSerializer, description="Suspect created."),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Permission denied. Requires Detective role."),
        },
        tags=["Suspects"],
    )
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

    @extend_schema(
        summary="Retrieve suspect details",
        description=(
            "Return full suspect detail with nested interrogations, trials, bails, "
            "and computed ranking properties. Requires authentication."
        ),
        responses={
            200: OpenApiResponse(response=SuspectDetailSerializer, description="Suspect detail."),
            404: OpenApiResponse(description="Suspect not found."),
        },
        tags=["Suspects"],
    )
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

    @extend_schema(
        summary="Update suspect profile",
        description=(
            "Partially update a suspect's mutable profile fields (name, address, etc.). "
            "Status changes use dedicated workflow endpoints. Requires Detective role."
        ),
        request=SuspectUpdateSerializer,
        responses={
            200: OpenApiResponse(response=SuspectDetailSerializer, description="Suspect updated."),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Permission denied."),
        },
        tags=["Suspects"],
    )
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
    @extend_schema(
        summary="List most-wanted suspects",
        description=(
            "Return the Most Wanted list — suspects wanted for more than 30 days, "
            "ranked by most_wanted_score (max_days × max_crime_degree). "
            "Visible to all authenticated users."
        ),
        responses={
            200: OpenApiResponse(response=MostWantedSerializer(many=True), description="Most wanted list."),
        },
        tags=["Suspects"],
    )
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
    @extend_schema(
        summary="Approve or reject suspect",
        description=(
            "Sergeant approves or rejects a suspect identification by the Detective. "
            "If rejected, a rejection_message is required. Requires Sergeant role."
        ),
        request=SuspectApprovalSerializer,
        responses={
            200: OpenApiResponse(response=SuspectDetailSerializer, description="Approval decision processed."),
            400: OpenApiResponse(description="Validation error or invalid status."),
            403: OpenApiResponse(description="Permission denied. Requires Sergeant role."),
        },
        tags=["Suspects – Workflow"],
    )
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
    @extend_schema(
        summary="Issue arrest warrant",
        description=(
            "Sergeant issues an arrest warrant for an approved suspect. "
            "The suspect must be approved and in WANTED status. Requires Sergeant role."
        ),
        request=ArrestWarrantSerializer,
        responses={
            200: OpenApiResponse(response=SuspectDetailSerializer, description="Warrant issued."),
            400: OpenApiResponse(description="Suspect not approved or not in WANTED status."),
            403: OpenApiResponse(description="Permission denied. Requires CAN_ISSUE_ARREST_WARRANT."),
        },
        tags=["Suspects – Workflow"],
    )
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
    @extend_schema(
        summary="Execute suspect arrest",
        description=(
            "Execute the arrest of a suspect, transitioning to In Custody status. "
            "Requires a valid warrant or a warrant_override_justification. "
            "Requires Sergeant or Captain role."
        ),
        request=ArrestPayloadSerializer,
        responses={
            200: OpenApiResponse(response=SuspectDetailSerializer, description="Arrest executed."),
            400: OpenApiResponse(description="Invalid status, missing warrant and no override."),
            403: OpenApiResponse(description="Permission denied."),
        },
        tags=["Suspects – Workflow"],
    )
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
    @extend_schema(
        summary="Transition suspect status",
        description=(
            "Generic status transition for non-arrest lifecycle changes. "
            "Allowed transitions depend on current status and user role."
        ),
        request=SuspectStatusTransitionSerializer,
        responses={
            200: OpenApiResponse(response=SuspectDetailSerializer, description="Status transitioned."),
            400: OpenApiResponse(description="Invalid transition from current status."),
            403: OpenApiResponse(description="Permission denied."),
        },
        tags=["Suspects – Workflow"],
    )
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

    @action(detail=True, methods=["post"], url_path="captain-verdict")
    def captain_verdict(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/suspects/{id}/captain-verdict/

        **Captain renders a verdict on a suspect after reviewing
        interrogation scores and evidence.**

        For CRITICAL crime-level cases, this sets the suspect to
        PENDING_CHIEF_APPROVAL. For other levels, the suspect is
        forwarded directly to trial (UNDER_TRIAL).

        Example Request
        ---------------
        ::

            POST /api/suspects/12/captain-verdict/
            {
                "verdict": "guilty",
                "notes": "Strong forensic evidence and high interrogation scores."
            }
        """
        serializer = CaptainVerdictSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            suspect = VerdictService.submit_captain_verdict(
                actor=request.user,
                suspect_id=pk,
                verdict=serializer.validated_data["verdict"],
                notes=serializer.validated_data["notes"],
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

    @action(detail=True, methods=["post"], url_path="chief-approval")
    def chief_approval(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/suspects/{id}/chief-approval/

        **Police Chief approves or rejects the Captain's verdict for
        a CRITICAL case suspect.**

        Only available when the suspect is in PENDING_CHIEF_APPROVAL
        status.

        - Approve: suspect moves to UNDER_TRIAL.
        - Reject: suspect reverts to UNDER_INTERROGATION.

        Example Request (Approve)
        -------------------------
        ::

            POST /api/suspects/12/chief-approval/
            {"decision": "approve", "notes": "Evidence supports verdict."}

        Example Request (Reject)
        ------------------------
        ::

            POST /api/suspects/12/chief-approval/
            {
                "decision": "reject",
                "notes": "Insufficient evidence. Re-interrogate."
            }
        """
        serializer = ChiefApprovalSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            suspect = VerdictService.process_chief_approval(
                actor=request.user,
                suspect_id=pk,
                decision=serializer.validated_data["decision"],
                notes=serializer.validated_data.get("notes", ""),
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

    @extend_schema(
        summary="List interrogations for a suspect",
        description="Return all interrogation sessions recorded for the given suspect.",
        responses={200: OpenApiResponse(response=InterrogationListSerializer(many=True), description="Interrogation list.")},
        tags=["Interrogations"],
    )
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
        try:
            qs = InterrogationService.get_interrogations_for_suspect(
                suspect_id=suspect_pk,
                requesting_user=request.user,
            )
        except NotFound as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND,
            )
        except PermissionDenied as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN,
            )
        output = InterrogationListSerializer(qs, many=True)
        return Response(output.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Create interrogation session",
        description=(
            "Record a new interrogation session for the suspect. "
            "Requires CAN_CONDUCT_INTERROGATION permission."
        ),
        request=InterrogationCreateSerializer,
        responses={
            201: OpenApiResponse(response=InterrogationDetailSerializer, description="Interrogation created."),
            400: OpenApiResponse(description="Validation error."),
        },
        tags=["Interrogations"],
    )
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
        serializer = InterrogationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            interrogation = InterrogationService.create_interrogation(
                suspect_id=suspect_pk,
                validated_data=serializer.validated_data,
                requesting_user=request.user,
            )
        except PermissionDenied as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN,
            )
        except NotFound as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND,
            )
        except DomainError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST,
            )
        output = InterrogationDetailSerializer(interrogation)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Retrieve interrogation detail",
        description="Fetch a single interrogation session by ID.",
        responses={200: OpenApiResponse(response=InterrogationDetailSerializer, description="Interrogation detail.")},
        tags=["Interrogations"],
    )
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
        try:
            interrogation = InterrogationService.get_interrogation_detail(
                interrogation_id=pk,
            )
        except NotFound as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND,
            )
        output = InterrogationDetailSerializer(interrogation)
        return Response(output.data, status=status.HTTP_200_OK)


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

    @extend_schema(
        summary="List trials for a suspect",
        description="Return all trial records for the given suspect.",
        responses={200: OpenApiResponse(response=TrialListSerializer(many=True), description="Trial list.")},
        tags=["Trials"],
    )
    def list(self, request: Request, suspect_pk: int = None) -> Response:
        """
        GET /api/suspects/{suspect_pk}/trials/

        List all trial records for the given suspect.
        """
        try:
            qs = TrialService.get_trials_for_suspect(
                suspect_id=suspect_pk,
                requesting_user=request.user,
            )
            serializer = TrialListSerializer(qs, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except NotFound as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        summary="Create trial record",
        description="Record a trial verdict for the suspect. Requires CAN_JUDGE_TRIAL permission.",
        request=TrialCreateSerializer,
        responses={
            201: OpenApiResponse(response=TrialDetailSerializer, description="Trial created."),
            400: OpenApiResponse(description="Validation error."),
        },
        tags=["Trials"],
    )
    def create(self, request: Request, suspect_pk: int = None) -> Response:
        """
        POST /api/suspects/{suspect_pk}/trials/

        Create a trial record for the suspect (Judge action).
        """
        serializer = TrialCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            trial = TrialService.create_trial(
                suspect_id=suspect_pk,
                validated_data=serializer.validated_data,
                requesting_user=request.user,
            )
            result = TrialDetailSerializer(trial)
            return Response(result.data, status=status.HTTP_201_CREATED)
        except PermissionDenied as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except NotFound as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except DomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Retrieve trial detail",
        description="Fetch a single trial record by ID.",
        responses={200: OpenApiResponse(response=TrialDetailSerializer, description="Trial detail.")},
        tags=["Trials"],
    )
    def retrieve(
        self, request: Request, suspect_pk: int = None, pk: int = None,
    ) -> Response:
        """
        GET /api/suspects/{suspect_pk}/trials/{id}/

        Retrieve a single trial record detail.
        """
        try:
            trial = TrialService.get_trial_detail(trial_id=pk)
            serializer = TrialDetailSerializer(trial)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except NotFound as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)


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

    @extend_schema(
        summary="List bail records for a suspect",
        description="Return all bail/fine records for the given suspect.",
        responses={200: OpenApiResponse(response=BailListSerializer(many=True), description="Bail list.")},
        tags=["Bail"],
    )
    def list(self, request: Request, suspect_pk: int = None) -> Response:
        """
        GET /api/suspects/{suspect_pk}/bails/

        List all bail records for the given suspect.
        """
        try:
            bails = BailService.get_bails_for_suspect(
                suspect_id=suspect_pk,
                requesting_user=request.user,
            )
        except NotFound as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND,
            )
        serializer = BailListSerializer(bails, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Create bail record",
        description="Set a bail amount for the suspect. Requires CAN_SET_BAIL_AMOUNT permission.",
        request=BailCreateSerializer,
        responses={
            201: OpenApiResponse(response=BailDetailSerializer, description="Bail created."),
            400: OpenApiResponse(description="Validation error."),
        },
        tags=["Bail"],
    )
    def create(self, request: Request, suspect_pk: int = None) -> Response:
        """
        POST /api/suspects/{suspect_pk}/bails/

        Create a bail record for the suspect (Sergeant action).
        """
        serializer = BailCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            bail = BailService.create_bail(
                actor=request.user,
                suspect_id=suspect_pk,
                amount=serializer.validated_data["amount"],
                conditions=serializer.validated_data.get("conditions", ""),
            )
        except PermissionDenied as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN,
            )
        except NotFound as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND,
            )
        except DomainError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST,
            )
        output = BailDetailSerializer(bail)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Retrieve bail detail",
        description="Fetch a single bail record by ID.",
        responses={200: OpenApiResponse(response=BailDetailSerializer, description="Bail detail.")},
        tags=["Bail"],
    )
    def retrieve(
        self, request: Request, suspect_pk: int = None, pk: int = None,
    ) -> Response:
        """
        GET /api/suspects/{suspect_pk}/bails/{id}/

        Retrieve a single bail record detail.
        """
        try:
            bail = BailService.get_bail_detail(
                suspect_id=suspect_pk,
                bail_id=pk,
                requesting_user=request.user,
            )
        except NotFound as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND,
            )
        serializer = BailDetailSerializer(bail)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="pay")
    @extend_schema(
        summary="Process bail payment",
        description="Process bail payment via payment gateway callback.",
        request=None,
        responses={
            200: OpenApiResponse(response=BailDetailSerializer, description="Payment processed."),
            400: OpenApiResponse(description="Payment processing failed."),
        },
        tags=["Bail"],
    )
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

    @extend_schema(
        summary="List bounty tips",
        description="Return bounty tips visible to the authenticated user.",
        responses={200: OpenApiResponse(response=BountyTipListSerializer(many=True), description="Bounty tip list.")},
        tags=["Bounty Tips"],
    )
    def list(self, request: Request) -> Response:
        """
        GET /api/bounty-tips/

        List bounty tips visible to the authenticated user.
        """
        tips = BountyTipService.get_bounty_tips(
            requesting_user=request.user,
        )
        serializer = BountyTipListSerializer(tips, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Submit a bounty tip",
        description="Citizen submits a tip about a suspect or case.",
        request=BountyTipCreateSerializer,
        responses={
            201: OpenApiResponse(response=BountyTipDetailSerializer, description="Tip submitted."),
            400: OpenApiResponse(description="Validation error."),
        },
        tags=["Bounty Tips"],
    )
    def create(self, request: Request) -> Response:
        """
        POST /api/bounty-tips/

        Citizen submits a bounty tip.
        """
        serializer = BountyTipCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            tip = BountyTipService.submit_tip(
                validated_data=serializer.validated_data,
                requesting_user=request.user,
            )
        except DomainError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST,
            )
        output = BountyTipDetailSerializer(tip)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Retrieve bounty tip detail",
        description="Fetch a single bounty tip by ID.",
        responses={200: OpenApiResponse(response=BountyTipDetailSerializer, description="Tip detail.")},
        tags=["Bounty Tips"],
    )
    def retrieve(self, request: Request, pk: int = None) -> Response:
        """
        GET /api/bounty-tips/{id}/

        Retrieve a single bounty tip detail.
        """
        try:
            tip = BountyTip.objects.select_related(
                "suspect", "case", "informant", "reviewed_by", "verified_by",
            ).get(pk=pk)
        except BountyTip.DoesNotExist:
            return Response(
                {"detail": f"Bounty tip with id {pk} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = BountyTipDetailSerializer(tip)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="review")
    @extend_schema(
        summary="Officer reviews bounty tip",
        description="Police Officer reviews a submitted bounty tip (accept/reject).",
        request=BountyTipReviewSerializer,
        responses={
            200: OpenApiResponse(response=BountyTipDetailSerializer, description="Review recorded."),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Requires CAN_REVIEW_BOUNTY_TIP."),
        },
        tags=["Bounty Tips"],
    )
    def review(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/bounty-tips/{id}/review/

        Police Officer reviews a bounty tip.
        """
        serializer = BountyTipReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            tip = BountyTipService.officer_review_tip(
                tip_id=pk,
                officer_user=request.user,
                decision=serializer.validated_data["decision"],
                review_notes=serializer.validated_data.get("review_notes", ""),
            )
        except PermissionDenied as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN,
            )
        except NotFound as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND,
            )
        except (DomainError, InvalidTransition) as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST,
            )
        output = BountyTipDetailSerializer(tip)
        return Response(output.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="verify")
    @extend_schema(
        summary="Detective verifies bounty tip",
        description=(
            "Detective verifies a bounty tip. A unique reward code is generated "
            "for the informant upon verification."
        ),
        request=BountyTipVerifySerializer,
        responses={
            200: OpenApiResponse(response=BountyTipDetailSerializer, description="Verification recorded."),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Requires CAN_VERIFY_BOUNTY_TIP."),
        },
        tags=["Bounty Tips"],
    )
    def verify(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/bounty-tips/{id}/verify/

        Detective verifies a bounty tip. Upon verification, a unique
        reward code is generated for the informant.
        """
        serializer = BountyTipVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            tip = BountyTipService.detective_verify_tip(
                tip_id=pk,
                detective_user=request.user,
                decision=serializer.validated_data["decision"],
                verification_notes=serializer.validated_data.get(
                    "verification_notes", "",
                ),
            )
        except PermissionDenied as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN,
            )
        except NotFound as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND,
            )
        except (DomainError, InvalidTransition) as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST,
            )
        output = BountyTipDetailSerializer(tip)
        return Response(output.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="lookup-reward")
    @extend_schema(
        summary="Look up bounty reward",
        description=(
            "Look up a bounty reward using the citizen’s national ID and unique code. "
            "Any authenticated user can verify a reward claim at the station."
        ),
        request=BountyRewardLookupSerializer,
        responses={
            200: OpenApiResponse(description="Reward info dict."),
            400: OpenApiResponse(description="Validation error or no matching reward."),
        },
        tags=["Bounty Tips"],
    )
    def lookup_reward(self, request: Request) -> Response:
        """
        POST /api/bounty-tips/lookup-reward/

        Look up bounty reward using citizen's national ID and unique code.
        """
        serializer = BountyRewardLookupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = BountyTipService.lookup_reward(
                national_id=serializer.validated_data["national_id"],
                unique_code=serializer.validated_data["unique_code"],
                requesting_user=request.user,
            )
        except NotFound as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND,
            )
        except DomainError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(result, status=status.HTTP_200_OK)
