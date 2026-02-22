"""
Evidence app serializers.

Contains all Request and Response serializers for the Evidence API.
Serializers handle field definitions, read/write constraints, and field-level
/ object-level validation only.  **No business logic, workflow transitions,
or permission checks live here** — those belong in ``services.py``.

Structure
---------
1. Filter / query-param serializers
2. Evidence read serializers (list, detail, polymorphic children)
3. Evidence write serializers (polymorphic create, update)
4. Workflow action serializers (verify biological, link/unlink case)
5. Sub-resource serializers (EvidenceFile, chain-of-custody)
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    BiologicalEvidence,
    Evidence,
    EvidenceFile,
    EvidenceType,
    FileType,
    IdentityEvidence,
    TestimonyEvidence,
    VehicleEvidence,
)

User = get_user_model()


# ═══════════════════════════════════════════════════════════════════
#  1. Filter / Query-Parameter Serializers
# ═══════════════════════════════════════════════════════════════════


class EvidenceFilterSerializer(serializers.Serializer):
    """
    Validates and cleans query-parameter filters for ``GET /api/evidence/``.

    All fields are optional.  The view passes the validated dict directly
    to ``EvidenceQueryService.get_filtered_queryset``.

    Query Parameters
    ----------------
    ``evidence_type``   : str     — one of ``EvidenceType`` values
    ``case``            : int     — PK of the associated case
    ``registered_by``   : int     — PK of the registrar user
    ``is_verified``     : bool    — filter biological evidence by verification status
    ``search``          : str     — free-text search against title/description
    ``created_after``   : date    — ISO 8601 date string
    ``created_before``  : date    — ISO 8601 date string
    """

    evidence_type = serializers.ChoiceField(
        choices=EvidenceType.choices,
        required=False,
    )
    case = serializers.IntegerField(required=False, min_value=1)
    registered_by = serializers.IntegerField(required=False, min_value=1)
    is_verified = serializers.BooleanField(required=False)
    search = serializers.CharField(
        required=False,
        max_length=255,
        allow_blank=False,
    )
    created_after = serializers.DateField(required=False)
    created_before = serializers.DateField(required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Ensure ``created_after <= created_before`` when both are provided.

        Implementation Contract
        -----------------------
        If both present and ``created_after > created_before``, raise
        ``ValidationError("created_after must be earlier than created_before.")``.

        Also validate that ``is_verified`` is only used together with
        ``evidence_type == "biological"`` or when no ``evidence_type`` is
        specified (in the latter case, the queryset is automatically
        scoped to biological evidence).
        """
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════
#  2. Evidence Read Serializers
# ═══════════════════════════════════════════════════════════════════


class EvidenceFileReadSerializer(serializers.ModelSerializer):
    """
    Read-only representation of an ``EvidenceFile`` attachment.

    Used as a nested serializer inside evidence detail responses.
    """

    file_type_display = serializers.CharField(
        source="get_file_type_display",
        read_only=True,
    )

    class Meta:
        model = EvidenceFile
        fields = [
            "id",
            "file",
            "file_type",
            "file_type_display",
            "caption",
            "created_at",
        ]
        read_only_fields = fields


