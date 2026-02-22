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
    EvidenceCustodyLog,
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
        help_text="Filter by evidence type: testimony, biological, vehicle, identity, other.",
    )
    case = serializers.IntegerField(required=False, min_value=1, help_text="Filter by associated case PK.")
    registered_by = serializers.IntegerField(required=False, min_value=1, help_text="Filter by registrar user PK.")
    is_verified = serializers.BooleanField(required=False, help_text="Filter biological evidence by verification status. Only valid with evidence_type='biological'.")
    search = serializers.CharField(
        required=False,
        max_length=255,
        allow_blank=False,
        help_text="Free-text search against evidence title and description.",
    )
    created_after = serializers.DateField(required=False, help_text="ISO 8601 date. Return evidence created on or after this date.")
    created_before = serializers.DateField(required=False, help_text="ISO 8601 date. Return evidence created on or before this date.")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Ensure ``created_after <= created_before`` when both are provided.
        """
        created_after = attrs.get("created_after")
        created_before = attrs.get("created_before")
        if created_after and created_before and created_after > created_before:
            raise serializers.ValidationError(
                "created_after must be earlier than created_before."
            )

        is_verified = attrs.get("is_verified")
        evidence_type = attrs.get("evidence_type")
        if is_verified is not None and evidence_type and evidence_type != "biological":
            raise serializers.ValidationError(
                "is_verified filter can only be used with evidence_type 'biological'."
            )

        return attrs


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
        """Return the registrar's full name."""
        if obj.registered_by:
            return obj.registered_by.get_full_name()
        return None


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
        if obj.registered_by:
            return obj.registered_by.get_full_name()
        return None


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
        if obj.registered_by:
            return obj.registered_by.get_full_name()
        return None

    def get_verified_by_name(self, obj: BiologicalEvidence) -> str | None:
        """Return the Coroner's full name who verified this evidence, or ``None``."""
        if obj.verified_by:
            return obj.verified_by.get_full_name()
        return None


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
        if obj.registered_by:
            return obj.registered_by.get_full_name()
        return None


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
        if obj.registered_by:
            return obj.registered_by.get_full_name()
        return None


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
        if obj.registered_by:
            return obj.registered_by.get_full_name()
        return None


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
        """
        plate = attrs.get("license_plate", "").strip()
        serial = attrs.get("serial_number", "").strip()
        has_plate = bool(plate)
        has_serial = bool(serial)
        if has_plate and has_serial:
            raise serializers.ValidationError(
                "Provide either a license plate or a serial number, not both."
            )
        if not has_plate and not has_serial:
            raise serializers.ValidationError(
                "Either a license plate or a serial number must be provided."
            )
        attrs["license_plate"] = plate
        attrs["serial_number"] = serial
        return attrs


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
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("document_details must be a JSON object.")
        for k, v in value.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise serializers.ValidationError(
                    "All keys and values in document_details must be strings."
                )
        return value


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

    evidence_type = serializers.ChoiceField(choices=EvidenceType.choices, help_text="Discriminator field. Determines which type-specific fields are expected: testimony, biological, vehicle, identity, other.")

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
        """Return the serializer class matching the given ``evidence_type``."""
        return cls._SERIALIZER_MAP[evidence_type]


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
        """
        if self.instance is None:
            return attrs
        plate = attrs.get("license_plate", self.instance.license_plate).strip()
        serial = attrs.get("serial_number", self.instance.serial_number).strip()
        has_plate = bool(plate)
        has_serial = bool(serial)
        if has_plate and has_serial:
            raise serializers.ValidationError(
                "Provide either a license plate or a serial number, not both."
            )
        if not has_plate and not has_serial:
            raise serializers.ValidationError(
                "Either a license plate or a serial number must be provided."
            )
        if "license_plate" in attrs:
            attrs["license_plate"] = plate
        if "serial_number" in attrs:
            attrs["serial_number"] = serial
        return attrs


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
        if not isinstance(value, dict):
            raise serializers.ValidationError("document_details must be a JSON object.")
        for k, v in value.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise serializers.ValidationError(
                    "All keys and values in document_details must be strings."
                )
        return value


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
        """Cross-field validation for verification decisions."""
        decision = attrs["decision"]
        if decision == "approve" and not attrs.get("forensic_result", "").strip():
            raise serializers.ValidationError(
                {"forensic_result": "Forensic result is required when approving."}
            )
        if decision == "reject" and not attrs.get("notes", "").strip():
            raise serializers.ValidationError(
                {"notes": "A rejection reason is required."}
            )
        return attrs


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
        """Ensure ``file_type`` is a valid ``FileType`` choice."""
        if value not in FileType.values:
            raise serializers.ValidationError(
                f"Invalid file type '{value}'. Must be one of: {', '.join(FileType.values)}."
            )
        return value


class ChainOfCustodyEntrySerializer(serializers.ModelSerializer):
    """
    Read-only serializer for ``EvidenceCustodyLog`` entries.

    Maps model field names to a cleaner API representation:

    - ``action_type`` → ``action`` (display label)
    - ``handled_by``  → ``performed_by`` (PK) + ``performer_name``
    - ``notes``       → ``details``

    Fields
    ------
    ``id``             : int      — PK of the custody-log entry
    ``timestamp``      : datetime — when the action occurred
    ``action``         : str      — human-readable action description
    ``performed_by``   : int      — PK of the user who performed the action
    ``performer_name`` : str      — full name of that user
    ``details``        : str      — optional additional detail / notes
    """

    action = serializers.CharField(
        source="get_action_type_display",
        read_only=True,
    )
    performed_by = serializers.IntegerField(
        source="handled_by_id",
        read_only=True,
    )
    performer_name = serializers.SerializerMethodField()
    details = serializers.CharField(
        source="notes",
        read_only=True,
    )

    class Meta:
        model = EvidenceCustodyLog
        fields = [
            "id",
            "timestamp",
            "action",
            "performed_by",
            "performer_name",
            "details",
        ]
        read_only_fields = fields

    def get_performer_name(self, obj: EvidenceCustodyLog) -> str | None:
        """Return the full name of the user who performed the action."""
        if obj.handled_by:
            return obj.handled_by.get_full_name()
        return None
