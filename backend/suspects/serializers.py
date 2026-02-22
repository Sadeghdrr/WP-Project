"""
Suspects app serializers.

Contains all Request and Response serializers for the Suspects API.
Serializers handle field definitions, read/write constraints, and field-level
/ object-level validation only.  **No business logic, workflow transitions,
or permission checks live here** — those belong in ``services.py``.

Structure
---------
1. Filter / query-param serializers
2. Suspect read serializers (list, detail)
3. Suspect write serializers (create, update)
4. Workflow action serializers (arrest, approve/reject suspect, warrant)
5. Interrogation serializers (CRUD)
6. Trial serializers (read, create)
7. BountyTip serializers (CRUD + workflow)
8. Bail serializers (CRUD)
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    Bail,
    BountyTip,
    BountyTipStatus,
    Interrogation,
    Suspect,
    SuspectStatus,
    Trial,
    VerdictChoice,
)

User = get_user_model()


# ═══════════════════════════════════════════════════════════════════
#  1. Filter / Query-Parameter Serializers
# ═══════════════════════════════════════════════════════════════════


class SuspectFilterSerializer(serializers.Serializer):
    """
    Validates and cleans query-parameter filters for ``GET /api/suspects/``.

    All fields are optional.  The view passes the validated dict directly
    to ``SuspectProfileService.get_filtered_queryset``.

    Query Parameters
    ----------------
    ``status``          : str     — one of ``SuspectStatus`` values
    ``case``            : int     — PK of the associated case
    ``national_id``     : str     — national ID exact match
    ``search``          : str     — free-text search against full_name/aliases/description
    ``most_wanted``     : bool    — filter to most-wanted suspects only (> 30 days)
    ``created_after``   : date    — ISO 8601 date string
    ``created_before``  : date    — ISO 8601 date string
    ``approval_status`` : str     — sergeant approval status (pending/approved/rejected)
    """

    status = serializers.ChoiceField(
        choices=SuspectStatus.choices,
        required=False,
    )
    case = serializers.IntegerField(required=False, min_value=1)
    national_id = serializers.CharField(required=False, max_length=10)
    search = serializers.CharField(
        required=False,
        max_length=255,
        allow_blank=False,
    )
    most_wanted = serializers.BooleanField(required=False)
    created_after = serializers.DateField(required=False)
    created_before = serializers.DateField(required=False)
    approval_status = serializers.ChoiceField(
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        required=False,
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Ensure ``created_after <= created_before`` when both are provided.

        Implementation Contract
        -----------------------
        If both present and ``created_after > created_before``, raise
        ``ValidationError("created_after must be earlier than created_before.")``.
        """
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════
#  2. Suspect Read Serializers
# ═══════════════════════════════════════════════════════════════════