class EvidenceListSerializer(serializers.ModelSerializer):
    """
    Compact representation for the list endpoint.

    Excludes heavy nested data (files, type-specific fields) to keep
    list-page payloads small.  Includes display labels and registrar info.
    """

    evidence_type_display = serializers.CharField(
        source="get_evidence_type_display",
        read_only=True,
    )
    registered_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Evidence
        fields = [
            "id",
            "title",
            "description",
            "evidence_type",
            "evidence_type_display",
            "case",
            "registered_by",
            "registered_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_registered_by_name(self, obj: Evidence) -> str | None:
        """
        Return the registrar's full name.

        Implementation Contract
        -----------------------
        Return ``obj.registered_by.get_full_name()`` or ``None`` if the
        FK is somehow unset (should never happen given PROTECT).
        """
        raise NotImplementedError


# ── Type-specific read serializers ──────────────────────────────────


class TestimonyEvidenceDetailSerializer(serializers.ModelSerializer):
    """
    Full detail serializer for testimony evidence.

    Includes the ``statement_text`` field specific to this type plus
    all common fields and nested files.
    """

    evidence_type_display = serializers.CharField(
        source="get_evidence_type_display",
        read_only=True,
    )
    registered_by_name = serializers.SerializerMethodField()
    files = EvidenceFileReadSerializer(many=True, read_only=True)

    class Meta:
        model = TestimonyEvidence
        fields = [
            "id",
            "title",
            "description",
            "evidence_type",
            "evidence_type_display",
            "case",
            "registered_by",
            "registered_by_name",
            "statement_text",
            "files",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_registered_by_name(self, obj: TestimonyEvidence) -> str | None:
        """Return registrar's full name."""
        raise NotImplementedError


class BiologicalEvidenceDetailSerializer(serializers.ModelSerializer):
    """
    Full detail serializer for biological / medical evidence.

    Includes forensic examination fields, verification status, and
    the verifier (Coroner) identity.
    """

    evidence_type_display = serializers.CharField(
        source="get_evidence_type_display",
        read_only=True,
    )
    registered_by_name = serializers.SerializerMethodField()
    verified_by_name = serializers.SerializerMethodField()
    files = EvidenceFileReadSerializer(many=True, read_only=True)

    class Meta:
        model = BiologicalEvidence
        fields = [
            "id",
            "title",
            "description",
            "evidence_type",
            "evidence_type_display",
            "case",
            "registered_by",
            "registered_by_name",
            "forensic_result",
            "is_verified",
            "verified_by",
            "verified_by_name",
            "files",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_registered_by_name(self, obj: BiologicalEvidence) -> str | None:
        """Return registrar's full name."""
        raise NotImplementedError

    def get_verified_by_name(self, obj: BiologicalEvidence) -> str | None:
        """
        Return the Coroner's full name who verified this evidence, or ``None``.

        Implementation Contract
        -----------------------
        If ``obj.verified_by`` is not None, return their full name.
        Otherwise return ``None``.
        """
        raise NotImplementedError


class VehicleEvidenceDetailSerializer(serializers.ModelSerializer):
    """
    Full detail serializer for vehicle evidence.

    Includes vehicle-specific fields: ``vehicle_model``, ``color``,
    ``license_plate``, ``serial_number``.
    """

    evidence_type_display = serializers.CharField(
        source="get_evidence_type_display",
        read_only=True,
    )
    registered_by_name = serializers.SerializerMethodField()
    files = EvidenceFileReadSerializer(many=True, read_only=True)

    class Meta:
        model = VehicleEvidence
        fields = [
            "id",
            "title",
            "description",
            "evidence_type",
            "evidence_type_display",
            "case",
            "registered_by",
            "registered_by_name",
            "vehicle_model",
            "color",
            "license_plate",
            "serial_number",
            "files",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_registered_by_name(self, obj: VehicleEvidence) -> str | None:
        """Return registrar's full name."""
        raise NotImplementedError


class IdentityEvidenceDetailSerializer(serializers.ModelSerializer):
    """
    Full detail serializer for identity-document evidence.

    Includes ``owner_full_name`` and the dynamic ``document_details``
    JSON key-value pairs.
    """

    evidence_type_display = serializers.CharField(
        source="get_evidence_type_display",
        read_only=True,
    )
    registered_by_name = serializers.SerializerMethodField()
    files = EvidenceFileReadSerializer(many=True, read_only=True)

    class Meta:
        model = IdentityEvidence
        fields = [
            "id",
            "title",
            "description",
            "evidence_type",
            "evidence_type_display",
            "case",
            "registered_by",
            "registered_by_name",
            "owner_full_name",
            "document_details",
            "files",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_registered_by_name(self, obj: IdentityEvidence) -> str | None:
        """Return registrar's full name."""
        raise NotImplementedError


class OtherEvidenceDetailSerializer(serializers.ModelSerializer):
    """
    Full detail serializer for "Other Item" evidence.

    Uses the base ``Evidence`` model directly — no child-table fields.
    """

    evidence_type_display = serializers.CharField(
        source="get_evidence_type_display",
        read_only=True,
    )
    registered_by_name = serializers.SerializerMethodField()
    files = EvidenceFileReadSerializer(many=True, read_only=True)

    class Meta:
        model = Evidence
        fields = [
            "id",
            "title",
            "description",
            "evidence_type",
            "evidence_type_display",
            "case",
            "registered_by",
            "registered_by_name",
            "files",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_registered_by_name(self, obj: Evidence) -> str | None:
        """Return registrar's full name."""
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════
#  3. Evidence Write Serializers (Polymorphic Create / Update)
# ═══════════════════════════════════════════════════════════════════


class TestimonyEvidenceCreateSerializer(serializers.ModelSerializer):
    """
    Validates input for creating **Testimony** evidence.

    Accepts common fields plus ``statement_text``.
    ``registered_by`` and ``evidence_type`` are set by the service layer.
    """

    class Meta:
        model = TestimonyEvidence
        fields = [
            "case",
            "title",
            "description",
            "statement_text",
        ]
        extra_kwargs = {
            "case": {"required": True},
            "title": {"required": True},
        }


class BiologicalEvidenceCreateSerializer(serializers.ModelSerializer):
    """
    Validates input for creating **Biological / Medical** evidence.

    Only common fields are accepted on creation.  The ``forensic_result``,
    ``is_verified``, and ``verified_by`` fields are populated later
    through the Coroner verification workflow.
    """

    class Meta:
        model = BiologicalEvidence
        fields = [
            "case",
            "title",
            "description",
        ]
        extra_kwargs = {
            "case": {"required": True},
            "title": {"required": True},
        }


class VehicleEvidenceCreateSerializer(serializers.ModelSerializer):
    """
    Validates input for creating **Vehicle** evidence.

    Accepts vehicle-specific fields: ``vehicle_model``, ``color``,
    ``license_plate``, ``serial_number``.

    **CRITICAL: XOR Constraint Validation**
    ----------------------------------------
    The ``validate()`` method enforces the strict XOR rule from
    project-doc §4.3.3:

        A vehicle must have **either** a ``license_plate`` **or** a
        ``serial_number``, but **never both** simultaneously, and
        **never neither**.

    This validation mirrors the DB-level ``CheckConstraint``
    (``vehicle_plate_xor_serial``) defined on ``VehicleEvidence.Meta``,
    providing an early, user-friendly error *before* hitting the database.

    Frontend Payload Examples
    -------------------------
    **Valid — license plate only:**
    ::

        {
            "case": 42,
            "title": "Blue Sedan Near Alley",
            "vehicle_model": "Ford Sedan 1947",
            "color": "Blue",
            "license_plate": "LA-4521",
            "serial_number": ""        ← empty or omitted
        }

    **Valid — serial number only:**
    ::

        {
            "case": 42,
            "title": "Burnt Truck Frame",
            "vehicle_model": "Chevrolet Truck",
            "color": "Black (burnt)",
            "license_plate": "",       ← empty or omitted
            "serial_number": "CHV-19470812-0042"
        }

    **Invalid — both provided:**
    ::

        {
            "case": 42,
            "title": "...",
            "vehicle_model": "...",
            "color": "...",
            "license_plate": "LA-4521",
            "serial_number": "CHV-19470812-0042"
        }
        → 400:  {"non_field_errors": ["Provide either a license plate or a serial number, not both."]}

    **Invalid — neither provided:**
    ::

        {
            "case": 42,
            "title": "...",
            "vehicle_model": "...",
            "color": "...",
            "license_plate": "",
            "serial_number": ""
        }
        → 400:  {"non_field_errors": ["Either a license plate or a serial number must be provided."]}
    """

    class Meta:
        model = VehicleEvidence
        fields = [
            "case",
            "title",
            "description",
            "vehicle_model",
            "color",
            "license_plate",
            "serial_number",
        ]
        extra_kwargs = {
            "case": {"required": True},
            "title": {"required": True},
            "vehicle_model": {"required": True},
            "color": {"required": True},
            "license_plate": {"required": False, "allow_blank": True, "default": ""},
            "serial_number": {"required": False, "allow_blank": True, "default": ""},
        }

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Enforce the **XOR constraint** between ``license_plate`` and
        ``serial_number`` at the serializer level.

        This is the **API-boundary validation** — it runs before the
        service layer and before the DB constraint, providing clear,
        user-friendly error messages to the frontend.

        Implementation Contract
        -----------------------
        1. Extract ``plate = attrs.get("license_plate", "").strip()``.
        2. Extract ``serial = attrs.get("serial_number", "").strip()``.
        3. ``has_plate = bool(plate)``; ``has_serial = bool(serial)``.
        4. If ``has_plate and has_serial``:
           raise ``ValidationError(
               "Provide either a license plate or a serial number, not both."
           )``.
        5. If ``not has_plate and not has_serial``:
           raise ``ValidationError(
               "Either a license plate or a serial number must be provided."
           )``.
        6. Return ``attrs`` (with stripped values written back).

        Technical Notes
        ---------------
        - The DB ``CheckConstraint`` (``vehicle_plate_xor_serial``) is the
          last line of defence. This serializer check prevents hitting the
          DB at all on invalid input.
        - On update (PATCH), partial data may be sent.  The update
          serializer must merge existing instance values with incoming
          data before running this check.
        """
        raise NotImplementedError


class IdentityEvidenceCreateSerializer(serializers.ModelSerializer):
    """
    Validates input for creating **Identity Document** evidence.

    ``document_details`` is a JSON object with arbitrary key-value pairs.
    Zero pairs is valid (e.g. an ID card with only a name on it).
    """

    class Meta:
        model = IdentityEvidence
        fields = [
            "case",
            "title",
            "description",
            "owner_full_name",
            "document_details",
        ]
        extra_kwargs = {
            "case": {"required": True},
            "title": {"required": True},
            "owner_full_name": {"required": True},
            "document_details": {"required": False, "default": dict},
        }

    def validate_document_details(self, value: Any) -> dict:
        """
        Ensure ``document_details`` is a flat dict of string keys and
        string values (if provided).

        Implementation Contract
        -----------------------
        1. If not ``isinstance(value, dict)`` → raise ``ValidationError``.
        2. For each key, value pair: assert both are strings.
        3. Return value.
        """
        raise NotImplementedError


class OtherEvidenceCreateSerializer(serializers.ModelSerializer):
    """
    Validates input for creating **Other Item** evidence (§4.3.5).

    Uses the base ``Evidence`` model. Only ``title`` and ``description``
    beyond the common ``case`` field.
    """

    class Meta:
        model = Evidence
        fields = [
            "case",
            "title",
            "description",
        ]
        extra_kwargs = {
            "case": {"required": True},
            "title": {"required": True},
        }


class EvidencePolymorphicCreateSerializer(serializers.Serializer):
    """
    **Top-level dispatcher** for polymorphic evidence creation.

    The frontend sends a JSON payload with an ``evidence_type`` discriminator.
    This serializer selects the appropriate child serializer based on
    that discriminator and delegates validation to it.

    Usage (in the view's ``create`` action)
    ----------------------------------------
    ::

        serializer = EvidencePolymorphicCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evidence_type = serializer.validated_data["evidence_type"]
        child_serializer_class = serializer.get_child_serializer_class(evidence_type)
        child_serializer = child_serializer_class(data=request.data)
        child_serializer.is_valid(raise_exception=True)
        # pass child_serializer.validated_data to service layer

    Alternatively, the view may use ``get_child_serializer_class`` directly
    after extracting ``evidence_type`` from ``request.data``.
    """

    evidence_type = serializers.ChoiceField(choices=EvidenceType.choices)

    #: Maps each ``EvidenceType`` value to its dedicated create serializer.
    _SERIALIZER_MAP: dict[str, type[serializers.Serializer]] = {
        EvidenceType.TESTIMONY: TestimonyEvidenceCreateSerializer,
        EvidenceType.BIOLOGICAL: BiologicalEvidenceCreateSerializer,
        EvidenceType.VEHICLE: VehicleEvidenceCreateSerializer,
        EvidenceType.IDENTITY: IdentityEvidenceCreateSerializer,
        EvidenceType.OTHER: OtherEvidenceCreateSerializer,
    }

    @classmethod
    def get_child_serializer_class(
        cls,
        evidence_type: str,
    ) -> type[serializers.Serializer]:
        """
        Return the serializer class matching the given ``evidence_type``.

        Parameters
        ----------
        evidence_type : str
            Must be one of ``EvidenceType`` values.

        Returns
        -------
        type[serializers.Serializer]
            The matching create serializer class.

        Raises
        ------
        KeyError
            If ``evidence_type`` is not in ``_SERIALIZER_MAP``.
            Should never happen after ``is_valid()`` passes on this
            serializer.

        Implementation Contract
        -----------------------
        return cls._SERIALIZER_MAP[evidence_type]
        """
        raise NotImplementedError


# ── Update Serializers ──────────────────────────────────────────────


class EvidenceUpdateSerializer(serializers.ModelSerializer):
    """
    Validates partial updates to common evidence fields.

    Only mutable metadata fields are accepted.  ``evidence_type``,
    ``registered_by``, and ``case`` are immutable after creation.
    Type-specific fields are handled by dedicated update serializers.
    """

    class Meta:
        model = Evidence
        fields = [
            "title",
            "description",
        ]


class VehicleEvidenceUpdateSerializer(serializers.ModelSerializer):
    """
    Validates partial updates to vehicle-specific fields.

    Inherits the XOR constraint from the create serializer, but must
    account for partial payloads by merging incoming data with the
    existing instance values.

    Implementation Contract (validate)
    -----------------------------------
    1. ``plate = attrs.get("license_plate", self.instance.license_plate).strip()``
    2. ``serial = attrs.get("serial_number", self.instance.serial_number).strip()``
    3. Apply the same XOR check as ``VehicleEvidenceCreateSerializer.validate``.
    """

    class Meta:
        model = VehicleEvidence
        fields = [
            "title",
            "description",
            "vehicle_model",
            "color",
            "license_plate",
            "serial_number",
        ]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Enforce XOR constraint on partial updates by merging incoming values
        with existing instance data before checking.

        Implementation Contract
        -----------------------
        1. If self.instance is None, skip (should only run on update).
        2. Merge: ``plate = attrs.get("license_plate", self.instance.license_plate).strip()``
        3. Merge: ``serial = attrs.get("serial_number", self.instance.serial_number).strip()``
        4. Apply same XOR logic as VehicleEvidenceCreateSerializer.validate.
        5. Return ``attrs``.
        """
        raise NotImplementedError


class BiologicalEvidenceUpdateSerializer(serializers.ModelSerializer):
    """
    Validates partial updates to biological evidence metadata.

    ``forensic_result``, ``is_verified``, and ``verified_by`` are NOT
    editable through this serializer — they are set exclusively through
    the Coroner verification workflow (``POST /evidence/{id}/verify/``).
    """

    class Meta:
        model = BiologicalEvidence
        fields = [
            "title",
            "description",
        ]


class TestimonyEvidenceUpdateSerializer(serializers.ModelSerializer):
    """
    Validates partial updates to testimony-specific fields.
    """

    class Meta:
        model = TestimonyEvidence
        fields = [
            "title",
            "description",
            "statement_text",
        ]


class IdentityEvidenceUpdateSerializer(serializers.ModelSerializer):
    """
    Validates partial updates to identity-document evidence fields.
    """

    class Meta:
        model = IdentityEvidence
        fields = [
            "title",
            "description",
            "owner_full_name",
            "document_details",
        ]

    def validate_document_details(self, value: Any) -> dict:
        """
        Same flat-dict validation as ``IdentityEvidenceCreateSerializer``.
        """
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════
#  4. Workflow Action Serializers
# ═══════════════════════════════════════════════════════════════════


class VerifyBiologicalEvidenceSerializer(serializers.Serializer):
    """
    Request body for ``POST /api/evidence/{id}/verify/``.

    Used exclusively by the **Coroner** (Medical Examiner role) to
    approve or reject biological/medical evidence items.

    Fields
    ------
    ``decision`` : str
        ``"approve"`` or ``"reject"``.
    ``forensic_result`` : str
        The textual result of the forensic examination.
        Required when ``decision == "approve"``.
    ``notes`` : str
        Optional notes or rejection reason.  Required when
        ``decision == "reject"``.

    Payload Examples
    ----------------
    **Approve with report:**
    ::

        {
            "decision": "approve",
            "forensic_result": "Blood type O+, matches suspect DNA profile.",
            "notes": "Analysis conducted at LAPD forensics lab."
        }

    **Reject:**
    ::

        {
            "decision": "reject",
            "forensic_result": "",
            "notes": "Sample contaminated — request a new collection."
        }
    """

    DECISION_CHOICES = [("approve", "Approve"), ("reject", "Reject")]

    decision = serializers.ChoiceField(choices=DECISION_CHOICES)
    forensic_result = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=5000,
        help_text="Forensic examination result. Required on approval.",
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=2000,
        help_text="Additional notes or rejection reason.",
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Cross-field validation:

        - If ``decision == "approve"`` and ``forensic_result`` is blank,
          raise ``ValidationError``.
        - If ``decision == "reject"`` and ``notes`` is blank, raise
          ``ValidationError``.

        Implementation Contract
        -----------------------
        1. ``decision = attrs["decision"]``
        2. If ``decision == "approve"`` and not ``attrs.get("forensic_result", "").strip()``:
           raise ``ValidationError({"forensic_result": "Forensic result is required when approving."})``.
        3. If ``decision == "reject"`` and not ``attrs.get("notes", "").strip()``:
           raise ``ValidationError({"notes": "A rejection reason is required."})``.
        4. Return attrs.
        """
        raise NotImplementedError


class LinkCaseSerializer(serializers.Serializer):
    """
    Request body for ``POST /api/evidence/{id}/link-case/``.

    Links an existing evidence item to an additional case.
    """

    case_id = serializers.IntegerField(
        min_value=1,
        help_text="PK of the case to link this evidence to.",
    )


class UnlinkCaseSerializer(serializers.Serializer):
    """
    Request body for ``POST /api/evidence/{id}/unlink-case/``.

    Removes the association between an evidence item and a case.
    """

    case_id = serializers.IntegerField(
        min_value=1,
        help_text="PK of the case to unlink from this evidence.",
    )


# ═══════════════════════════════════════════════════════════════════
#  5. Sub-Resource Serializers (File Upload, Chain of Custody)
# ═══════════════════════════════════════════════════════════════════


class EvidenceFileUploadSerializer(serializers.ModelSerializer):
    """
    Validates file upload requests for ``POST /api/evidence/{id}/files/``.

    ``evidence`` is injected by the view/service — not accepted from the
    client payload.
    """

    class Meta:
        model = EvidenceFile
        fields = [
            "file",
            "file_type",
            "caption",
        ]
        extra_kwargs = {
            "file": {"required": True},
            "file_type": {"required": True},
            "caption": {"required": False, "default": ""},
        }

    def validate_file_type(self, value: str) -> str:
        """
        Ensure ``file_type`` is a valid ``FileType`` choice.

        Implementation Contract
        -----------------------
        Check ``value in FileType.values``; raise ``ValidationError``
        if not valid.
        """
        raise NotImplementedError


class ChainOfCustodyEntrySerializer(serializers.Serializer):
    """
    Read-only serializer for a single chain-of-custody audit entry.

    This is a virtual/computed serializer — it does not map to a
    dedicated model.  Entries are assembled from the evidence's
    ``updated_at`` history, file additions, and verification events.

    Fields
    ------
    ``timestamp``   : datetime — when the action occurred
    ``action``      : str      — human-readable action description
    ``performed_by``: int      — PK of the user who performed the action
    ``performer_name``: str    — full name of that user
    ``details``     : str      — optional additional detail
    """

    timestamp = serializers.DateTimeField(read_only=True)
    action = serializers.CharField(read_only=True)
    performed_by = serializers.IntegerField(read_only=True)
    performer_name = serializers.CharField(read_only=True)
    details = serializers.CharField(read_only=True, allow_blank=True)
