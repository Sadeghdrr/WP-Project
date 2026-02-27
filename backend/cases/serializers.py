"""
Cases app serializers.

Contains all Request and Response serializers for the Cases API.
Serializers handle field definitions, read/write constraints, and field-level
validation only.  **No business logic, workflow transitions, or formula
calculations live here** — those belong in ``services.py``.

Structure
---------
1. Filter / query-param serializers
2. Case read serializers (list, detail, full)
3. Case write serializers (complaint create, crime-scene create, update)
4. Workflow action serializers (review, transition, assignment)
5. Sub-resource serializers (complainant, witness, status log, calculations)
"""

from __future__ import annotations

import re
from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    Case,
    CaseComplainant,
    CaseCreationType,
    CaseStatus,
    CaseStatusLog,
    CaseWitness,
    CrimeLevel,
)

User = get_user_model()

# ── Phone number validation regex ───────────────────────────────────
_PHONE_REGEX = re.compile(r"^\+?\d{7,15}$")


# ═══════════════════════════════════════════════════════════════════
#  1. Filter / Query-Parameter Serializers
# ═══════════════════════════════════════════════════════════════════


class CaseFilterSerializer(serializers.Serializer):
    """
    Validates and cleans query-parameter filters for ``GET /api/cases/``.

    All fields are optional.  The view passes the validated dict directly
    to ``CaseQueryService.get_filtered_queryset``.

    Query Parameters
    ----------------
    ``status``          : str     — one of ``CaseStatus`` values
    ``crime_level``     : int     — one of ``CrimeLevel`` values (1–4)
    ``detective``       : int     — PK of assigned detective
    ``creation_type``   : str     — ``"complaint"`` or ``"crime_scene"``
    ``created_after``   : date    — ISO 8601 date string
    ``created_before``  : date    — ISO 8601 date string
    ``search``          : str     — free-text search against title/description
    """

    status = serializers.ChoiceField(
        choices=CaseStatus.choices,
        required=False,
        help_text="Filter by case status. Options: " + ", ".join([c[0] for c in CaseStatus.choices]) + ".",
    )
    crime_level = serializers.ChoiceField(
        choices=CrimeLevel.choices,
        required=False,
        help_text="Filter by crime level. 1=Level 3 (minor), 2=Level 2, 3=Level 1, 4=Critical.",
    )
    detective = serializers.IntegerField(required=False, min_value=1, help_text="PK of the assigned detective to filter by.")
    creation_type = serializers.ChoiceField(
        choices=CaseCreationType.choices,
        required=False,
        help_text="Filter by creation type: 'complaint' or 'crime_scene'.",
    )
    created_after = serializers.DateField(required=False, help_text="ISO 8601 date. Return cases created on or after this date.")
    created_before = serializers.DateField(required=False, help_text="ISO 8601 date. Return cases created on or before this date.")
    search = serializers.CharField(
        required=False,
        max_length=255,
        allow_blank=False,
        help_text="Free-text search against case title and description.",
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Ensure ``created_after <= created_before`` when both are provided.
        """
        after = attrs.get("created_after")
        before = attrs.get("created_before")
        if after and before and after > before:
            raise serializers.ValidationError(
                "created_after must be earlier than created_before."
            )
        return attrs


# ═══════════════════════════════════════════════════════════════════
#  2. Case Read Serializers
# ═══════════════════════════════════════════════════════════════════


class CaseListSerializer(serializers.ModelSerializer):
    """
    Compact representation for the list endpoint.

    Excludes heavy nested data (complainants, witnesses, status log)
    to keep list-page payloads small.  Includes summary counts as
    annotated read-only fields.
    """

    complainant_count = serializers.IntegerField(read_only=True)
    crime_level_display = serializers.CharField(
        source="get_crime_level_display",
        read_only=True,
    )
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    assigned_detective_name = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = [
            "id",
            "title",
            "crime_level",
            "crime_level_display",
            "status",
            "status_display",
            "creation_type",
            "incident_date",
            "location",
            "assigned_detective",
            "assigned_detective_name",
            "complainant_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_assigned_detective_name(self, obj: Case) -> str | None:
        """Return the detective's full name or ``None`` if unassigned."""
        if obj.assigned_detective is None:
            return None
        return (
            f"{obj.assigned_detective.first_name} "
            f"{obj.assigned_detective.last_name}"
        ).strip()


class CaseStatusLogSerializer(serializers.ModelSerializer):
    """Read-only serializer for the case audit trail."""

    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CaseStatusLog
        fields = [
            "id",
            "from_status",
            "to_status",
            "changed_by",
            "changed_by_name",
            "message",
            "created_at",
        ]
        read_only_fields = fields

    def get_changed_by_name(self, obj: CaseStatusLog) -> str | None:
        """Return full name of the actor or None."""
        if obj.changed_by is None:
            return None
        return (
            f"{obj.changed_by.first_name} {obj.changed_by.last_name}"
        ).strip()


class CaseComplainantSerializer(serializers.ModelSerializer):
    """Read representation of a ``CaseComplainant`` junction record."""

    user_display = serializers.SerializerMethodField()

    class Meta:
        model = CaseComplainant
        fields = [
            "id",
            "user",
            "user_display",
            "is_primary",
            "status",
            "reviewed_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_user_display(self, obj: CaseComplainant) -> str:
        """Return user's full name."""
        return (
            f"{obj.user.first_name} {obj.user.last_name}"
        ).strip()


class CaseWitnessSerializer(serializers.ModelSerializer):
    """Read representation of a ``CaseWitness`` record."""

    class Meta:
        model = CaseWitness
        fields = [
            "id",
            "full_name",
            "phone_number",
            "national_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CaseCalculationsSerializer(serializers.Serializer):
    """
    Read-only serializer wrapping the two core formula outputs.

    Populated entirely from ``CaseCalculationService.get_calculations_dict``.
    Used in ``CaseDetailSerializer`` (as a nested SerializerMethodField) and
    as the standalone response for ``GET /api/cases/{id}/calculations/``.

    Fields
    ------
    ``crime_level_degree``  : int — the ``L_j`` input (1–4)
    ``days_since_creation`` : int — the ``D_i`` proxy input
    ``tracking_threshold``  : int — ``L_j × D_i``
    ``reward_rials``        : int — ``L_j × D_i × 20,000,000``
    """

    crime_level_degree = serializers.IntegerField(read_only=True)
    days_since_creation = serializers.IntegerField(read_only=True)
    tracking_threshold = serializers.IntegerField(read_only=True)
    reward_rials = serializers.IntegerField(read_only=True)


class CaseDetailSerializer(serializers.ModelSerializer):
    """
    **Full case detail serializer.**

    Aggregates all nested sub-resources plus computed formula fields
    into a single response payload.  Used for ``GET /api/cases/{id}/``
    and the general reporting endpoint.

    The view's service call MUST pre-fetch the following before passing
    the case instance here to avoid N+1 queries:
    - ``complainants`` with ``select_related("user", "reviewed_by")``
    - ``witnesses``
    - ``status_logs`` with ``select_related("changed_by")``

    Formula fields are populated via ``SerializerMethodField`` so they
    are computed at serialisation time with zero extra DB queries
    (all data is already on the model instance).
    """

    complainants = CaseComplainantSerializer(many=True, read_only=True)
    witnesses = CaseWitnessSerializer(many=True, read_only=True)
    status_logs = CaseStatusLogSerializer(many=True, read_only=True)
    calculations = serializers.SerializerMethodField()
    crime_level_display = serializers.CharField(
        source="get_crime_level_display",
        read_only=True,
    )
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = Case
        fields = [
            "id",
            "title",
            "description",
            "crime_level",
            "crime_level_display",
            "status",
            "status_display",
            "creation_type",
            "rejection_count",
            "incident_date",
            "location",
            "created_by",
            "approved_by",
            "assigned_detective",
            "assigned_sergeant",
            "assigned_captain",
            "assigned_judge",
            "complainants",
            "witnesses",
            "status_logs",
            "calculations",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "approved_by", "rejection_count",
                            "created_at", "updated_at"]

    def get_calculations(self, obj: Case) -> dict:
        """
        Invoke ``CaseCalculationService.get_calculations_dict`` and return
        a serialised dict of the two formula outputs.
        """
        from .services import CaseCalculationService

        data = CaseCalculationService.get_calculations_dict(obj)
        return CaseCalculationsSerializer(data).data


# ═══════════════════════════════════════════════════════════════════
#  3. Case Write Serializers
# ═══════════════════════════════════════════════════════════════════


class CaseWitnessCreateSerializer(serializers.ModelSerializer):
    """
    Validates input for adding a witness to a crime-scene case.
    ``case`` is injected by the service; not accepted from the client.
    """

    class Meta:
        model = CaseWitness
        fields = ["full_name", "phone_number", "national_id"]
        extra_kwargs = {
            "full_name": {"required": True},
            "phone_number": {"required": True},
            "national_id": {"required": True},
        }

    def validate_national_id(self, value: str) -> str:
        """
        Validate that ``national_id`` is exactly 10 digits.

        Implementation Contract
        -----------------------
        If not ``value.isdigit()`` or len != 10:
        raise ``ValidationError("National ID must be exactly 10 digits.")``.
        """
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError(
                "National ID must be exactly 10 digits."
            )
        return value

    def validate_phone_number(self, value: str) -> str:
        """
        Validate that ``phone_number`` matches a valid phone format
        (7–15 digits, optionally prefixed with '+').
        """
        if not _PHONE_REGEX.match(value):
            raise serializers.ValidationError(
                "Phone number must be 7-15 digits, optionally prefixed with '+'."
            )
        return value


class ComplaintCaseCreateSerializer(serializers.ModelSerializer):
    """
    Validates input for creating a case via the **complaint** path.

    Fields accepted: ``title``, ``description``, ``crime_level``,
    ``incident_date`` (optional), ``location`` (optional).

    ``creation_type``, ``status``, and ``created_by`` are set by the
    service layer and must NOT be accepted from the client.
    """

    class Meta:
        model = Case
        fields = [
            "title",
            "description",
            "crime_level",
            "incident_date",
            "location",
        ]
        extra_kwargs = {
            "title": {"required": True},
            "description": {"required": True},
            "crime_level": {"required": True},
        }

    def validate_crime_level(self, value: int) -> int:
        """
        Ensure ``crime_level`` is a valid ``CrimeLevel`` choice.

        Implementation Contract
        -----------------------
        Check ``value in CrimeLevel.values``; raise ``ValidationError`` if not.
        """
        if value not in CrimeLevel.values:
            raise serializers.ValidationError(
                f"Invalid crime level. Choose from {list(CrimeLevel.values)}."
            )
        return value


class CrimeSceneCaseCreateSerializer(serializers.ModelSerializer):
    """
    Validates input for creating a case via the **crime-scene** path.

    Adds ``witnesses`` as a write-only nested list field on top of the
    complaint fields.  Both ``incident_date`` and ``location`` are
    required (unlike the complaint path where they are optional).
    """

    witnesses = CaseWitnessCreateSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = Case
        fields = [
            "title",
            "description",
            "crime_level",
            "incident_date",
            "location",
            "witnesses",
        ]
        extra_kwargs = {
            "title": {"required": True},
            "description": {"required": True},
            "crime_level": {"required": True},
            "incident_date": {"required": True},
            "location": {"required": True},
        }


class CaseUpdateSerializer(serializers.ModelSerializer):
    """
    Validates partial updates to mutable case fields.

    Only the fields explicitly listed here may be changed via PATCH.
    ``status``, ``crime_level``, ``creation_type``, and all assigned-user
    fields are immutable through this serializer — they are changed only
    via dedicated workflow/assignment endpoints.
    """

    class Meta:
        model = Case
        fields = [
            "title",
            "description",
            "incident_date",
            "location",
        ]


# ═══════════════════════════════════════════════════════════════════
#  4. Workflow Action Serializers
# ═══════════════════════════════════════════════════════════════════


class CaseTransitionSerializer(serializers.Serializer):
    """
    Generic request body for ``POST /api/cases/{id}/transition/``.

    The ``target_status`` must be a valid ``CaseStatus`` choice.
    ``message`` is optional but certain transitions (rejections) require it;
    that check is enforced in ``CaseWorkflowService.transition_state``.
    """

    target_status = serializers.ChoiceField(choices=CaseStatus.choices, help_text="Target workflow status for the case.")
    message = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=2000,
        help_text="Required for rejection transitions. Explains the reason for rejecting.",
    )


class CadetReviewSerializer(serializers.Serializer):
    """
    Request body for ``POST /api/cases/{id}/cadet-review/``.

    ``decision`` must be ``"approve"`` or ``"reject"``.
    ``message`` is required when ``decision == "reject"``.
    """

    DECISION_CHOICES = [("approve", "Approve"), ("reject", "Reject")]

    decision = serializers.ChoiceField(choices=DECISION_CHOICES, help_text="'approve' to forward the case, 'reject' to return it to the complainant.")
    message = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=2000,
        help_text="Rejection reason sent back to the complainant. Required when decision is 'reject'.",
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Require ``message`` when ``decision == "reject"``.

        Implementation Contract
        -----------------------
        If ``attrs["decision"] == "reject"`` and not ``attrs.get("message")``:
        raise ``ValidationError({"message": "A rejection reason is required."})``.
        """
        if attrs["decision"] == "reject" and not attrs.get("message"):
            raise serializers.ValidationError(
                {"message": "A rejection reason is required."}
            )
        return attrs


class OfficerReviewSerializer(serializers.Serializer):
    """
    Request body for ``POST /api/cases/{id}/officer-review/``.

    Identical shape to ``CadetReviewSerializer``; kept separate so
    Swagger documentation generates distinct schemas.
    """

    DECISION_CHOICES = [("approve", "Approve"), ("reject", "Reject")]

    decision = serializers.ChoiceField(choices=DECISION_CHOICES, help_text="'approve' to open the case, 'reject' to send it back to the Cadet.")
    message = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=2000,
        help_text="Rejection reason sent back to the Cadet. Required when decision is 'reject'.",
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Require ``message`` when ``decision == "reject"``.
        Same contract as ``CadetReviewSerializer.validate``.
        """
        if attrs["decision"] == "reject" and not attrs.get("message"):
            raise serializers.ValidationError(
                {"message": "A rejection reason is required."}
            )
        return attrs


class AssignPersonnelSerializer(serializers.Serializer):
    """
    Generic request body for personnel assignment endpoints.

    ``user_id`` is the PK of the user to assign.  The specific role
    constraint (must be Detective / Sergeant / etc.) is validated in the
    relevant service method.
    """

    user_id = serializers.IntegerField(min_value=1, help_text="PK of the user to assign to this case role (must have the appropriate rank).")


# ═══════════════════════════════════════════════════════════════════
#  5. Sub-Resource Write Serializers
# ═══════════════════════════════════════════════════════════════════


class AddComplainantSerializer(serializers.Serializer):
    """
    Request body for ``POST /api/cases/{id}/complainants/``.
    ``user_id`` is the PK of the user to add as an additional complainant.
    """

    user_id = serializers.IntegerField(min_value=1, help_text="PK of the user to register as an additional complainant on this case.")


class ComplainantReviewSerializer(serializers.Serializer):
    """
    Request body for the Cadet to approve/reject an individual complainant's
    information.  Used on ``POST /api/cases/{id}/complainants/{c_id}/review/``.
    """

    DECISION_CHOICES = [("approve", "Approve"), ("reject", "Reject")]
    decision = serializers.ChoiceField(choices=DECISION_CHOICES)


class ResubmitComplaintSerializer(serializers.Serializer):
    """
    Request body for ``POST /api/cases/{id}/resubmit/``.

    Complainant edits allowed fields before re-submitting to Cadet review.
    All fields are optional (partial update semantics).
    """

    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False)
    incident_date = serializers.DateTimeField(required=False)
    location = serializers.CharField(max_length=500, required=False)


# ═══════════════════════════════════════════════════════════════════
#  6. Case Report Serializers (Judiciary Flow)
# ═══════════════════════════════════════════════════════════════════


class _UserSummarySerializer(serializers.Serializer):
    """Compact user representation used across report sub-sections."""

    id = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True, allow_null=True)


