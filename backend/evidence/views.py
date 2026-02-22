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

    def retrieve(self, request: Request, pk: int = None) -> Response:
        """GET /api/evidence/{id}/ — Evidence detail."""
        evidence = self._get_evidence(pk)
        detail_serializer_class = self._get_detail_serializer(evidence)
        serializer = detail_serializer_class(evidence)
        return Response(serializer.data, status=status.HTTP_200_OK)

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

    def destroy(self, request: Request, pk: int = None) -> Response:
        """DELETE /api/evidence/{id}/ — Delete evidence."""
        evidence = self._get_evidence(pk)
        EvidenceProcessingService.delete_evidence(evidence, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── Workflow @actions ─────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="verify")
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
    def files(self, request: Request, pk: int = None) -> Response:
        """
        GET  /api/evidence/{id}/files/ — list attached files.
        POST /api/evidence/{id}/files/ — upload a new file.
        """
        evidence = self._get_evidence(pk)

        if request.method == "GET":
            files_qs = EvidenceFileService.get_files_for_evidence(evidence)
            serializer = EvidenceFileReadSerializer(files_qs, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # POST
        serializer = EvidenceFileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        evidence_file = EvidenceFileService.upload_file(
            evidence, serializer.validated_data, request.user
        )
        response_serializer = EvidenceFileReadSerializer(evidence_file)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    # ── Audit / history @actions ──────────────────────────────────────

    @action(detail=True, methods=["get"], url_path="chain-of-custody")
    def chain_of_custody(self, request: Request, pk: int = None) -> Response:
        """GET /api/evidence/{id}/chain-of-custody/ — Audit trail."""
        evidence = self._get_evidence(pk)
        trail = ChainOfCustodyService.get_custody_trail(evidence)
        serializer = ChainOfCustodyEntrySerializer(trail, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
