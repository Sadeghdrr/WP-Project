"""
Evidence app ViewSets.

Architecture: Views are intentionally thin.
Every view follows the strict three-step pattern:

    1. Parse / validate input via a serializer.
    2. Delegate all business logic to the appropriate service class.
    3. Serialize the result and return a DRF ``Response``.

No database queries, workflow logic, permission checks, or XOR
validation lives here.

ViewSets
--------
- ``EvidenceViewSet`` — The single ViewSet for all evidence-related
  endpoints.  Custom ``@action`` methods handle verification workflows,
  file management, case linking, and chain-of-custody retrieval.
"""

from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)

from .models import (
    BiologicalEvidence,
    Evidence,
    EvidenceFile,
    EvidenceType,
)
from .serializers import (
    BiologicalEvidenceDetailSerializer,
    BiologicalEvidenceUpdateSerializer,
    ChainOfCustodyEntrySerializer,
    EvidenceFileReadSerializer,
    EvidenceFileUploadSerializer,
    EvidenceFilterSerializer,
    EvidenceListSerializer,
    EvidencePolymorphicCreateSerializer,
    EvidenceUpdateSerializer,
    IdentityEvidenceDetailSerializer,
    IdentityEvidenceUpdateSerializer,
    LinkCaseSerializer,
    OtherEvidenceDetailSerializer,
    TestimonyEvidenceDetailSerializer,
    TestimonyEvidenceUpdateSerializer,
    UnlinkCaseSerializer,
    VehicleEvidenceDetailSerializer,
    VehicleEvidenceUpdateSerializer,
    VerifyBiologicalEvidenceSerializer,
)
from .services import (
    ChainOfCustodyService,
    EvidenceFileService,
    EvidenceProcessingService,
    EvidenceQueryService,
    MedicalExaminerService,
)


