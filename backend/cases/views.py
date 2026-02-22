"""
Cases app ViewSets.

Architecture: Views are intentionally thin.
Every view follows the strict three-step pattern:

    1. Parse / validate input via a serializer.
    2. Delegate all business logic to the appropriate service class.
    3. Serialize the result and return a DRF ``Response``.

No database queries, workflow logic, or formula math lives here.

ViewSets
--------
- ``CaseViewSet`` — The single ViewSet for all case-related endpoints.
  Custom @action methods handle all workflow, assignment, and sub-resource
  operations so the URL structure stays clean and discoverable.
"""

from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
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

from core.domain.exceptions import NotFound, PermissionDenied

from .models import Case, CaseComplainant
from .serializers import (
    AddComplainantSerializer,
    AssignPersonnelSerializer,
    CadetReviewSerializer,
    CaseCalculationsSerializer,
    CaseComplainantSerializer,
    CaseDetailSerializer,
    CaseFilterSerializer,
    CaseListSerializer,
    CaseStatusLogSerializer,
    CaseTransitionSerializer,
    CaseUpdateSerializer,
    CaseWitnessCreateSerializer,
    CaseWitnessSerializer,
    ComplainantReviewSerializer,
    ComplaintCaseCreateSerializer,
    CrimeSceneCaseCreateSerializer,
    OfficerReviewSerializer,
    ResubmitComplaintSerializer,
    SergeantReviewSerializer,
)
from .services import (
    CaseAssignmentService,
    CaseCalculationService,
    CaseComplainantService,
    CaseCreationService,
    CaseQueryService,
    CaseWitnessService,
    CaseWorkflowService,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class CaseViewSet(viewsets.ViewSet):
    """
    Central ViewSet for the cases app.

    Uses ``viewsets.ViewSet`` (not ``ModelViewSet``) so every action is
    explicitly defined, preventing accidental exposure of unintended
    CRUD operations.

    All list/retrieve actions use ``get_object_or_404`` helpers.
    All write actions wrap service calls in try/except to convert
    service-layer exceptions into appropriate HTTP responses.

    Permission Strategy
    -------------------
    The base permission is ``IsAuthenticated``.  Fine-grained permission
    checks (role based, ownership based) are enforced exclusively inside
    the service layer — never in the view.
    """

    permission_classes = [IsAuthenticated]

    # ── Helpers ──────────────────────────────────────────────────────

    def _get_case(self, pk: int) -> Case:
        """
        Retrieve a case by PK.  Raises HTTP 404 if not found.
        """
        return get_object_or_404(Case, pk=pk)

    def _get_complainant(self, case: Case, complainant_pk: int) -> CaseComplainant:
        """
        Retrieve a CaseComplainant by PK scoped to a case.  Raises 404.
        """
        return get_object_or_404(CaseComplainant, pk=complainant_pk, case=case)

    # ── Standard CRUD ────────────────────────────────────────────────
    @extend_schema(
        summary="List cases",
        description=(
            "List cases visible to the authenticated user with optional filtering. "
            "Requires authentication."
        ),
        parameters=[
            OpenApiParameter(name="status", type=str, location=OpenApiParameter.QUERY, description="Filter by case status."),
            OpenApiParameter(name="crime_level", type=int, location=OpenApiParameter.QUERY, description="Filter by crime level (1–4)."),
            OpenApiParameter(name="detective", type=int, location=OpenApiParameter.QUERY, description="Filter by assigned detective PK."),
            OpenApiParameter(name="creation_type", type=str, location=OpenApiParameter.QUERY, description="Filter by creation type: 'complaint' or 'crime_scene'."),
            OpenApiParameter(name="created_after", type=str, location=OpenApiParameter.QUERY, description="ISO 8601 date. Cases created on or after."),
            OpenApiParameter(name="created_before", type=str, location=OpenApiParameter.QUERY, description="ISO 8601 date. Cases created on or before."),
            OpenApiParameter(name="search", type=str, location=OpenApiParameter.QUERY, description="Free-text search on title/description."),
        ],
        responses={
            200: OpenApiResponse(response=CaseListSerializer(many=True), description="Filtered list of cases."),
        },
        tags=["Cases"],
    )
    def list(self, request: Request) -> Response:
        """
        GET /api/cases/

        List cases visible to the authenticated user, with optional filtering.
        """
        filter_serializer = CaseFilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        filters = filter_serializer.validated_data

        qs = CaseQueryService.get_filtered_queryset(request.user, filters)
        serializer = CaseListSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Create a new case",
        description=(
            "Create a new case via complaint or crime-scene path. "
            "Set creation_type to 'complaint' (Civilian/Complainant) or 'crime_scene' (Police Officer+). "
            "Requires authentication."
        ),
        request=ComplaintCaseCreateSerializer,
        responses={
            201: OpenApiResponse(response=CaseDetailSerializer, description="Case created successfully."),
            400: OpenApiResponse(description="Validation error or invalid creation_type."),
            403: OpenApiResponse(description="Permission denied."),
        },
        tags=["Cases"],
    )
    def create(self, request: Request) -> Response:
        """
        POST /api/cases/

        Create a new case.  The creation path (complaint vs crime-scene) is
        determined by the ``creation_type`` field in the request body.

        Steps
        -----
        1. Inspect ``request.data.get("creation_type")``.
        2. If ``"complaint"``:
           a. Validate with ``ComplaintCaseCreateSerializer``.
           b. Delegate to ``CaseCreationService.create_complaint_case``.
        3. If ``"crime_scene"``:
           a. Validate with ``CrimeSceneCaseCreateSerializer``.
           b. Delegate to ``CaseCreationService.create_crime_scene_case``.
        4. Serialize result with ``CaseDetailSerializer``.
        5. Return HTTP 201.
        """
        creation_type = request.data.get("creation_type")

        if creation_type == "complaint":
            serializer = ComplaintCaseCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            case = CaseCreationService.create_complaint_case(
                serializer.validated_data, request.user,
            )
        elif creation_type == "crime_scene":
            serializer = CrimeSceneCaseCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            case = CaseCreationService.create_crime_scene_case(
                serializer.validated_data, request.user,
            )
        else:
            return Response(
                {"detail": "creation_type must be 'complaint' or 'crime_scene'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        out = CaseDetailSerializer(case, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Retrieve case details",
        description=(
            "Return the full case detail with nested complainants, witnesses, "
            "status logs, and computed formula fields. Requires authentication."
        ),
        responses={
            200: OpenApiResponse(response=CaseDetailSerializer, description="Full case detail."),
            404: OpenApiResponse(description="Case not found."),
        },
        tags=["Cases"],
    )
    def retrieve(self, request: Request, pk: int = None) -> Response:
        """
        GET /api/cases/{id}/

        Return the full case detail with all nested sub-resources and
        computed formula fields.
        """
        case = CaseQueryService.get_case_detail(request.user, pk)
        serializer = CaseDetailSerializer(case, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Partially update case",
        description=(
            "Partially update mutable case metadata (title, description, "
            "incident_date, location). Requires authentication."
        ),
        request=CaseUpdateSerializer,
        responses={
            200: OpenApiResponse(response=CaseDetailSerializer, description="Case updated."),
            400: OpenApiResponse(description="Validation error."),
            404: OpenApiResponse(description="Case not found."),
        },
        tags=["Cases"],
    )
    def partial_update(self, request: Request, pk: int = None) -> Response:
        """
        PATCH /api/cases/{id}/

        Partially update mutable case metadata fields (title, description,
        incident_date, location).

        Steps
        -----
        1. ``case = self._get_case(pk)``.
        2. Validate with ``CaseUpdateSerializer(case, data=request.data, partial=True)``.
        3. Apply updates (simple field writes — no service needed for this).
        4. Return HTTP 200 with ``CaseDetailSerializer`` payload.
        """
        raise NotImplementedError

    @extend_schema(
        summary="Delete a case",
        description=(
            "Hard-delete a case. Restricted to System Admin only."
        ),
        responses={
            204: OpenApiResponse(description="Case deleted."),
            403: OpenApiResponse(description="Permission denied. Requires Admin."),
            404: OpenApiResponse(description="Case not found."),
        },
        tags=["Cases"],
    )
    def destroy(self, request: Request, pk: int = None) -> Response:
        """
        DELETE /api/cases/{id}/

        Hard-delete a case.  Restricted to Admin roles only; enforced in
        service logic.

        Steps
        -----
        1. ``case = self._get_case(pk)``.
        2. Guard: only admin may delete (check in service or directly here).
        3. ``case.delete()``.
        4. Return HTTP 204.
        """
        raise NotImplementedError

    # ── Workflow @actions ─────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="submit")
    @extend_schema(
        summary="Submit complaint for review",
        description=(
            "Complainant submits a draft complaint for initial Cadet review. "
            "Requires Complainant role (case creator)."
        ),
        request=None,
        responses={
            200: OpenApiResponse(response=CaseDetailSerializer, description="Case submitted for review."),
            403: OpenApiResponse(description="Permission denied. Only the case creator can submit."),
            404: OpenApiResponse(description="Case not found."),
        },
        tags=["Cases – Workflow"],
    )
    def submit(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/cases/{id}/submit/

        Complainant submits a draft complaint for initial Cadet review.

        Steps
        -----
        1. ``case = self._get_case(pk)``.
        2. Delegate to ``CaseWorkflowService.submit_for_review(case, request.user)``.
        3. Return HTTP 200 with ``CaseDetailSerializer`` payload.
        """
        case = self._get_case(pk)
        case = CaseWorkflowService.submit_for_review(case, request.user)
        serializer = CaseDetailSerializer(case, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="resubmit")
    @extend_schema(
        summary="Resubmit returned complaint",
        description=(
            "Complainant edits and re-submits a case that was returned by the Cadet. "
            "After 3 rejections the case is voided. Requires Complainant role."
        ),
        request=ResubmitComplaintSerializer,
        responses={
            200: OpenApiResponse(response=CaseDetailSerializer, description="Case re-submitted."),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Permission denied."),
        },
        tags=["Cases – Workflow"],
    )
    def resubmit(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/cases/{id}/resubmit/

        Complainant edits and re-submits a case that was returned.

        Steps
        -----
        1. ``case = self._get_case(pk)``.
        2. Validate ``request.data`` with ``ResubmitComplaintSerializer``.
        3. Delegate to ``CaseWorkflowService.resubmit_complaint(case, validated_data, request.user)``.
        4. Return HTTP 200 with ``CaseDetailSerializer``.
        """
        case = self._get_case(pk)
        serializer = ResubmitComplaintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case = CaseWorkflowService.resubmit_complaint(
            case, serializer.validated_data, request.user,
        )
        out = CaseDetailSerializer(case, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="cadet-review")
    @extend_schema(
        summary="Cadet reviews complaint",
        description=(
            "Cadet approves or rejects a complaint case. If rejected, a message "
            "is required. Requires Cadet role."
        ),
        request=CadetReviewSerializer,
        responses={
            200: OpenApiResponse(response=CaseDetailSerializer, description="Review processed."),
            400: OpenApiResponse(description="Validation error (e.g. missing rejection message)."),
            403: OpenApiResponse(description="Permission denied. Requires Cadet role."),
        },
        tags=["Cases – Workflow"],
    )
    def cadet_review(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/cases/{id}/cadet-review/

        Cadet approves or rejects a complaint case.

        Steps
        -----
        1. ``case = self._get_case(pk)``.
        2. Validate ``request.data`` with ``CadetReviewSerializer``.
        3. Delegate to ``CaseWorkflowService.process_cadet_review(
               case,
               validated_data["decision"],
               validated_data["message"],
               request.user,
           )``.
        4. Return HTTP 200 with ``CaseDetailSerializer``.
        """
        case = self._get_case(pk)
        serializer = CadetReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case = CaseWorkflowService.process_cadet_review(
            case,
            serializer.validated_data["decision"],
            serializer.validated_data.get("message", ""),
            request.user,
        )
        out = CaseDetailSerializer(case, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="officer-review")
    @extend_schema(
        summary="Officer reviews case",
        description=(
            "Officer approves or rejects a case forwarded by the Cadet. "
            "If rejected, it returns to the Cadet. Requires Police Officer role."
        ),
        request=OfficerReviewSerializer,
        responses={
            200: OpenApiResponse(response=CaseDetailSerializer, description="Review processed."),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Permission denied. Requires Police Officer role."),
        },
        tags=["Cases – Workflow"],
    )
    def officer_review(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/cases/{id}/officer-review/

        Officer approves or rejects a case forwarded by the Cadet.

        Steps
        -----
        1. ``case = self._get_case(pk)``.
        2. Validate with ``OfficerReviewSerializer``.
        3. Delegate to ``CaseWorkflowService.process_officer_review``.
        4. Return HTTP 200 with ``CaseDetailSerializer``.
        """
        case = self._get_case(pk)
        serializer = OfficerReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case = CaseWorkflowService.process_officer_review(
            case,
            serializer.validated_data["decision"],
            serializer.validated_data.get("message", ""),
            request.user,
        )
        out = CaseDetailSerializer(case, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="approve-crime-scene")
    @extend_schema(
        summary="Approve crime-scene case",
        description=(
            "Superior approves a crime-scene case (PENDING_APPROVAL → OPEN). "
            "If registered by Police Chief, no approval needed. Requires a rank above the registrar."
        ),
        request=None,
        responses={
            200: OpenApiResponse(response=CaseDetailSerializer, description="Crime-scene case approved."),
            403: OpenApiResponse(description="Permission denied. Requires superior rank."),
            404: OpenApiResponse(description="Case not found."),
        },
        tags=["Cases – Workflow"],
    )
    def approve_crime_scene(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/cases/{id}/approve-crime-scene/

        Superior approves a crime-scene case (PENDING_APPROVAL → OPEN).

        Steps
        -----
        1. ``case = self._get_case(pk)``.
        2. Delegate to ``CaseWorkflowService.approve_crime_scene_case(case, request.user)``.
        3. Return HTTP 200 with ``CaseDetailSerializer``.
        """
        case = self._get_case(pk)
        case = CaseWorkflowService.approve_crime_scene_case(case, request.user)
        out = CaseDetailSerializer(case, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="declare-suspects")
    @extend_schema(
        summary="Declare suspects identified",
        description=(
            "Detective declares suspects have been identified and escalates to "
            "Sergeant review. Requires Detective role."
        ),
        request=None,
        responses={
            200: OpenApiResponse(response=CaseDetailSerializer, description="Suspects declared, sent for Sergeant review."),
            403: OpenApiResponse(description="Permission denied. Requires Detective role."),
        },
        tags=["Cases – Workflow"],
    )
    def declare_suspects(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/cases/{id}/declare-suspects/

        Detective declares suspects identified and escalates to Sergeant review.
        (INVESTIGATION → SUSPECT_IDENTIFIED → SERGEANT_REVIEW)

        Steps
        -----
        1. ``case = self._get_case(pk)``.
        2. Delegate to ``CaseWorkflowService.declare_suspects_identified(case, request.user)``.
        3. Return HTTP 200 with ``CaseDetailSerializer``.
        """
        case = self._get_case(pk)
        case = CaseWorkflowService.declare_suspects_identified(case, request.user)
        out = CaseDetailSerializer(case, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="sergeant-review")
    @extend_schema(
        summary="Sergeant reviews suspect list",
        description=(
            "Sergeant approves arrest of suspects or rejects and returns to Detective. "
            "Requires Sergeant role."
        ),
        request=SergeantReviewSerializer,
        responses={
            200: OpenApiResponse(response=CaseDetailSerializer, description="Sergeant review processed."),
            400: OpenApiResponse(description="Validation error (missing rejection message)."),
            403: OpenApiResponse(description="Permission denied. Requires Sergeant role."),
        },
        tags=["Cases – Workflow"],
    )
    def sergeant_review(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/cases/{id}/sergeant-review/

        Sergeant approves arrest or rejects and returns to Detective.

        Steps
        -----
        1. ``case = self._get_case(pk)``.
        2. Validate with ``SergeantReviewSerializer``.
        3. Delegate to ``CaseWorkflowService.process_sergeant_review``.
        4. Return HTTP 200 with ``CaseDetailSerializer``.
        """
        case = self._get_case(pk)
        serializer = SergeantReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case = CaseWorkflowService.process_sergeant_review(
            case,
            serializer.validated_data["decision"],
            serializer.validated_data.get("message", ""),
            request.user,
        )
        out = CaseDetailSerializer(case, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="forward-judiciary")
    @extend_schema(
        summary="Forward case to judiciary",
        description=(
            "Captain or Police Chief forwards the case to the judiciary for trial. "
            "For critical-level crimes, Police Chief approval is required. "
            "Requires Captain or Police Chief role."
        ),
        request=None,
        responses={
            200: OpenApiResponse(response=CaseDetailSerializer, description="Case forwarded to judiciary."),
            403: OpenApiResponse(description="Permission denied. Requires Captain or Police Chief."),
        },
        tags=["Cases – Workflow"],
    )
    def forward_judiciary(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/cases/{id}/forward-judiciary/

        Captain or Chief forwards the case to the judiciary system.
        For critical cases the flow passes through CHIEF_REVIEW first.

        Steps
        -----
        1. ``case = self._get_case(pk)``.
        2. Delegate to ``CaseWorkflowService.forward_to_judiciary(case, request.user)``.
        3. Return HTTP 200 with ``CaseDetailSerializer``.
        """
        case = self._get_case(pk)
        case = CaseWorkflowService.forward_to_judiciary(case, request.user)
        out = CaseDetailSerializer(case, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="transition")
    @extend_schema(
        summary="Generic case state transition",
        description=(
            "Centralized state-transition endpoint for transitions without a dedicated action. "
            "The service layer validates allowed transitions based on current status and user role."
        ),
        request=CaseTransitionSerializer,
        responses={
            200: OpenApiResponse(response=CaseDetailSerializer, description="Transition applied."),
            400: OpenApiResponse(description="Invalid transition or missing message."),
            403: OpenApiResponse(description="Permission denied."),
        },
        tags=["Cases – Workflow"],
    )
    def transition(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/cases/{id}/transition/

        **Centralized generic state-transition endpoint.**

        Used for transitions that do not have a dedicated semantic action
        (e.g. INTERROGATION → CAPTAIN_REVIEW, JUDICIARY → CLOSED).

        Steps
        -----
        1. ``case = self._get_case(pk)``.
        2. Validate ``request.data`` with ``CaseTransitionSerializer``.
        3. Delegate to ``CaseWorkflowService.transition_state(
               case,
               validated_data["target_status"],
               request.user,
               validated_data.get("message", ""),
           )``.
        4. Return HTTP 200 with ``CaseDetailSerializer``.
        """
        case = self._get_case(pk)
        serializer = CaseTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case = CaseWorkflowService.transition_state(
            case,
            serializer.validated_data["target_status"],
            request.user,
            serializer.validated_data.get("message", ""),
        )
        out = CaseDetailSerializer(case, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)

    # ── Assignment @actions ───────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="assign-detective")
    @extend_schema(
        summary="Assign detective to case",
        description=(
            "Assign a detective to an open case and move it to INVESTIGATION status. "
            "Requires Sergeant or higher rank."
        ),
        request=AssignPersonnelSerializer,
        responses={
            200: OpenApiResponse(response=CaseDetailSerializer, description="Detective assigned."),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Permission denied."),
            404: OpenApiResponse(description="Case or user not found."),
        },
        tags=["Cases – Assignment"],
    )
    def assign_detective(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/cases/{id}/assign-detective/

        Assign a detective to an open case and move it to INVESTIGATION.

        Steps
        -----
        1. ``case = self._get_case(pk)``.
        2. Validate ``request.data`` with ``AssignPersonnelSerializer``.
        3. Fetch ``detective = get_object_or_404(User, pk=validated_data["user_id"])``.
        4. Delegate to ``CaseAssignmentService.assign_detective(case, detective, request.user)``.
        5. Return HTTP 200 with ``CaseDetailSerializer``.
        """
        case = self._get_case(pk)
        serializer = AssignPersonnelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        detective = get_object_or_404(User, pk=serializer.validated_data["user_id"])
        case = CaseAssignmentService.assign_detective(case, detective, request.user)
        out = CaseDetailSerializer(case, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["delete"], url_path="unassign-detective")
    @extend_schema(
        summary="Unassign detective from case",
        description=(
            "Remove the currently assigned detective from the case. "
            "Requires Sergeant or higher rank."
        ),
        responses={
            200: OpenApiResponse(response=CaseDetailSerializer, description="Detective unassigned."),
            403: OpenApiResponse(description="Permission denied."),
            404: OpenApiResponse(description="Case not found."),
        },
        tags=["Cases – Assignment"],
    )
    def unassign_detective(self, request: Request, pk: int = None) -> Response:
        """
        DELETE /api/cases/{id}/unassign-detective/

        Remove the currently assigned detective.

        Steps
        -----
        1. ``case = self._get_case(pk)``.
        2. Delegate to ``CaseAssignmentService.unassign_role(case, "assigned_detective", request.user)``.
        3. Return HTTP 200 with ``CaseDetailSerializer``.
        """
        case = self._get_case(pk)
        case = CaseAssignmentService.unassign_role(case, "assigned_detective", request.user)
        out = CaseDetailSerializer(case, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="assign-sergeant")
    @extend_schema(
        summary="Assign sergeant to case",
        description=(
            "Assign a sergeant to the case. Requires Captain or higher rank."
        ),
        request=AssignPersonnelSerializer,
        responses={
            200: OpenApiResponse(response=CaseDetailSerializer, description="Sergeant assigned."),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Permission denied."),
        },
        tags=["Cases – Assignment"],
    )
    def assign_sergeant(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/cases/{id}/assign-sergeant/

        Steps
        -----
        1. ``case = self._get_case(pk)``.
        2. Validate with ``AssignPersonnelSerializer``.
        3. Fetch sergeant user.
        4. Delegate to ``CaseAssignmentService.assign_sergeant(case, sergeant, request.user)``.
        5. Return HTTP 200 with ``CaseDetailSerializer``.
        """
        case = self._get_case(pk)
        serializer = AssignPersonnelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sergeant = get_object_or_404(User, pk=serializer.validated_data["user_id"])
        case = CaseAssignmentService.assign_sergeant(case, sergeant, request.user)
        out = CaseDetailSerializer(case, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="assign-captain")
    @extend_schema(
        summary="Assign captain to case",
        description=(
            "Assign a captain to the case. Requires Police Chief or Admin."
        ),
        request=AssignPersonnelSerializer,
        responses={
            200: OpenApiResponse(response=CaseDetailSerializer, description="Captain assigned."),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Permission denied."),
        },
        tags=["Cases – Assignment"],
    )
    def assign_captain(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/cases/{id}/assign-captain/

        Steps
        -----
        Same pattern as ``assign_sergeant`` with ``assign_captain`` service call.
        """
        case = self._get_case(pk)
        serializer = AssignPersonnelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        captain = get_object_or_404(User, pk=serializer.validated_data["user_id"])
        case = CaseAssignmentService.assign_captain(case, captain, request.user)
        out = CaseDetailSerializer(case, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="assign-judge")
    @extend_schema(
        summary="Assign judge to case",
        description=(
            "Assign a judge to the case for trial. Requires Captain or higher rank."
        ),
        request=AssignPersonnelSerializer,
        responses={
            200: OpenApiResponse(response=CaseDetailSerializer, description="Judge assigned."),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Permission denied."),
        },
        tags=["Cases – Assignment"],
    )
    def assign_judge(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/cases/{id}/assign-judge/

        Steps
        -----
        Same pattern as ``assign_sergeant`` with ``assign_judge`` service call.
        """
        case = self._get_case(pk)
        serializer = AssignPersonnelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        judge = get_object_or_404(User, pk=serializer.validated_data["user_id"])
        case = CaseAssignmentService.assign_judge(case, judge, request.user)
        out = CaseDetailSerializer(case, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)

    # ── Sub-resource @actions — Complainants ─────────────────────────

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="complainants",
    )
    @extend_schema(
        summary="List or add complainants",
        description=(
            "GET: List all complainants for a case. "
            "POST: Add a new complainant (provide user_id). "
            "Requires authentication."
        ),
        request=AddComplainantSerializer,
        responses={
            200: OpenApiResponse(response=CaseComplainantSerializer(many=True), description="List of complainants."),
            201: OpenApiResponse(response=CaseComplainantSerializer, description="Complainant added."),
            404: OpenApiResponse(description="Case or user not found."),
        },
        tags=["Cases – Complainants"],
    )
    def complainants(self, request: Request, pk: int = None) -> Response:
        """
        GET  /api/cases/{id}/complainants/ — list all complainants.
        POST /api/cases/{id}/complainants/ — add a new complainant.

        GET Steps
        ---------
        1. ``case = self._get_case(pk)``.
        2. Serialize ``case.complainants.select_related("user", "reviewed_by")``.
        3. Return HTTP 200.

        POST Steps
        ----------
        1. ``case = self._get_case(pk)``.
        2. Validate with ``AddComplainantSerializer``.
        3. Fetch user by ``validated_data["user_id"]``.
        4. Delegate to ``CaseComplainantService.add_complainant(case, user, request.user)``.
        5. Return HTTP 201 with ``CaseComplainantSerializer``.
        """
        case = self._get_case(pk)

        if request.method == "GET":
            qs = case.complainants.select_related("user", "reviewed_by")
            serializer = CaseComplainantSerializer(qs, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # POST
        serializer = AddComplainantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(pk=serializer.validated_data["user_id"]).first()
        if not user:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        complainant = CaseComplainantService.add_complainant(
            case, user, request.user,
        )
        out = CaseComplainantSerializer(complainant)
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["post"],
        url_path=r"complainants/(?P<complainant_pk>[^/.]+)/review",
    )
    @extend_schema(
        summary="Review complainant info",
        description=(
            "Cadet approves or rejects an individual complainant's information. "
            "Requires Cadet role."
        ),
        request=ComplainantReviewSerializer,
        responses={
            200: OpenApiResponse(response=CaseComplainantSerializer, description="Complainant review processed."),
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Permission denied. Requires Cadet role."),
        },
        tags=["Cases – Complainants"],
    )
    def review_complainant(
        self,
        request: Request,
        pk: int = None,
        complainant_pk: int = None,
    ) -> Response:
        """
        POST /api/cases/{id}/complainants/{complainant_pk}/review/

        Cadet approves or rejects an individual complainant's information.

        Steps
        -----
        1. ``case = self._get_case(pk)``.
        2. ``complainant = self._get_complainant(case, complainant_pk)``.
        3. Validate ``request.data`` with ``ComplainantReviewSerializer``.
        4. Delegate to ``CaseComplainantService.review_complainant(
               complainant, validated_data["decision"], request.user
           )``.
        5. Return HTTP 200 with ``CaseComplainantSerializer``.
        """
        case = self._get_case(pk)
        complainant = self._get_complainant(case, complainant_pk)
        serializer = ComplainantReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        complainant = CaseComplainantService.review_complainant(
            complainant,
            serializer.validated_data["decision"],
            request.user,
        )
        out = CaseComplainantSerializer(complainant)
        return Response(out.data, status=status.HTTP_200_OK)

    # ── Sub-resource @actions — Witnesses ────────────────────────────

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="witnesses",
    )
    @extend_schema(
        summary="List or add witnesses",
        description=(
            "GET: List all witnesses for a case. "
            "POST: Add a witness (full_name, phone_number, national_id). "
            "Requires authentication. Adding witnesses is typically for crime-scene cases."
        ),
        request=CaseWitnessCreateSerializer,
        responses={
            200: OpenApiResponse(response=CaseWitnessSerializer(many=True), description="List of witnesses."),
            201: OpenApiResponse(response=CaseWitnessSerializer, description="Witness added."),
            400: OpenApiResponse(description="Validation error."),
        },
        tags=["Cases – Witnesses"],
    )
    def witnesses(self, request: Request, pk: int = None) -> Response:
        """
        GET  /api/cases/{id}/witnesses/ — list witnesses.
        POST /api/cases/{id}/witnesses/ — add a witness.

        GET Steps
        ---------
        Serialize ``case.witnesses.all()`` with ``CaseWitnessSerializer``.

        POST Steps
        ----------
        1. ``case = self._get_case(pk)``.
        2. Validate with ``CaseWitnessCreateSerializer``.
        3. Delegate to ``CaseWitnessService.add_witness(case, validated_data, request.user)``.
        4. Return HTTP 201 with ``CaseWitnessSerializer``.
        """
        case = self._get_case(pk)

        if request.method == "GET":
            qs = case.witnesses.all()
            serializer = CaseWitnessSerializer(qs, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # POST
        serializer = CaseWitnessCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        witness = CaseWitnessService.add_witness(
            case, serializer.validated_data, request.user,
        )
        out = CaseWitnessSerializer(witness)
        return Response(out.data, status=status.HTTP_201_CREATED)

    # ── Sub-resource @actions — Audit & Calculations ─────────────────

    @action(detail=True, methods=["get"], url_path="status-log")
    @extend_schema(
        summary="Get case status audit log",
        description=(
            "Return the immutable status-transition audit trail for the case, "
            "ordered chronologically (newest first). Requires authentication."
        ),
        responses={
            200: OpenApiResponse(response=CaseStatusLogSerializer(many=True), description="Status transition log."),
            404: OpenApiResponse(description="Case not found."),
        },
        tags=["Cases"],
    )
    def status_log(self, request: Request, pk: int = None) -> Response:
        """
        GET /api/cases/{id}/status-log/

        Return the immutable status-transition audit trail for the case,
        ordered chronologically (newest first).

        Steps
        -----
        1. ``case = self._get_case(pk)``.
        2. ``logs = case.status_logs.select_related("changed_by").order_by("-created_at")``.
        3. Serialize with ``CaseStatusLogSerializer(logs, many=True)``.
        4. Return HTTP 200.
        """
        case = self._get_case(pk)
        logs = case.status_logs.select_related("changed_by").order_by("-created_at")
        serializer = CaseStatusLogSerializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="calculations")
    @extend_schema(
        summary="Get case calculations",
        description=(
            "Return computed reward and tracking-threshold values for the case. "
            "Includes crime_level_degree, days_since_creation, tracking_threshold, "
            "and reward_rials. Requires authentication."
        ),
        responses={
            200: OpenApiResponse(response=CaseCalculationsSerializer, description="Case formula outputs."),
            404: OpenApiResponse(description="Case not found."),
        },
        tags=["Cases"],
    )
    def calculations(self, request: Request, pk: int = None) -> Response:
        """
        GET /api/cases/{id}/calculations/

        Return the computed reward and tracking-threshold values for the case.

        Steps
        -----
        1. ``case = self._get_case(pk)``.
        2. ``data = CaseCalculationService.get_calculations_dict(case)``.
        3. Serialize with ``CaseCalculationsSerializer(data)``.
        4. Return HTTP 200.

        Example response::

            {
              "crime_level_degree": 3,
              "days_since_creation": 45,
              "tracking_threshold": 135,
              "reward_rials": 2700000000
            }
        """
        case = self._get_case(pk)
        data = CaseCalculationService.get_calculations_dict(case)
        serializer = CaseCalculationsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
