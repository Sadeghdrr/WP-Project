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
        Resolves to the most specific child type.  Raises HTTP 404.

        Implementation Contract
        -----------------------
        from django.shortcuts import get_object_or_404
        return EvidenceQueryService.get_evidence_detail(pk)
        Wrap in try/except Evidence.DoesNotExist → raise Http404.
        """
        raise NotImplementedError

    def _get_detail_serializer(self, evidence: Evidence) -> type:
        """
        Return the detail serializer class for the given evidence's type.

        Implementation Contract
        -----------------------
        return self._DETAIL_SERIALIZER_MAP.get(
            evidence.evidence_type, OtherEvidenceDetailSerializer
        )
        """
        raise NotImplementedError

    def _get_update_serializer(self, evidence: Evidence) -> type:
        """
        Return the update serializer class for the given evidence's type.

        Implementation Contract
        -----------------------
        return self._UPDATE_SERIALIZER_MAP.get(
            evidence.evidence_type, EvidenceUpdateSerializer
        )
        """
        raise NotImplementedError

    # ── Standard CRUD ────────────────────────────────────────────────

    def list(self, request: Request) -> Response:
        """
        GET /api/evidence/

        List evidence items visible to the authenticated user, with
        optional query-parameter filtering.

        Steps
        -----
        1. Validate query params with
           ``EvidenceFilterSerializer(data=request.query_params)``.
        2. If invalid, return HTTP 400 with errors.
        3. Get queryset via ``EvidenceQueryService.get_filtered_queryset(
               request.user, filter_serializer.validated_data
           )``.
        4. Serialize with ``EvidenceListSerializer(queryset, many=True)``.
        5. Return HTTP 200 with serialised data.

        Example Response
        ----------------
        ::

            [
                {
                    "id": 1,
                    "title": "Bloodstain on Doorframe",
                    "evidence_type": "biological",
                    "evidence_type_display": "Biological / Medical",
                    "case": 5,
                    "registered_by": 12,
                    "registered_by_name": "John Smith",
                    "created_at": "2026-02-20T10:30:00Z",
                    "updated_at": "2026-02-20T10:30:00Z"
                },
                ...
            ]
        """
        raise NotImplementedError

    def create(self, request: Request) -> Response:
        """
        POST /api/evidence/

        Create a new evidence item.  The evidence type is determined by
        the ``evidence_type`` field in the request body.  The request is
        validated using the appropriate type-specific serializer.

        Steps
        -----
        1. Extract ``evidence_type`` from ``request.data``.
        2. Validate ``evidence_type`` with
           ``EvidencePolymorphicCreateSerializer(data=request.data)``.
        3. If ``evidence_type`` valid, get child serializer via
           ``EvidencePolymorphicCreateSerializer.get_child_serializer_class(evidence_type)``.
        4. Validate the full payload with the child serializer.
        5. Delegate to ``EvidenceProcessingService.process_new_evidence(
               evidence_type=evidence_type,
               validated_data=child_serializer.validated_data,
               requesting_user=request.user,
           )``.
        6. Serialize result with the matching detail serializer.
        7. Return HTTP 201 with serialised data.

        Example Request Body (Vehicle)
        --------------------------------
        ::

            {
                "evidence_type": "vehicle",
                "case": 42,
                "title": "Blue Sedan Near Alley",
                "description": "Found parked 50m from the crime scene.",
                "vehicle_model": "Ford Sedan 1947",
                "color": "Blue",
                "license_plate": "LA-4521"
            }

        Error Handling
        --------------
        - HTTP 400 if ``evidence_type`` is invalid.
        - HTTP 400 if type-specific validation fails (e.g. vehicle XOR).
        - HTTP 403 if the user lacks creation permission (raised by service).
        """
        raise NotImplementedError

    def retrieve(self, request: Request, pk: int = None) -> Response:
        """
        GET /api/evidence/{id}/

        Return the full evidence detail with type-specific fields and
        nested file attachments.

        Steps
        -----
        1. ``evidence = self._get_evidence(pk)``.
        2. Determine the detail serializer via
           ``self._get_detail_serializer(evidence)``.
        3. Serialize the evidence instance.
        4. Return HTTP 200.

        Example Response (Biological)
        ------------------------------
        ::

            {
                "id": 7,
                "title": "Hair Sample #3",
                "description": "Found on victim's jacket.",
                "evidence_type": "biological",
                "evidence_type_display": "Biological / Medical",
                "case": 5,
                "registered_by": 12,
                "registered_by_name": "Jane Doe",
                "forensic_result": "",
                "is_verified": false,
                "verified_by": null,
                "verified_by_name": null,
                "files": [
                    {
                        "id": 15,
                        "file": "/media/evidence_files/2026/02/hair_sample.jpg",
                        "file_type": "image",
                        "file_type_display": "Image",
                        "caption": "Close-up photo",
                        "created_at": "2026-02-20T11:00:00Z"
                    }
                ],
                "created_at": "2026-02-20T10:30:00Z",
                "updated_at": "2026-02-20T10:30:00Z"
            }
        """
        raise NotImplementedError

    def partial_update(self, request: Request, pk: int = None) -> Response:
        """
        PATCH /api/evidence/{id}/

        Partially update an evidence item's mutable fields.

        The update serializer is selected based on the evidence's type
        to support type-specific field updates (e.g., ``vehicle_model``
        for vehicles, ``statement_text`` for testimony).

        Steps
        -----
        1. ``evidence = self._get_evidence(pk)``.
        2. Get update serializer class via
           ``self._get_update_serializer(evidence)``.
        3. Validate ``request.data`` with the update serializer:
           ``serializer = UpdateSerializer(evidence, data=request.data, partial=True)``.
        4. If invalid, return HTTP 400.
        5. Delegate to ``EvidenceProcessingService.update_evidence(
               evidence, serializer.validated_data, request.user
           )``.
        6. Serialize result with the matching detail serializer.
        7. Return HTTP 200.

        Notes
        -----
        - ``evidence_type``, ``case``, and ``registered_by`` are
          immutable — they are excluded from all update serializers.
        - Vehicle updates re-validate the XOR constraint by merging
          incoming values with existing instance data.
        """
        raise NotImplementedError

    def destroy(self, request: Request, pk: int = None) -> Response:
        """
        DELETE /api/evidence/{id}/

        Permanently delete an evidence item and its associated files.

        Steps
        -----
        1. ``evidence = self._get_evidence(pk)``.
        2. Delegate to ``EvidenceProcessingService.delete_evidence(
               evidence, request.user
           )``.
        3. Return HTTP 204 (No Content).

        Error Handling
        --------------
        - HTTP 403 if the user lacks delete permission.
        - HTTP 400 if the evidence is verified and cannot be deleted.
        """
        raise NotImplementedError

    # ── Workflow @actions ─────────────────────────────────────────────

    @action(detail=True, methods=["post"], url_path="verify")
    def verify(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/evidence/{id}/verify/

        **Coroner (Medical Examiner) verifies biological evidence.**

        This endpoint is restricted to users with the ``Coroner`` role
        who have the ``CAN_VERIFY_EVIDENCE`` permission.  The service
        layer performs the actual permission check.

        Steps
        -----
        1. Validate ``request.data`` with ``VerifyBiologicalEvidenceSerializer``.
        2. If invalid, return HTTP 400 with validation errors.
        3. Delegate to ``MedicalExaminerService.verify_biological_evidence(
               evidence_id=pk,
               examiner_user=request.user,
               decision=validated_data["decision"],
               forensic_result=validated_data.get("forensic_result", ""),
               notes=validated_data.get("notes", ""),
           )``.
        4. Serialize the result with ``BiologicalEvidenceDetailSerializer``.
        5. Return HTTP 200 on success.

        Error Handling
        --------------
        - HTTP 400 if the evidence is not biological type.
        - HTTP 400 if the evidence is already verified.
        - HTTP 403 if the user lacks Coroner permissions.
        - HTTP 404 if the evidence ID does not exist.

        Example Request
        ---------------
        ::

            POST /api/evidence/7/verify/
            {
                "decision": "approve",
                "forensic_result": "Blood type O+, matches suspect DNA profile.",
                "notes": "Analysis at LAPD forensics lab, ref #2026-0220."
            }

        Example Response
        ----------------
        ::

            {
                "id": 7,
                "title": "Bloodstain on Doorframe",
                "forensic_result": "Blood type O+, matches suspect DNA.",
                "is_verified": true,
                "verified_by": 8,
                "verified_by_name": "Dr. Malcolm Stone",
                ...
            }
        """
        raise NotImplementedError

    @action(detail=True, methods=["post"], url_path="link-case")
    def link_case(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/evidence/{id}/link-case/

        Link this evidence item to a specific case.

        Steps
        -----
        1. ``evidence = self._get_evidence(pk)``.
        2. Validate ``request.data`` with ``LinkCaseSerializer``.
        3. Delegate to ``EvidenceProcessingService.link_evidence_to_case(
               evidence,
               validated_data["case_id"],
               request.user,
           )``.
        4. Serialize result with the matching detail serializer.
        5. Return HTTP 200.

        Example Request
        ---------------
        ::

            POST /api/evidence/7/link-case/
            {"case_id": 42}
        """
        raise NotImplementedError

    @action(detail=True, methods=["post"], url_path="unlink-case")
    def unlink_case(self, request: Request, pk: int = None) -> Response:
        """
        POST /api/evidence/{id}/unlink-case/

        Remove the link between this evidence and the specified case.

        Steps
        -----
        1. ``evidence = self._get_evidence(pk)``.
        2. Validate ``request.data`` with ``UnlinkCaseSerializer``.
        3. Delegate to ``EvidenceProcessingService.unlink_evidence_from_case(
               evidence,
               validated_data["case_id"],
               request.user,
           )``.
        4. Serialize result with the matching detail serializer.
        5. Return HTTP 200.

        Notes
        -----
        Since the current schema uses a non-nullable FK, unlinking
        without a replacement will raise a ``ValidationError``.  Use
        ``link-case`` to reassign evidence to another case instead.
        """
        raise NotImplementedError

    # ── File management @actions ──────────────────────────────────────

    @action(detail=True, methods=["get", "post"], url_path="files")
    def files(self, request: Request, pk: int = None) -> Response:
        """
        GET  /api/evidence/{id}/files/ — list all attached files.
        POST /api/evidence/{id}/files/ — upload a new file.

        GET Steps
        ---------
        1. ``evidence = self._get_evidence(pk)``.
        2. ``files_qs = EvidenceFileService.get_files_for_evidence(evidence)``.
        3. Serialize with ``EvidenceFileReadSerializer(files_qs, many=True)``.
        4. Return HTTP 200.

        POST Steps
        ----------
        1. ``evidence = self._get_evidence(pk)``.
        2. Validate ``request.data`` with ``EvidenceFileUploadSerializer``.
        3. Delegate to ``EvidenceFileService.upload_file(
               evidence, serializer.validated_data, request.user
           )``.
        4. Serialize result with ``EvidenceFileReadSerializer``.
        5. Return HTTP 201.

        Example POST Request (multipart/form-data)
        -------------------------------------------
        ::

            POST /api/evidence/7/files/
            Content-Type: multipart/form-data

            file: <binary>
            file_type: "image"
            caption: "Close-up of blood sample"
        """
        raise NotImplementedError

    # ── Audit / history @actions ──────────────────────────────────────

    @action(detail=True, methods=["get"], url_path="chain-of-custody")
    def chain_of_custody(self, request: Request, pk: int = None) -> Response:
        """
        GET /api/evidence/{id}/chain-of-custody/

        Return the read-only chain-of-custody audit trail for this
        evidence item.  Shows a chronological history of who handled,
        modified, or verified the evidence.

        Steps
        -----
        1. ``evidence = self._get_evidence(pk)``.
        2. ``trail = ChainOfCustodyService.get_custody_trail(evidence)``.
        3. Serialize with ``ChainOfCustodyEntrySerializer(trail, many=True)``.
        4. Return HTTP 200.

        Example Response
        ----------------
        ::

            [
                {
                    "timestamp": "2026-02-20T10:30:00Z",
                    "action": "Registered",
                    "performed_by": 12,
                    "performer_name": "Jane Doe",
                    "details": "Evidence registered as Biological / Medical"
                },
                {
                    "timestamp": "2026-02-20T11:00:00Z",
                    "action": "File Added",
                    "performed_by": 12,
                    "performer_name": "Jane Doe",
                    "details": "Image: Close-up of blood sample"
                },
                {
                    "timestamp": "2026-02-21T09:15:00Z",
                    "action": "Verified by Coroner",
                    "performed_by": 8,
                    "performer_name": "Dr. Malcolm Stone",
                    "details": "Approved — Blood type O+, matches suspect DNA."
                }
            ]
        """
        raise NotImplementedError