class EvidenceViewSet(viewsets.ViewSet):
    """
    Central ViewSet for the evidence app.

    Uses ``viewsets.ViewSet`` (not ``ModelViewSet``) so every action is
    explicitly defined, preventing accidental exposure of unintended
    CRUD operations.

    Permission Strategy
    -------------------
    The base permission is ``IsAuthenticated``.  Fine-grained permission
    checks (role-based, ownership-based) are enforced exclusively inside
    the service layer — never in the view.
    """

    permission_classes = [IsAuthenticated]
    # Allows drf-spectacular to infer path-parameter types automatically.
    queryset = Evidence.objects.none()

    # ── Serializer Resolution Helpers ────────────────────────────────

    #: Maps ``EvidenceType`` values to their detail (read) serializer.
    _DETAIL_SERIALIZER_MAP: dict[str, type] = {
        EvidenceType.TESTIMONY: TestimonyEvidenceDetailSerializer,
        EvidenceType.BIOLOGICAL: BiologicalEvidenceDetailSerializer,
        EvidenceType.VEHICLE: VehicleEvidenceDetailSerializer,
        EvidenceType.IDENTITY: IdentityEvidenceDetailSerializer,
        EvidenceType.OTHER: OtherEvidenceDetailSerializer,
    }

    #: Maps ``EvidenceType`` values to their update (write) serializer.
    _UPDATE_SERIALIZER_MAP: dict[str, type] = {
        EvidenceType.TESTIMONY: TestimonyEvidenceUpdateSerializer,
        EvidenceType.BIOLOGICAL: BiologicalEvidenceUpdateSerializer,
        EvidenceType.VEHICLE: VehicleEvidenceUpdateSerializer,
        EvidenceType.IDENTITY: IdentityEvidenceUpdateSerializer,
        EvidenceType.OTHER: EvidenceUpdateSerializer,
    }

    def _get_evidence(self, pk: int) -> Evidence:
        """
        Retrieve an evidence item by PK using the query service.
        Resolves to the most specific child type.  Raises domain NotFound.
        """
        return EvidenceQueryService.get_evidence_detail(pk)

    def _get_detail_serializer(self, evidence: Evidence) -> type:
        """Return the detail serializer class for the given evidence's type."""
        return self._DETAIL_SERIALIZER_MAP.get(
            evidence.evidence_type, OtherEvidenceDetailSerializer
        )

    def _get_update_serializer(self, evidence: Evidence) -> type:
        """Return the update serializer class for the given evidence's type."""
        return self._UPDATE_SERIALIZER_MAP.get(
            evidence.evidence_type, EvidenceUpdateSerializer
        )

    # ── Standard CRUD ────────────────────────────────────────────────

    @extend_schema(
        summary="List evidence items",
        description="Return evidence items with optional filters (type, status, case, date range, search).",
        parameters=[
            OpenApiParameter(name="evidence_type", type=str, required=False, description="Filter by evidence type."),
            OpenApiParameter(name="verification_status", type=str, required=False, description="Filter by verification status."),
            OpenApiParameter(name="case", type=int, required=False, description="Filter by linked case ID."),
            OpenApiParameter(name="collected_after", type=str, required=False, description="ISO date — collected on or after."),
            OpenApiParameter(name="collected_before", type=str, required=False, description="ISO date — collected on or before."),
            OpenApiParameter(name="search", type=str, required=False, description="Free-text search across evidence fields."),
        ],
        responses={200: OpenApiResponse(response=EvidenceListSerializer(many=True), description="Evidence list.")},
        tags=["Evidence"],
    )
    def list(self, request: Request) -> Response:
        """GET /api/evidence/ — List evidence with optional filters."""
        filter_serializer = EvidenceFilterSerializer(data=request.query_params)
        if not filter_serializer.is_valid():
            return Response(filter_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        queryset = EvidenceQueryService.get_filtered_queryset(
            request.user, filter_serializer.validated_data
        )
        serializer = EvidenceListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Create evidence (polymorphic)",
        description=(
            "Create a new evidence item. The `evidence_type` field acts as a discriminator "
            "to determine which child serializer validates the rest of the payload. "
            "Supported types: testimony, biological, vehicle, identity, other."
        ),
        request=EvidencePolymorphicCreateSerializer,
        responses={
            201: OpenApiResponse(response=EvidenceListSerializer, description="Evidence created."),
            400: OpenApiResponse(description="Validation error."),
        },
        tags=["Evidence"],
    )
    def create(self, request: Request) -> Response:
        """POST /api/evidence/ — Create polymorphic evidence."""
        # 1. Validate evidence_type discriminator
        poly_serializer = EvidencePolymorphicCreateSerializer(data=request.data)
        if not poly_serializer.is_valid():
            return Response(poly_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        evidence_type = poly_serializer.validated_data["evidence_type"]

        # 2. Validate full payload with the type-specific serializer
        child_serializer_class = EvidencePolymorphicCreateSerializer.get_child_serializer_class(
            evidence_type
        )
        child_serializer = child_serializer_class(data=request.data)
        if not child_serializer.is_valid():
            return Response(child_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 3. Delegate to service
        evidence = EvidenceProcessingService.process_new_evidence(
            evidence_type=evidence_type,
            validated_data=child_serializer.validated_data,
            requesting_user=request.user,
        )

        # 4. Serialize response
        detail_serializer_class = self._get_detail_serializer(evidence)
        response_serializer = detail_serializer_class(evidence)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Retrieve evidence detail",
        description="Fetch full detail for a single evidence item, resolved to its polymorphic subtype.",
        responses={200: OpenApiResponse(response=EvidenceListSerializer, description="Evidence detail (type-specific).")},
        tags=["Evidence"],
    )
    def retrieve(self, request: Request, pk: int = None) -> Response:
        """GET /api/evidence/{id}/ — Evidence detail."""
        evidence = self._get_evidence(pk)
        detail_serializer_class = self._get_detail_serializer(evidence)
        serializer = detail_serializer_class(evidence)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Partial update evidence",
        description="Update evidence fields. The update serializer is selected based on the evidence type.",
        request=EvidenceUpdateSerializer,
        responses={
            200: OpenApiResponse(response=EvidenceListSerializer, description="Evidence updated."),
            400: OpenApiResponse(description="Validation error."),
        },
        tags=["Evidence"],
    )
    def partial_update(self, request: Request, pk: int = None) -> Response:
        """PATCH /api/evidence/{id}/ — Partial update."""
        evidence = self._get_evidence(pk)
        update_serializer_class = self._get_update_serializer(evidence)
        serializer = update_serializer_class(evidence, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated = EvidenceProcessingService.update_evidence(
            evidence, serializer.validated_data, request.user
        )

        detail_serializer_class = self._get_detail_serializer(updated)
        response_serializer = detail_serializer_class(updated)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Delete evidence",
        description="Delete an evidence item.",
        responses={204: OpenApiResponse(description="Deleted.")},
        tags=["Evidence"],
    )
    def destroy(self, request: Request, pk: int = None) -> Response:
        """DELETE /api/evidence/{id}/ — Delete evidence."""
        evidence = self._get_evidence(pk)
        EvidenceProcessingService.delete_evidence(evidence, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── Workflow @actions ─────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="verify")
    @extend_schema(
        summary="Verify biological evidence",
        description="Medical examiner / coroner verifies biological evidence with a forensic result.",
        request=VerifyBiologicalEvidenceSerializer,
        responses={
            200: OpenApiResponse(response=BiologicalEvidenceDetailSerializer, description="Verification recorded."),
            400: OpenApiResponse(description="Validation error or wrong evidence type."),
        },
        tags=["Evidence"],
    )
    def verify(self, request: Request, pk: int = None) -> Response:
        """POST /api/evidence/{id}/verify/ — Coroner verifies biological evidence."""
        serializer = VerifyBiologicalEvidenceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        bio_evidence = MedicalExaminerService.verify_biological_evidence(
            evidence_id=pk,
            examiner_user=request.user,
            decision=serializer.validated_data["decision"],
            forensic_result=serializer.validated_data.get("forensic_result", ""),
            notes=serializer.validated_data.get("notes", ""),
        )

        response_serializer = BiologicalEvidenceDetailSerializer(bio_evidence)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="link-case")
    @extend_schema(
        summary="Link evidence to a case",
        description="Associate an evidence item with a case.",
        request=LinkCaseSerializer,
        responses={200: OpenApiResponse(response=EvidenceListSerializer, description="Evidence linked.")},
        tags=["Evidence"],
    )
    def link_case(self, request: Request, pk: int = None) -> Response:
        """POST /api/evidence/{id}/link-case/ — Link evidence to a case."""
        evidence = self._get_evidence(pk)
        serializer = LinkCaseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated = EvidenceProcessingService.link_evidence_to_case(
            evidence, serializer.validated_data["case_id"], request.user
        )

        detail_serializer_class = self._get_detail_serializer(updated)
        response_serializer = detail_serializer_class(updated)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="unlink-case")
    @extend_schema(
        summary="Unlink evidence from a case",
        description="Remove the association between an evidence item and a case.",
        request=UnlinkCaseSerializer,
        responses={200: OpenApiResponse(response=EvidenceListSerializer, description="Evidence unlinked.")},
        tags=["Evidence"],
    )
    def unlink_case(self, request: Request, pk: int = None) -> Response:
        """POST /api/evidence/{id}/unlink-case/ — Unlink evidence from a case."""
        evidence = self._get_evidence(pk)
        serializer = UnlinkCaseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated = EvidenceProcessingService.unlink_evidence_from_case(
            evidence, serializer.validated_data["case_id"], request.user
        )

        detail_serializer_class = self._get_detail_serializer(updated)
        response_serializer = detail_serializer_class(updated)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    # ── File management @actions ──────────────────────────────────────

    @action(detail=True, methods=["get", "post"], url_path="files")
    @extend_schema(
        summary="List or upload evidence files",
        description=(
            "GET: List all files attached to this evidence item.\n"
            "POST: Upload a new file (multipart/form-data)."
        ),
        request=EvidenceFileUploadSerializer,
        responses={
            200: OpenApiResponse(response=EvidenceFileReadSerializer(many=True), description="File list."),
            201: OpenApiResponse(response=EvidenceFileReadSerializer, description="File uploaded."),
        },
        tags=["Evidence"],
    )
    def files(self, request: Request, pk: int = None) -> Response:
        """
        GET  /api/evidence/{id}/files/ — list attached files.
        POST /api/evidence/{id}/files/ — upload a new file.
        """
        if request.method == "GET":
            files_qs = EvidenceFileService.list_files(pk, request.user)
            serializer = EvidenceFileReadSerializer(files_qs, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # POST — multipart/form-data expected
        serializer = EvidenceFileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        evidence_file = EvidenceFileService.upload_file(
            pk, request.user, serializer.validated_data
        )
        response_serializer = EvidenceFileReadSerializer(evidence_file)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    # ── Audit / history @actions ──────────────────────────────────────

    @action(detail=True, methods=["get"], url_path="chain-of-custody")
    @extend_schema(
        summary="Chain of custody audit trail",
        description="Return the full chain-of-custody log for an evidence item.",
        responses={200: OpenApiResponse(response=ChainOfCustodyEntrySerializer(many=True), description="Custody log.")},
        tags=["Evidence"],
    )
    def chain_of_custody(self, request: Request, pk: int = None) -> Response:
        """GET /api/evidence/{id}/chain-of-custody/ — Audit trail."""
        logs = ChainOfCustodyService.get_chain_of_custody(pk, request.user)
        serializer = ChainOfCustodyEntrySerializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