class SuspectListSerializer(serializers.ModelSerializer):
    """
    Compact representation for the suspect list endpoint.

    Excludes heavy nested data (interrogations, warrants, trials) to
    keep list-page payloads small.  Includes display labels, case info,
    and identification metadata.
    """

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    identified_by_name = serializers.SerializerMethodField()
    case_title = serializers.SerializerMethodField()
    is_most_wanted = serializers.BooleanField(read_only=True)
    days_wanted = serializers.IntegerField(read_only=True)

    class Meta:
        model = Suspect
        fields = [
            "id",
            "full_name",
            "national_id",
            "phone_number",
            "photo",
            "status",
            "status_display",
            "case",
            "case_title",
            "wanted_since",
            "days_wanted",
            "is_most_wanted",
            "identified_by",
            "identified_by_name",
            "sergeant_approval_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_identified_by_name(self, obj: Suspect) -> str | None:
        """
        Return the identifying detective's full name.

        Implementation Contract
        -----------------------
        Return ``obj.identified_by.get_full_name()`` or ``None``.
        """
        raise NotImplementedError

    def get_case_title(self, obj: Suspect) -> str | None:
        """
        Return the linked case's title for display purposes.

        Implementation Contract
        -----------------------
        Return ``obj.case.title`` if the case FK is loaded.
        """
        raise NotImplementedError


class InterrogationInlineSerializer(serializers.ModelSerializer):
    """
    Compact inline serializer for interrogations nested inside
    ``SuspectDetailSerializer``.  Shows key scores and officer info
    without the full interrogation detail.
    """

    detective_name = serializers.SerializerMethodField()
    sergeant_name = serializers.SerializerMethodField()

    class Meta:
        model = Interrogation
        fields = [
            "id",
            "detective",
            "detective_name",
            "sergeant",
            "sergeant_name",
            "detective_guilt_score",
            "sergeant_guilt_score",
            "notes",
            "created_at",
        ]
        read_only_fields = fields

    def get_detective_name(self, obj: Interrogation) -> str | None:
        """Return the detective's full name."""
        raise NotImplementedError

    def get_sergeant_name(self, obj: Interrogation) -> str | None:
        """Return the sergeant's full name."""
        raise NotImplementedError


class TrialInlineSerializer(serializers.ModelSerializer):
    """
    Compact inline serializer for trials nested inside
    ``SuspectDetailSerializer``.
    """

    verdict_display = serializers.CharField(
        source="get_verdict_display",
        read_only=True,
    )
    judge_name = serializers.SerializerMethodField()

    class Meta:
        model = Trial
        fields = [
            "id",
            "judge",
            "judge_name",
            "verdict",
            "verdict_display",
            "punishment_title",
            "punishment_description",
            "created_at",
        ]
        read_only_fields = fields

    def get_judge_name(self, obj: Trial) -> str | None:
        """Return the judge's full name."""
        raise NotImplementedError


class BailInlineSerializer(serializers.ModelSerializer):
    """
    Compact inline serializer for bail records nested inside
    ``SuspectDetailSerializer``.
    """

    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Bail
        fields = [
            "id",
            "amount",
            "is_paid",
            "payment_reference",
            "paid_at",
            "approved_by",
            "approved_by_name",
            "created_at",
        ]
        read_only_fields = fields

    def get_approved_by_name(self, obj: Bail) -> str | None:
        """Return the approving sergeant's full name."""
        raise NotImplementedError


class SuspectDetailSerializer(serializers.ModelSerializer):
    """
    Full detail serializer for a single suspect.

    Nests related interrogations, trials, bail records, and computed
    properties (most wanted score, reward amount, days wanted).  This
    gives the detective/sergeant a comprehensive view of the suspect's
    full profile and lifecycle within a single API call.

    Nested Relations
    ----------------
    - ``interrogations`` — all interrogation sessions for this suspect
    - ``trials``         — all trial records for this suspect
    - ``bails``          — all bail records for this suspect
    - ``bounty_tip_count`` — number of tips submitted about this suspect

    Computed Fields
    ---------------
    - ``days_wanted``       — days since ``wanted_since``
    - ``is_most_wanted``    — True if wanted > 30 days
    - ``most_wanted_score`` — ranking score for Most Wanted page
    - ``reward_amount``     — bounty reward in Rials
    """

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    identified_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    case_title = serializers.SerializerMethodField()

    # Computed model properties
    days_wanted = serializers.IntegerField(read_only=True)
    is_most_wanted = serializers.BooleanField(read_only=True)
    most_wanted_score = serializers.IntegerField(read_only=True)
    reward_amount = serializers.IntegerField(read_only=True)

    # Nested relations
    interrogations = InterrogationInlineSerializer(many=True, read_only=True)
    trials = TrialInlineSerializer(many=True, read_only=True)
    bails = BailInlineSerializer(many=True, read_only=True)
    bounty_tip_count = serializers.SerializerMethodField()

    class Meta:
        model = Suspect
        fields = [
            "id",
            "full_name",
            "national_id",
            "phone_number",
            "photo",
            "address",
            "description",
            "status",
            "status_display",
            "case",
            "case_title",
            "user",
            "wanted_since",
            "days_wanted",
            "is_most_wanted",
            "most_wanted_score",
            "reward_amount",
            "identified_by",
            "identified_by_name",
            "approved_by_sergeant",
            "approved_by_name",
            "sergeant_approval_status",
            "sergeant_rejection_message",
            "interrogations",
            "trials",
            "bails",
            "bounty_tip_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_identified_by_name(self, obj: Suspect) -> str | None:
        """
        Return the identifying detective's full name.

        Implementation Contract
        -----------------------
        Return ``obj.identified_by.get_full_name()`` or ``None``.
        """
        raise NotImplementedError

    def get_approved_by_name(self, obj: Suspect) -> str | None:
        """
        Return the approving sergeant's full name, or ``None`` if not
        yet approved.

        Implementation Contract
        -----------------------
        If ``obj.approved_by_sergeant`` is not None, return their full name.
        Otherwise return ``None``.
        """
        raise NotImplementedError

    def get_case_title(self, obj: Suspect) -> str | None:
        """
        Return the linked case's title.

        Implementation Contract
        -----------------------
        Return ``obj.case.title`` if loaded, else ``None``.
        """
        raise NotImplementedError

    def get_bounty_tip_count(self, obj: Suspect) -> int:
        """
        Return the number of bounty tips submitted about this suspect.

        Implementation Contract
        -----------------------
        Return ``obj.bounty_tips.count()``.
        """
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════
#  3. Suspect Write Serializers (Create / Update)
# ═══════════════════════════════════════════════════════════════════


class SuspectCreateSerializer(serializers.ModelSerializer):
    """
    Validates input for identifying/creating a new suspect in a case.

    The ``identified_by`` (detective) is injected by the service layer
    from ``request.user``, not accepted from the client.  The ``status``
    defaults to ``WANTED`` and ``sergeant_approval_status`` defaults to
    ``pending`` — both set by the service.

    Required Fields
    ---------------
    - ``case``       : FK to the case this suspect is linked to
    - ``full_name``  : suspect's full name

    Optional Fields
    ---------------
    - ``national_id``, ``phone_number``, ``photo``, ``address``,
      ``description``, ``user`` (link to system user if applicable)

    Example Request
    ---------------
    ::

        POST /api/suspects/
        {
            "case": 5,
            "full_name": "Roy Earle",
            "national_id": "1234567890",
            "phone_number": "+1-213-555-0147",
            "address": "742 S. Broadway, Los Angeles",
            "description": "Tall, dark hair, scar on left cheek."
        }
    """

    class Meta:
        model = Suspect
        fields = [
            "case",
            "full_name",
            "national_id",
            "phone_number",
            "photo",
            "address",
            "description",
            "user",
        ]
        extra_kwargs = {
            "case": {"required": True},
            "full_name": {"required": True},
            "national_id": {"required": False},
            "phone_number": {"required": False},
            "photo": {"required": False},
            "address": {"required": False},
            "description": {"required": False},
            "user": {"required": False},
        }


class SuspectUpdateSerializer(serializers.ModelSerializer):
    """
    Validates partial updates to a suspect's profile fields.

    Only mutable identity/description fields are accepted.
    ``status``, ``case``, ``identified_by``, and approval fields are
    managed through dedicated workflow endpoints, NOT through this
    serializer.

    Mutable Fields
    --------------
    - ``full_name``, ``national_id``, ``phone_number``, ``photo``,
      ``address``, ``description``

    Immutable Fields (excluded)
    ---------------------------
    - ``case``, ``status``, ``identified_by``, ``approved_by_sergeant``,
      ``sergeant_approval_status``, ``wanted_since``, ``user``
    """

    class Meta:
        model = Suspect
        fields = [
            "full_name",
            "national_id",
            "phone_number",
            "photo",
            "address",
            "description",
        ]


# ═══════════════════════════════════════════════════════════════════
#  4. Workflow Action Serializers
# ═══════════════════════════════════════════════════════════════════


class SuspectApprovalSerializer(serializers.Serializer):
    """
    Request body for ``POST /api/suspects/{id}/approve/``.

    Used by the **Sergeant** to approve or reject a suspect identified
    by a Detective.

    Fields
    ------
    ``decision`` : str
        ``"approve"`` or ``"reject"``.
    ``rejection_message`` : str
        Required when ``decision == "reject"``; the message is sent
        back to the Detective explaining why the suspect identification
        was rejected.

    Payload Examples
    ----------------
    **Approve:**
    ::

        {"decision": "approve"}

    **Reject:**
    ::

        {
            "decision": "reject",
            "rejection_message": "Insufficient evidence linking suspect to case."
        }
    """

    DECISION_CHOICES = [("approve", "Approve"), ("reject", "Reject")]

    decision = serializers.ChoiceField(choices=DECISION_CHOICES)
    rejection_message = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=2000,
        help_text="Required when rejecting. Sent back to the detective.",
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Cross-field validation:

        - If ``decision == "reject"`` and ``rejection_message`` is blank,
          raise ``ValidationError``.

        Implementation Contract
        -----------------------
        1. ``decision = attrs["decision"]``
        2. If ``decision == "reject"`` and not ``attrs.get("rejection_message", "").strip()``:
           raise ``ValidationError({"rejection_message": "A rejection message is required."})``.
        3. Return attrs.
        """
        raise NotImplementedError


class ArrestWarrantSerializer(serializers.Serializer):
    """
    Request body for ``POST /api/suspects/{id}/issue-warrant/``.

    Used by the **Sergeant** to issue an arrest warrant for an approved
    suspect.  The warrant must only be issuable after the suspect has
    been approved by a sergeant (``sergeant_approval_status == "approved"``).

    Fields
    ------
    ``warrant_reason`` : str
        Detailed justification for the arrest warrant.
    ``priority`` : str
        Urgency level: ``"normal"``, ``"high"``, ``"critical"``.

    Example
    -------
    ::

        POST /api/suspects/12/issue-warrant/
        {
            "warrant_reason": "Strong forensic evidence linking suspect to murder weapon.",
            "priority": "high"
        }
    """

    PRIORITY_CHOICES = [
        ("normal", "Normal"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    warrant_reason = serializers.CharField(
        required=True,
        max_length=5000,
        help_text="Detailed justification for the arrest warrant.",
    )
    priority = serializers.ChoiceField(
        choices=PRIORITY_CHOICES,
        default="normal",
        help_text="Urgency level for the warrant.",
    )


class ArrestPayloadSerializer(serializers.Serializer):
    """
    Request body for ``POST /api/suspects/{id}/arrest/``.

    Transitions a suspect's status to ``ARRESTED`` (In Custody).
    This endpoint requires the **Sergeant** or **Captain** role and
    validates that an active arrest warrant exists for the suspect
    OR provides an override justification.

    Fields
    ------
    ``arrest_location`` : str
        Location where the arrest took place.
    ``arrest_notes`` : str
        Additional notes about the arrest circumstances.
    ``warrant_override_justification`` : str
        If no warrant exists, this field must provide a justification
        for the warrantless arrest (e.g. caught in the act).  Optional
        when a valid warrant already exists.

    Validation Rules
    ----------------
    - If no active warrant exists for the suspect AND
      ``warrant_override_justification`` is blank → HTTP 400.
    - The serializer performs a preliminary check; the full warrant
      validation is done in the service layer.

    Example (with warrant)
    ----------------------
    ::

        POST /api/suspects/12/arrest/
        {
            "arrest_location": "742 S. Broadway, Los Angeles",
            "arrest_notes": "Suspect apprehended without resistance."
        }

    Example (without warrant — override)
    -------------------------------------
    ::

        POST /api/suspects/12/arrest/
        {
            "arrest_location": "Corner of 5th and Main",
            "arrest_notes": "Suspect caught fleeing crime scene.",
            "warrant_override_justification": "Suspect caught in the act of committing a felony."
        }
    """

    arrest_location = serializers.CharField(
        required=True,
        max_length=500,
        help_text="Location where the arrest took place.",
    )
    arrest_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=5000,
        help_text="Additional notes about the arrest.",
    )
    warrant_override_justification = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=3000,
        help_text=(
            "Required if no active warrant exists. "
            "Justification for a warrantless arrest (e.g., caught in the act)."
        ),
    )


class SuspectStatusTransitionSerializer(serializers.Serializer):
    """
    Request body for ``POST /api/suspects/{id}/transition-status/``.

    Generic status transition endpoint for moving a suspect through
    lifecycle states beyond the dedicated arrest/bail/trial workflows.

    Allowed transitions depend on the current status and the user's
    role.  The service layer enforces the full state-machine rules.

    Fields
    ------
    ``new_status`` : str
        The target status (one of ``SuspectStatus`` values).
    ``reason`` : str
        Justification for the transition.
    """

    new_status = serializers.ChoiceField(
        choices=SuspectStatus.choices,
        help_text="Target status for the suspect.",
    )
    reason = serializers.CharField(
        required=True,
        max_length=2000,
        help_text="Justification for the status transition.",
    )


# ═══════════════════════════════════════════════════════════════════
#  5. Interrogation Serializers
# ═══════════════════════════════════════════════════════════════════


class InterrogationListSerializer(serializers.ModelSerializer):
    """
    Compact representation for listing interrogation sessions.

    Used in ``GET /api/suspects/{id}/interrogations/``.
    """

    detective_name = serializers.SerializerMethodField()
    sergeant_name = serializers.SerializerMethodField()

    class Meta:
        model = Interrogation
        fields = [
            "id",
            "suspect",
            "case",
            "detective",
            "detective_name",
            "sergeant",
            "sergeant_name",
            "detective_guilt_score",
            "sergeant_guilt_score",
            "created_at",
        ]
        read_only_fields = fields

    def get_detective_name(self, obj: Interrogation) -> str | None:
        """Return the detective's full name."""
        raise NotImplementedError

    def get_sergeant_name(self, obj: Interrogation) -> str | None:
        """Return the sergeant's full name."""
        raise NotImplementedError


class InterrogationDetailSerializer(serializers.ModelSerializer):
    """
    Full detail serializer for a single interrogation session.

    Includes all fields plus nested subject (suspect) info.
    """

    detective_name = serializers.SerializerMethodField()
    sergeant_name = serializers.SerializerMethodField()
    suspect_name = serializers.SerializerMethodField()

    class Meta:
        model = Interrogation
        fields = [
            "id",
            "suspect",
            "suspect_name",
            "case",
            "detective",
            "detective_name",
            "sergeant",
            "sergeant_name",
            "detective_guilt_score",
            "sergeant_guilt_score",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_detective_name(self, obj: Interrogation) -> str | None:
        """Return the detective's full name."""
        raise NotImplementedError

    def get_sergeant_name(self, obj: Interrogation) -> str | None:
        """Return the sergeant's full name."""
        raise NotImplementedError

    def get_suspect_name(self, obj: Interrogation) -> str | None:
        """Return the suspect's full name."""
        raise NotImplementedError


class InterrogationCreateSerializer(serializers.ModelSerializer):
    """
    Validates input for creating a new interrogation session.

    The ``detective`` and ``sergeant`` are resolved from ``request.user``
    and the case context by the service layer.  The ``case`` is
    automatically derived from the suspect's linked case.

    Fields
    ------
    - ``detective_guilt_score`` : int (1–10)
    - ``sergeant_guilt_score``  : int (1–10)
    - ``notes``                 : str (optional)

    The ``suspect`` FK is injected by the view from the URL path
    parameter (``/suspects/{suspect_id}/interrogations/``).

    Example Request
    ---------------
    ::

        POST /api/suspects/12/interrogations/
        {
            "detective_guilt_score": 8,
            "sergeant_guilt_score": 7,
            "notes": "Suspect showed signs of deception during questioning about alibi."
        }
    """

    class Meta:
        model = Interrogation
        fields = [
            "detective_guilt_score",
            "sergeant_guilt_score",
            "notes",
        ]
        extra_kwargs = {
            "detective_guilt_score": {"required": True},
            "sergeant_guilt_score": {"required": True},
            "notes": {"required": False},
        }


# ═══════════════════════════════════════════════════════════════════
#  6. Trial Serializers
# ═══════════════════════════════════════════════════════════════════


class TrialListSerializer(serializers.ModelSerializer):
    """
    Compact representation for listing trials.

    Used in ``GET /api/suspects/{id}/trials/``.
    """

    verdict_display = serializers.CharField(
        source="get_verdict_display",
        read_only=True,
    )
    judge_name = serializers.SerializerMethodField()

    class Meta:
        model = Trial
        fields = [
            "id",
            "suspect",
            "case",
            "judge",
            "judge_name",
            "verdict",
            "verdict_display",
            "punishment_title",
            "created_at",
        ]
        read_only_fields = fields

    def get_judge_name(self, obj: Trial) -> str | None:
        """Return the judge's full name."""
        raise NotImplementedError


class TrialDetailSerializer(serializers.ModelSerializer):
    """
    Full detail serializer for a single trial record.
    """

    verdict_display = serializers.CharField(
        source="get_verdict_display",
        read_only=True,
    )
    judge_name = serializers.SerializerMethodField()
    suspect_name = serializers.SerializerMethodField()

    class Meta:
        model = Trial
        fields = [
            "id",
            "suspect",
            "suspect_name",
            "case",
            "judge",
            "judge_name",
            "verdict",
            "verdict_display",
            "punishment_title",
            "punishment_description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_judge_name(self, obj: Trial) -> str | None:
        """Return the judge's full name."""
        raise NotImplementedError

    def get_suspect_name(self, obj: Trial) -> str | None:
        """Return the suspect's full name."""
        raise NotImplementedError


class TrialCreateSerializer(serializers.ModelSerializer):
    """
    Validates input for creating a trial record.

    The ``judge`` is injected from ``request.user`` by the service layer.
    The ``suspect`` and ``case`` are resolved from the URL path.

    Fields
    ------
    - ``verdict``               : str ("guilty" or "innocent")
    - ``punishment_title``      : str (required if guilty)
    - ``punishment_description``: str (required if guilty)

    Validation
    ----------
    If ``verdict == "guilty"``, both ``punishment_title`` and
    ``punishment_description`` must be provided.

    Example Request
    ---------------
    ::

        POST /api/suspects/12/trials/
        {
            "verdict": "guilty",
            "punishment_title": "First Degree Murder",
            "punishment_description": "25 years imprisonment without parole."
        }
    """

    class Meta:
        model = Trial
        fields = [
            "verdict",
            "punishment_title",
            "punishment_description",
        ]
        extra_kwargs = {
            "verdict": {"required": True},
            "punishment_title": {"required": False},
            "punishment_description": {"required": False},
        }

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        If verdict is guilty, punishment fields must be provided.

        Implementation Contract
        -----------------------
        1. If ``attrs["verdict"] == "guilty"``:
           a. If not ``attrs.get("punishment_title", "").strip()``:
              raise ``ValidationError({"punishment_title": "Required when verdict is guilty."})``.
           b. If not ``attrs.get("punishment_description", "").strip()``:
              raise ``ValidationError({"punishment_description": "Required when verdict is guilty."})``.
        2. Return attrs.
        """
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════
#  7. BountyTip Serializers
# ═══════════════════════════════════════════════════════════════════


class BountyTipListSerializer(serializers.ModelSerializer):
    """
    Compact representation for listing bounty tips.

    Used in ``GET /api/suspects/{id}/bounty-tips/`` and
    ``GET /api/bounty-tips/``.
    """

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    informant_name = serializers.SerializerMethodField()

    class Meta:
        model = BountyTip
        fields = [
            "id",
            "suspect",
            "case",
            "informant",
            "informant_name",
            "status",
            "status_display",
            "is_claimed",
            "created_at",
        ]
        read_only_fields = fields

    def get_informant_name(self, obj: BountyTip) -> str | None:
        """Return the informant's full name."""
        raise NotImplementedError


class BountyTipDetailSerializer(serializers.ModelSerializer):
    """
    Full detail serializer for a single bounty tip.
    """

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    informant_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    verified_by_name = serializers.SerializerMethodField()

    class Meta:
        model = BountyTip
        fields = [
            "id",
            "suspect",
            "case",
            "informant",
            "informant_name",
            "information",
            "status",
            "status_display",
            "reviewed_by",
            "reviewed_by_name",
            "verified_by",
            "verified_by_name",
            "unique_code",
            "reward_amount",
            "is_claimed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_informant_name(self, obj: BountyTip) -> str | None:
        """Return the informant's full name."""
        raise NotImplementedError

    def get_reviewed_by_name(self, obj: BountyTip) -> str | None:
        """Return the reviewing officer's name, or None."""
        raise NotImplementedError

    def get_verified_by_name(self, obj: BountyTip) -> str | None:
        """Return the verifying detective's name, or None."""
        raise NotImplementedError


class BountyTipCreateSerializer(serializers.ModelSerializer):
    """
    Validates input for a citizen submitting a bounty tip.

    The ``informant`` is injected from ``request.user`` by the service.
    At least one of ``suspect`` or ``case`` must be provided.

    Example Request
    ---------------
    ::

        POST /api/bounty-tips/
        {
            "suspect": 12,
            "case": 5,
            "information": "I saw the suspect at the corner of 5th and Main at 3 AM."
        }
    """

    class Meta:
        model = BountyTip
        fields = [
            "suspect",
            "case",
            "information",
        ]
        extra_kwargs = {
            "suspect": {"required": False},
            "case": {"required": False},
            "information": {"required": True},
        }

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Ensure at least one of ``suspect`` or ``case`` is provided.

        Implementation Contract
        -----------------------
        If neither ``suspect`` nor ``case`` is in attrs (or both are None),
        raise ``ValidationError("At least one of 'suspect' or 'case' must be provided.")``.
        """
        raise NotImplementedError


class BountyTipReviewSerializer(serializers.Serializer):
    """
    Request body for ``POST /api/bounty-tips/{id}/review/``.

    Used by a **Police Officer** to perform the initial review of a
    bounty tip.

    Fields
    ------
    ``decision`` : str
        ``"accept"`` (forward to detective) or ``"reject"``.
    ``review_notes`` : str
        Optional notes about the review decision.
    """

    DECISION_CHOICES = [("accept", "Accept"), ("reject", "Reject")]

    decision = serializers.ChoiceField(choices=DECISION_CHOICES)
    review_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=2000,
    )


class BountyTipVerifySerializer(serializers.Serializer):
    """
    Request body for ``POST /api/bounty-tips/{id}/verify/``.

    Used by the **Detective** to verify bounty tip information.
    Upon verification, a unique reward code is generated for the
    informant.

    Fields
    ------
    ``decision`` : str
        ``"verify"`` or ``"reject"``.
    ``verification_notes`` : str
        Notes about the verification outcome.
    """

    DECISION_CHOICES = [("verify", "Verify"), ("reject", "Reject")]

    decision = serializers.ChoiceField(choices=DECISION_CHOICES)
    verification_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=2000,
    )


class BountyRewardLookupSerializer(serializers.Serializer):
    """
    Request body for ``POST /api/bounty-tips/lookup-reward/``.

    Used by any police rank to look up a bounty reward claim using
    the citizen's national ID and unique code.

    Fields
    ------
    ``national_id``  : str — citizen's national ID
    ``unique_code``  : str — reward claim code
    """

    national_id = serializers.CharField(
        required=True,
        max_length=10,
        help_text="Citizen's national ID.",
    )
    unique_code = serializers.CharField(
        required=True,
        max_length=50,
        help_text="Reward claim code provided to the citizen.",
    )


# ═══════════════════════════════════════════════════════════════════
#  8. Bail Serializers
# ═══════════════════════════════════════════════════════════════════


class BailListSerializer(serializers.ModelSerializer):
    """
    Compact representation for listing bail records.
    """

    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Bail
        fields = [
            "id",
            "suspect",
            "case",
            "amount",
            "is_paid",
            "approved_by",
            "approved_by_name",
            "paid_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_approved_by_name(self, obj: Bail) -> str | None:
        """Return the approving sergeant's full name."""
        raise NotImplementedError


class BailDetailSerializer(serializers.ModelSerializer):
    """
    Full detail serializer for a single bail record.
    """

    approved_by_name = serializers.SerializerMethodField()
    suspect_name = serializers.SerializerMethodField()

    class Meta:
        model = Bail
        fields = [
            "id",
            "suspect",
            "suspect_name",
            "case",
            "amount",
            "is_paid",
            "payment_reference",
            "paid_at",
            "approved_by",
            "approved_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_approved_by_name(self, obj: Bail) -> str | None:
        """Return the approving sergeant's full name."""
        raise NotImplementedError

    def get_suspect_name(self, obj: Bail) -> str | None:
        """Return the suspect's full name."""
        raise NotImplementedError


class BailCreateSerializer(serializers.ModelSerializer):
    """
    Validates input for creating a bail record.

    The ``approved_by`` (sergeant) is injected from ``request.user``.
    The ``suspect`` and ``case`` are resolved from the URL path.

    Validation
    ----------
    The service layer validates that:
    - The suspect's case is Level 2 or Level 3.
    - The suspect is currently ``ARRESTED`` or ``CONVICTED`` (for Level 3 criminals).
    - The bail ``amount`` is positive.

    Example Request
    ---------------
    ::

        POST /api/suspects/12/bails/
        {
            "amount": 50000000
        }
    """

    class Meta:
        model = Bail
        fields = [
            "amount",
        ]
        extra_kwargs = {
            "amount": {"required": True},
        }


# ═══════════════════════════════════════════════════════════════════
#  9. Most-Wanted Serializer
# ═══════════════════════════════════════════════════════════════════


class MostWantedSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for the public Most Wanted listing page.

    Returns suspect identity, photo, case summary, computed ranking
    score, and bounty reward.  Visible to all authenticated users
    (including base users).

    Used in ``GET /api/suspects/most-wanted/``.
    """

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    days_wanted = serializers.IntegerField(read_only=True)
    most_wanted_score = serializers.IntegerField(read_only=True)
    reward_amount = serializers.IntegerField(read_only=True)
    case_title = serializers.SerializerMethodField()

    class Meta:
        model = Suspect
        fields = [
            "id",
            "full_name",
            "national_id",
            "photo",
            "description",
            "address",
            "status",
            "status_display",
            "case",
            "case_title",
            "wanted_since",
            "days_wanted",
            "most_wanted_score",
            "reward_amount",
        ]
        read_only_fields = fields

    def get_case_title(self, obj: Suspect) -> str | None:
        """Return the case's title for public display."""
        raise NotImplementedError