class _ReportCaseSerializer(serializers.Serializer):
    """Top-level case fields within the report."""

    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    crime_level = serializers.IntegerField(read_only=True)
    crime_level_display = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    status_display = serializers.CharField(read_only=True)
    creation_type = serializers.CharField(read_only=True)
    rejection_count = serializers.IntegerField(read_only=True)
    incident_date = serializers.CharField(read_only=True, allow_null=True)
    location = serializers.CharField(read_only=True, allow_null=True)
    created_at = serializers.CharField(read_only=True, allow_null=True)
    updated_at = serializers.CharField(read_only=True, allow_null=True)


class _ReportPersonnelSerializer(serializers.Serializer):
    """Personnel assignments block."""

    created_by = _UserSummarySerializer(allow_null=True, read_only=True)
    approved_by = _UserSummarySerializer(allow_null=True, read_only=True)
    assigned_detective = _UserSummarySerializer(allow_null=True, read_only=True)
    assigned_sergeant = _UserSummarySerializer(allow_null=True, read_only=True)
    assigned_captain = _UserSummarySerializer(allow_null=True, read_only=True)
    assigned_judge = _UserSummarySerializer(allow_null=True, read_only=True)


class _ReportComplainantSerializer(serializers.Serializer):
    """Single complainant within the report."""

    id = serializers.IntegerField(read_only=True)
    user = _UserSummarySerializer(allow_null=True, read_only=True)
    is_primary = serializers.BooleanField(read_only=True)
    status = serializers.CharField(read_only=True)
    reviewed_by = _UserSummarySerializer(allow_null=True, read_only=True)


class _ReportWitnessSerializer(serializers.Serializer):
    """Single witness within the report."""

    id = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    phone_number = serializers.CharField(read_only=True, allow_null=True)
    national_id = serializers.CharField(read_only=True, allow_null=True)


class _ReportEvidenceSerializer(serializers.Serializer):
    """Evidence metadata entry within the report."""

    id = serializers.IntegerField(read_only=True)
    evidence_type = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True, allow_null=True)
    registered_by = _UserSummarySerializer(allow_null=True, read_only=True)
    created_at = serializers.CharField(read_only=True, allow_null=True)


class _ReportInterrogationSerializer(serializers.Serializer):
    """Interrogation summary nested under a suspect."""

    id = serializers.IntegerField(read_only=True)
    detective = _UserSummarySerializer(allow_null=True, read_only=True)
    sergeant = _UserSummarySerializer(allow_null=True, read_only=True)
    detective_guilt_score = serializers.IntegerField(read_only=True, allow_null=True)
    sergeant_guilt_score = serializers.IntegerField(read_only=True, allow_null=True)
    notes = serializers.CharField(read_only=True, allow_null=True)
    created_at = serializers.CharField(read_only=True, allow_null=True)


class _ReportTrialSerializer(serializers.Serializer):
    """Trial summary nested under a suspect."""

    id = serializers.IntegerField(read_only=True)
    judge = _UserSummarySerializer(allow_null=True, read_only=True)
    verdict = serializers.CharField(read_only=True)
    punishment_title = serializers.CharField(read_only=True, allow_null=True)
    punishment_description = serializers.CharField(read_only=True, allow_null=True)
    created_at = serializers.CharField(read_only=True, allow_null=True)


class _ReportSuspectSerializer(serializers.Serializer):
    """Full suspect block with interrogation & trial sub-lists."""

    id = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    national_id = serializers.CharField(read_only=True, allow_null=True)
    status = serializers.CharField(read_only=True)
    status_display = serializers.CharField(read_only=True)
    wanted_since = serializers.CharField(read_only=True, allow_null=True)
    days_wanted = serializers.IntegerField(read_only=True, allow_null=True)
    identified_by = _UserSummarySerializer(allow_null=True, read_only=True)
    sergeant_approval_status = serializers.CharField(read_only=True, allow_null=True)
    approved_by_sergeant = _UserSummarySerializer(allow_null=True, read_only=True)
    sergeant_rejection_message = serializers.CharField(read_only=True, allow_null=True)
    interrogations = _ReportInterrogationSerializer(many=True, read_only=True)
    trials = _ReportTrialSerializer(many=True, read_only=True)


class _ReportStatusLogSerializer(serializers.Serializer):
    """Single status-history entry."""

    id = serializers.IntegerField(read_only=True)
    from_status = serializers.CharField(read_only=True, allow_null=True)
    to_status = serializers.CharField(read_only=True)
    changed_by = _UserSummarySerializer(allow_null=True, read_only=True)
    message = serializers.CharField(read_only=True, allow_null=True)
    created_at = serializers.CharField(read_only=True, allow_null=True)


class _ReportCalculationsSerializer(serializers.Serializer):
    """Computed values for the case."""

    crime_level_degree = serializers.IntegerField(read_only=True)
    days_since_creation = serializers.IntegerField(read_only=True)
    tracking_threshold = serializers.IntegerField(read_only=True)
    reward_rials = serializers.IntegerField(read_only=True)


class CaseReportSerializer(serializers.Serializer):
    """
    Read-only serializer for the aggregated case report returned by
    ``CaseReportingService.get_case_report()``.

    This mirrors the exact dictionary structure produced by the service
    and provides schema documentation for drf-spectacular / Swagger.
    """

    case = _ReportCaseSerializer(read_only=True)
    personnel = _ReportPersonnelSerializer(read_only=True)
    complainants = _ReportComplainantSerializer(many=True, read_only=True)
    witnesses = _ReportWitnessSerializer(many=True, read_only=True)
    evidence = _ReportEvidenceSerializer(many=True, read_only=True)
    suspects = _ReportSuspectSerializer(many=True, read_only=True)
    status_history = _ReportStatusLogSerializer(many=True, read_only=True)
    calculations = _ReportCalculationsSerializer(read_only=True)
