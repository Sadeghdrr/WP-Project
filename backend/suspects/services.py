"""
Suspects app Service Layer.

This module is the **single source of truth** for all business logic
in the ``suspects`` app.  Views must remain thin: validate input via
serializers, call a service method, and return the result wrapped in
a DRF ``Response``.

Architecture
------------
- ``SuspectProfileService``     — Suspect CRUD, filtered querysets, most-wanted.
- ``ArrestAndWarrantService``   — Warrant issuance, arrest execution, status
                                  transitions, and audit trail.
- ``InterrogationService``      — Interrogation session creation & retrieval.
- ``TrialService``              — Trial record creation & retrieval.
- ``BountyTipService``          — Tip submission, officer review, detective
                                  verification, reward lookup.
- ``BailService``               — Bail creation, payment processing.

Permission Constants (from ``core.permissions_constants.SuspectsPerms``)
------------------------------------------------------------------------
- ``CAN_IDENTIFY_SUSPECT``       — Detective identifies suspects.
- ``CAN_APPROVE_SUSPECT``        — Sergeant approves/rejects suspect IDs.
- ``CAN_ISSUE_ARREST_WARRANT``   — Sergeant issues arrest warrants.
- ``CAN_CONDUCT_INTERROGATION``  — Sergeant/Detective conduct interrogation.
- ``CAN_SCORE_GUILT``            — Sergeant/Detective assign guilt scores.
- ``CAN_RENDER_VERDICT``         — Captain/Chief renders verdict.
- ``CAN_JUDGE_TRIAL``            — Judge presides over trial.
- ``CAN_REVIEW_BOUNTY_TIP``      — Officer reviews bounty tips.
- ``CAN_VERIFY_BOUNTY_TIP``      — Detective verifies bounty tips.
- ``CAN_SET_BAIL_AMOUNT``        — Sergeant sets bail amount.
"""

from __future__ import annotations

import logging
import secrets
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.db.models import (
    ExpressionWrapper,
    F,
    IntegerField,
    Max,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Value,
)
from django.db.models.functions import Coalesce, ExtractDay, Now
from django.utils import timezone

from cases.models import CrimeLevel
from core.constants import REWARD_MULTIPLIER
from core.domain.access import apply_role_filter, get_user_role_name
from core.domain.exceptions import DomainError, InvalidTransition, NotFound, PermissionDenied
from core.domain.notifications import NotificationService
from core.permissions_constants import CasesPerms, SuspectsPerms
from core.services import RewardCalculatorService

from .models import (
    Bail,
    BountyTip,
    BountyTipStatus,
    Interrogation,
    Suspect,
    SuspectStatus,
    SuspectStatusLog,
    Trial,
    VerdictChoice,
    Warrant,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  Suspect Profile Service
# ═══════════════════════════════════════════════════════════════════


class SuspectProfileService:
    """
    Handles suspect profile CRUD, filtered querysets, and the
    Most-Wanted listing logic.

    This service is the **primary entry point** for all suspect
    profile operations.  Views must delegate here rather than
    performing direct ORM queries.
    """

    @staticmethod
    def get_filtered_queryset(
        requesting_user: Any,
        filters: dict[str, Any],
    ) -> QuerySet[Suspect]:
        """
        Build a role-scoped, filtered queryset of ``Suspect`` objects.

        Parameters
        ----------
        requesting_user : User
            From ``request.user``.  Used to apply role-based visibility
            scoping before applying explicit filters.
        filters : dict
            Cleaned query-parameter dict from ``SuspectFilterSerializer``.
            Supported keys:
            - ``status``          : str   (``SuspectStatus`` value)
            - ``case``            : int   (case PK)
            - ``national_id``     : str   (exact match)
            - ``search``          : str   (full-text on name/description)
            - ``most_wanted``     : bool  (filter to > 30 days wanted)
            - ``created_after``   : date
            - ``created_before``  : date
            - ``approval_status`` : str   (pending/approved/rejected)

        Returns
        -------
        QuerySet[Suspect]
            Filtered, ``select_related`` queryset ready for serialisation.

        Role Scoping Rules
        ------------------
        - **Base User / Complainant / Witness**: can only see suspects
          on cases they are directly associated with.
        - **Detective**: sees suspects on cases assigned to them, plus
          suspects they have identified.
        - **Sergeant**: sees suspects on cases they supervise, plus
          suspects pending their approval.
        - **Captain / Chief / Admin / Judge**: unrestricted visibility.
        - **Coroner**: limited to suspects on cases they have examined
          evidence for.

        Implementation Contract
        -----------------------
        1. Determine the user's role(s).
        2. Apply the role-specific base queryset scope.
        3. Apply explicit ``filters`` on top of the scoped queryset:
           a. ``status``          → exact match.
           b. ``case``            → ``case_id`` exact match.
           c. ``national_id``     → ``national_id`` exact match.
           d. ``search``          → ``Q(full_name__icontains=...) |
                                     Q(description__icontains=...) |
                                     Q(address__icontains=...)``.
           e. ``most_wanted``     → annotate/filter suspects wanted > 30 days.
           f. ``created_after``   → ``created_at__date__gte``.
           g. ``created_before``  → ``created_at__date__lte``.
           h. ``approval_status`` → ``sergeant_approval_status`` exact match.
        4. ``select_related("case", "identified_by", "approved_by_sergeant", "user")``.
        5. ``prefetch_related("interrogations", "trials", "bails")``.
        6. Return queryset ordered by ``-wanted_since``.
        """
        qs = Suspect.objects.select_related(
            "case", "identified_by", "approved_by_sergeant", "user",
        ).prefetch_related(
            "interrogations", "trials", "bails",
        )

        # ── Role-based scoping ──────────────────────────────────────
        user = requesting_user
        role_name = ""
        if hasattr(user, "role") and user.role:
            role_name = user.role.name.lower()

        high_level_roles = {
            "captain", "police chief", "admin", "system administrator", "judge",
        }
        if role_name not in high_level_roles and not user.is_superuser:
            if role_name == "sergeant":
                qs = qs.filter(
                    Q(case__assigned_sergeant=user)
                    | Q(sergeant_approval_status="pending")
                )
            elif role_name == "detective":
                qs = qs.filter(
                    Q(case__assigned_detective=user) | Q(identified_by=user)
                )
            elif role_name == "coroner":
                qs = qs.filter(case__evidences__registered_by=user).distinct()
            else:
                # Base user / complainant / witness
                qs = qs.filter(
                    Q(case__complainants__user=user)
                    | Q(case__created_by=user)
                ).distinct()

        # ── Explicit filters ────────────────────────────────────────
        if "status" in filters:
            qs = qs.filter(status=filters["status"])
        if "case" in filters:
            qs = qs.filter(case_id=filters["case"])
        if "national_id" in filters:
            qs = qs.filter(national_id=filters["national_id"])
        if "search" in filters:
            term = filters["search"]
            qs = qs.filter(
                Q(full_name__icontains=term)
                | Q(description__icontains=term)
                | Q(address__icontains=term)
            )
        if filters.get("most_wanted"):
            cutoff = timezone.now() - timedelta(days=30)
            # Strictly "over 30 days" per project-doc §4.7.
            qs = qs.filter(status=SuspectStatus.WANTED, wanted_since__lt=cutoff)
        if "created_after" in filters:
            qs = qs.filter(created_at__date__gte=filters["created_after"])
        if "created_before" in filters:
            qs = qs.filter(created_at__date__lte=filters["created_before"])
        if "approval_status" in filters:
            qs = qs.filter(sergeant_approval_status=filters["approval_status"])

        return qs.order_by("-wanted_since")

    @staticmethod
    def get_suspect_detail(pk: int) -> Suspect:
        """
        Retrieve a single suspect by PK with all related data
        pre-fetched for detail serialisation.

        Parameters
        ----------
        pk : int
            Primary key of the suspect.

        Returns
        -------
        Suspect
            The suspect instance with related data loaded.

        Raises
        ------
        Suspect.DoesNotExist
            If no suspect with the given PK exists.

        Implementation Contract
        -----------------------
        1. ``suspect = Suspect.objects.select_related(
               "case", "identified_by", "approved_by_sergeant", "user"
           ).prefetch_related(
               "interrogations__detective",
               "interrogations__sergeant",
               "trials__judge",
               "bails__approved_by",
               "bounty_tips",
           ).get(pk=pk)``.
        2. Return the suspect instance.
        """
        try:
            return Suspect.objects.select_related(
                "case", "identified_by", "approved_by_sergeant", "user",
            ).prefetch_related(
                "interrogations__detective",
                "interrogations__sergeant",
                "trials__judge",
                "bails__approved_by",
                "bounty_tips",
            ).get(pk=pk)
        except Suspect.DoesNotExist:
            raise NotFound(f"Suspect with id {pk} not found.")

    @staticmethod
    @transaction.atomic
    def create_suspect(
        validated_data: dict[str, Any],
        requesting_user: Any,
    ) -> Suspect:
        """
        Identify a new suspect and link them to a case.

        This corresponds to the Detective identifying a suspect
        (project-doc §4.4).  The suspect is created with status
        ``WANTED`` and ``sergeant_approval_status = "pending"``.

        Parameters
        ----------
        validated_data : dict
            Cleaned data from ``SuspectCreateSerializer``.
            Keys: ``case``, ``full_name``, ``national_id``,
            ``phone_number``, ``photo``, ``address``, ``description``,
            ``user`` (optional).
        requesting_user : User
            The detective identifying the suspect.  Must have the
            ``CAN_IDENTIFY_SUSPECT`` permission.

        Returns
        -------
        Suspect
            The newly created suspect instance.

        Raises
        ------
        PermissionError
            If ``requesting_user`` lacks ``CAN_IDENTIFY_SUSPECT``.

        Implementation Contract
        -----------------------
        1. Assert ``requesting_user.has_perm(
               f"suspects.{SuspectsPerms.CAN_IDENTIFY_SUSPECT}"
           )``.
        2. Inject ``identified_by = requesting_user``.
        3. Inject ``status = SuspectStatus.WANTED``.
        4. Inject ``sergeant_approval_status = "pending"``.
        5. ``suspect = Suspect.objects.create(**validated_data)``.
        6. Dispatch notification to the Sergeant about the new suspect
           identification pending approval.
        7. Return ``suspect``.
        """
        if not requesting_user.has_perm(
            f"suspects.{SuspectsPerms.CAN_IDENTIFY_SUSPECT}"
        ):
            raise PermissionDenied(
                "You do not have permission to identify suspects."
            )

        validated_data["identified_by"] = requesting_user
        validated_data["status"] = SuspectStatus.WANTED
        validated_data["sergeant_approval_status"] = "pending"

        suspect = Suspect.objects.create(**validated_data)

        # Dispatch notification to the Sergeant assigned to the case
        case = suspect.case
        sergeant = getattr(case, "assigned_sergeant", None)
        if sergeant:
            NotificationService.create(
                actor=requesting_user,
                recipients=sergeant,
                event_type="suspect_needs_review",
                payload={
                    "suspect_id": suspect.id,
                    "suspect_name": suspect.full_name,
                    "case_id": case.id,
                    "case_title": case.title,
                    "identified_by": requesting_user.get_full_name(),
                },
                related_object=suspect,
            )

        return suspect

    @staticmethod
    @transaction.atomic
    def update_suspect(
        suspect: Suspect,
        validated_data: dict[str, Any],
        requesting_user: Any,
    ) -> Suspect:
        """
        Update a suspect's mutable profile fields.

        Only identity/description fields can be updated through this
        method.  Status transitions use dedicated service methods.

        Parameters
        ----------
        suspect : Suspect
            The suspect instance to update.
        validated_data : dict
            Cleaned data from ``SuspectUpdateSerializer``.
        requesting_user : User
            Must have ``CHANGE_SUSPECT`` permission.

        Returns
        -------
        Suspect
            The updated suspect instance.

        Raises
        ------
        PermissionError
            If ``requesting_user`` lacks change permission.

        Implementation Contract
        -----------------------
        1. Assert ``requesting_user.has_perm(
               f"suspects.{SuspectsPerms.CHANGE_SUSPECT}"
           )``.
        2. For each key/value in ``validated_data``:
           ``setattr(suspect, key, value)``.
        3. ``update_fields = list(validated_data.keys()) + ["updated_at"]``.
        4. ``suspect.save(update_fields=update_fields)``.
        5. Return ``suspect``.
        """
        if not requesting_user.has_perm(
            f"suspects.{SuspectsPerms.CHANGE_SUSPECT}"
        ):
            raise PermissionDenied(
                "You do not have permission to update suspects."
            )

        for key, value in validated_data.items():
            setattr(suspect, key, value)

        update_fields = list(validated_data.keys()) + ["updated_at"]
        suspect.save(update_fields=update_fields)
        return suspect

    @staticmethod
    def get_most_wanted_list() -> list[Suspect]:
        """
        Return suspects qualifying for the Most Wanted page.

        Eligibility rules (project-doc §4.7)
        ------------------------------------
        1. The suspect MUST have status ``WANTED``.
        2. ``wanted_since`` is **strictly more than 30 days** ago.
        3. The suspect MUST be linked to at least one **open** case
           (not closed or voided).

        Ranking formula
        ---------------
        .. math::

            \\text{score} = \\max(\\text{days\\_wanted in open cases})
                           \\times \\max(\\text{crime\\_degree across all cases})

        For non-empty ``national_id`` values, results are aggregated
        per person (one row per national ID). Computed annotations:
        - ``computed_days_wanted`` = max days wanted in open cases
        - ``crime_degree`` = max crime_level across all linked cases
        - ``computed_score`` = computed_days_wanted * crime_degree
        - ``computed_reward`` = computed_score * REWARD_MULTIPLIER

        Returns
        -------
        list[Suspect]
            Annotated suspect rows ordered by ``computed_score`` descending.
        """
        from cases.models import CaseStatus

        cutoff = timezone.now() - timedelta(
            days=RewardCalculatorService.MOST_WANTED_THRESHOLD_DAYS,
        )

        # Closed / voided statuses to exclude from "open case" check
        closed_statuses = [CaseStatus.CLOSED, CaseStatus.VOIDED]

        eligible_open_rows = (
            Suspect.objects.filter(
                status=SuspectStatus.WANTED,
                wanted_since__lt=cutoff,
            )
            .exclude(case__status__in=closed_statuses)
            .select_related("case")
        )

        max_days_subquery = (
            Suspect.objects.filter(
                national_id=OuterRef("national_id"),
                status=SuspectStatus.WANTED,
                wanted_since__lt=cutoff,
            )
            .exclude(case__status__in=closed_statuses)
            .annotate(days_wanted=ExtractDay(Now() - F("wanted_since")))
            .values("national_id")
            .annotate(max_days=Max("days_wanted"))
            .values("max_days")[:1]
        )
        max_crime_subquery = (
            Suspect.objects.filter(national_id=OuterRef("national_id"))
            .values("national_id")
            .annotate(max_crime=Max("case__crime_level"))
            .values("max_crime")[:1]
        )

        grouped_by_national_id = eligible_open_rows.exclude(national_id="").annotate(
            computed_days_wanted=Coalesce(
                Subquery(max_days_subquery, output_field=IntegerField()),
                Value(0),
            ),
            crime_degree=Coalesce(
                Subquery(max_crime_subquery, output_field=IntegerField()),
                F("case__crime_level"),
            ),
        ).annotate(
            computed_score=ExpressionWrapper(
                F("computed_days_wanted") * F("crime_degree"),
                output_field=IntegerField(),
            ),
            computed_reward=ExpressionWrapper(
                F("computed_days_wanted")
                * F("crime_degree")
                * Value(REWARD_MULTIPLIER),
                output_field=IntegerField(),
            ),
        )

        # Distinct-on picks one representative row per national_id.
        grouped_by_national_id = grouped_by_national_id.order_by(
            "national_id",
            "-computed_score",
            "id",
        ).distinct("national_id")

        # Backward compatibility: keep per-row behavior for missing national_id.
        no_national_id_rows = eligible_open_rows.filter(national_id="").annotate(
            computed_days_wanted=ExtractDay(Now() - F("wanted_since")),
            crime_degree=F("case__crime_level"),
            computed_score=ExpressionWrapper(
                F("computed_days_wanted") * F("crime_degree"),
                output_field=IntegerField(),
            ),
            computed_reward=ExpressionWrapper(
                F("computed_days_wanted")
                * F("crime_degree")
                * Value(REWARD_MULTIPLIER),
                output_field=IntegerField(),
            ),
        ).order_by("-computed_score", "id")

        combined = list(grouped_by_national_id) + list(no_national_id_rows)
        combined.sort(key=lambda suspect: (-suspect.computed_score, suspect.id))
        return combined


# ═══════════════════════════════════════════════════════════════════
#  Arrest and Warrant Service
# ═══════════════════════════════════════════════════════════════════


class ArrestAndWarrantService:
    """
    Handles the complete arrest and warrant lifecycle for suspects.

    This service enforces strict permission checks and validation
    at every step:

    Workflow Overview
    -----------------
    1. **Detective identifies suspect** → ``SuspectProfileService.create_suspect()``
       creates suspect with ``sergeant_approval_status = "pending"``.

    2. **Sergeant approves/rejects** → ``approve_or_reject_suspect()``
       If approved, suspect is eligible for warrant issuance.

    3. **Sergeant issues warrant** → ``issue_arrest_warrant()``
       Records the warrant details.  Suspect remains ``WANTED``.

    4. **Arrest execution** → ``execute_arrest()``
       Transitions suspect to ``ARRESTED``.  Requires:
       - An active warrant (or override justification)
       - ``CAN_ISSUE_ARREST_WARRANT`` permission
       - Suspect is currently ``WANTED``
       Updates the global status and generates an audit log entry.

    5. **Status transitions** → ``transition_status()``
       Generic method for non-arrest transitions (e.g., to
       ``UNDER_INTERROGATION``, ``UNDER_TRIAL``, ``RELEASED``,
       ``CONVICTED``, ``ACQUITTED``).

    State Machine
    -------------
    ::

        WANTED → ARRESTED → UNDER_INTERROGATION → UNDER_TRIAL → CONVICTED
                                                               → ACQUITTED
                                               → RELEASED (bail)

    Permissions Required
    --------------------
    - ``CAN_APPROVE_SUSPECT`` — Sergeant approves/rejects
    - ``CAN_ISSUE_ARREST_WARRANT`` — Sergeant issues warrant
    - ``CAN_CONDUCT_INTERROGATION`` — transition to UNDER_INTERROGATION
    - ``CAN_RENDER_VERDICT`` — Captain/Chief forwards to trial
    - ``CAN_JUDGE_TRIAL`` — Judge renders final verdict
    - ``CAN_SET_BAIL_AMOUNT`` — Sergeant sets bail for release
    """

    @staticmethod
    @transaction.atomic
    def approve_or_reject_suspect(
        suspect_id: int,
        sergeant_user: Any,
        decision: str,
        rejection_message: str = "",
    ) -> Suspect:
        """
        Sergeant approves or rejects a suspect identification.

        This is called after the Detective identifies a suspect and
        reports to the Sergeant (project-doc §4.4).

        Parameters
        ----------
        suspect_id : int
            PK of the suspect to approve/reject.
        sergeant_user : User
            The authenticated Sergeant.  Must have
            ``CAN_APPROVE_SUSPECT`` permission.
        decision : str
            ``"approve"`` or ``"reject"``.
        rejection_message : str
            Required when ``decision == "reject"``.  The objection
            message returned to the Detective.

        Returns
        -------
        Suspect
            The updated suspect instance.

        Raises
        ------
        PermissionError
            If ``sergeant_user`` lacks ``CAN_APPROVE_SUSPECT``.
        django.core.exceptions.ValidationError
            - If the suspect is not in ``pending`` approval status.
            - If ``decision == "reject"`` but no message provided.

        Implementation Contract
        -----------------------
        1. **Permission check:**
           ``if not sergeant_user.has_perm(
               f"suspects.{SuspectsPerms.CAN_APPROVE_SUSPECT}"
           ):``
           ``    raise PermissionError("Only a Sergeant can approve suspects.")``
        2. **Fetch suspect:**
           ``suspect = Suspect.objects.select_related("case").get(pk=suspect_id)``
        3. **Guard — already processed:**
           ``if suspect.sergeant_approval_status != "pending":``
           ``    raise ValidationError("Suspect approval already processed.")``
        4. **Decision processing:**
           a. If ``decision == "approve"``:
              - ``suspect.sergeant_approval_status = "approved"``
              - ``suspect.approved_by_sergeant = sergeant_user``
              - Dispatch notification to the Detective: "Suspect approved,
                arrest warrant may now be issued."
           b. If ``decision == "reject"``:
              - ``suspect.sergeant_approval_status = "rejected"``
              - ``suspect.approved_by_sergeant = sergeant_user``
              - ``suspect.sergeant_rejection_message = rejection_message``
              - Dispatch notification to the Detective with the rejection
                message (project-doc §4.4: "the objection is returned as
                a message to the Detective").
        5. **Save:**
           ``suspect.save(update_fields=[
               "sergeant_approval_status", "approved_by_sergeant",
               "sergeant_rejection_message", "updated_at"
           ])``
        6. Return ``suspect``.
        """
        if not sergeant_user.has_perm(
            f"suspects.{SuspectsPerms.CAN_APPROVE_SUSPECT}"
        ):
            raise PermissionDenied(
                "Only a Sergeant (or higher) can approve/reject suspects."
            )

        try:
            suspect = Suspect.objects.select_related(
                "case", "identified_by",
            ).get(pk=suspect_id)
        except Suspect.DoesNotExist:
            raise NotFound(f"Suspect with id {suspect_id} not found.")

        if suspect.sergeant_approval_status != "pending":
            raise DomainError(
                "Suspect approval has already been processed."
            )

        detective = suspect.identified_by

        if decision == "approve":
            suspect.sergeant_approval_status = "approved"
            suspect.approved_by_sergeant = sergeant_user
            suspect.save(update_fields=[
                "sergeant_approval_status",
                "approved_by_sergeant",
                "updated_at",
            ])
            NotificationService.create(
                actor=sergeant_user,
                recipients=detective,
                event_type="suspect_approved",
                payload={
                    "suspect_id": suspect.id,
                    "suspect_name": suspect.full_name,
                    "case_id": suspect.case_id,
                    "case_title": suspect.case.title,
                    "approved_by": sergeant_user.get_full_name(),
                },
                related_object=suspect,
            )
        elif decision == "reject":
            if not rejection_message.strip():
                raise DomainError(
                    "A rejection message is required when rejecting a suspect."
                )
            suspect.sergeant_approval_status = "rejected"
            suspect.approved_by_sergeant = sergeant_user
            suspect.sergeant_rejection_message = rejection_message
            suspect.save(update_fields=[
                "sergeant_approval_status",
                "approved_by_sergeant",
                "sergeant_rejection_message",
                "updated_at",
            ])
            NotificationService.create(
                actor=sergeant_user,
                recipients=detective,
                event_type="suspect_rejected",
                payload={
                    "suspect_id": suspect.id,
                    "suspect_name": suspect.full_name,
                    "case_id": suspect.case_id,
                    "case_title": suspect.case.title,
                    "rejected_by": sergeant_user.get_full_name(),
                    "rejection_message": rejection_message,
                },
                related_object=suspect,
            )

        return suspect

    @staticmethod
    @transaction.atomic
    def issue_arrest_warrant(
        suspect_id: int,
        issuing_sergeant: Any,
        warrant_reason: str,
        priority: str = "normal",
    ) -> Suspect:
        """
        Issue an arrest warrant for an approved suspect.

        This is performed by the Sergeant (project-doc §3.1.5)
        after approving the suspect identification.

        Parameters
        ----------
        suspect_id : int
            PK of the suspect.
        issuing_sergeant : User
            The Sergeant issuing the warrant.  Must have
            ``CAN_ISSUE_ARREST_WARRANT`` permission.
        warrant_reason : str
            Justification for the warrant.
        priority : str
            ``"normal"``, ``"high"``, or ``"critical"``.

        Returns
        -------
        Suspect
            The suspect instance (unchanged status — still WANTED,
            but warrant is now on record).

        Raises
        ------
        PermissionError
            If ``issuing_sergeant`` lacks ``CAN_ISSUE_ARREST_WARRANT``.
        django.core.exceptions.ValidationError
            - If suspect is not approved (``sergeant_approval_status != "approved"``).
            - If suspect is not in ``WANTED`` status.
            - If a warrant has already been issued (prevent duplicates).

        Implementation Contract
        -----------------------
        1. **Permission check:**
           Assert ``CAN_ISSUE_ARREST_WARRANT``.
        2. **Fetch suspect** with ``select_related("case")``.
        3. **Guards:**
           a. ``sergeant_approval_status == "approved"``
           b. ``status == SuspectStatus.WANTED``
           c. No duplicate active warrant (check an audit mechanism or
              a flag on the suspect — for the structural draft, assume
              a ``warrant_issued`` flag or similar will be added).
        4. **Record the warrant:**
           Store ``warrant_reason``, ``priority``, ``warrant_issued_at``,
           and ``warrant_issued_by`` on the suspect (or in an audit log).
           For the structural draft, note this may require extending
           the ``Suspect`` model or creating a ``Warrant`` model.
        5. **Notification:**
           Notify the Detective that a warrant has been issued and
           arrest can proceed.
        6. Return ``suspect``.

        Notes
        -----
        The current ``Suspect`` model does not have dedicated warrant
        fields.  In the full implementation, either:
        a) Add ``warrant_issued``, ``warrant_reason``, ``warrant_priority``,
           ``warrant_issued_at``, ``warrant_issued_by`` fields to ``Suspect``.
        b) Create a separate ``ArrestWarrant`` model for full auditing.
        For this structural draft, the method signature and contract
        are defined; the storage mechanism is deferred.
        """
        # ── Permission check ────────────────────────────────────────
        if not issuing_sergeant.has_perm(
            f"suspects.{SuspectsPerms.CAN_ISSUE_ARREST_WARRANT}"
        ):
            raise PermissionDenied(
                "Only a Sergeant (or higher) can issue arrest warrants."
            )

        # ── Fetch suspect ───────────────────────────────────────────
        try:
            suspect = Suspect.objects.select_related(
                "case", "identified_by",
            ).get(pk=suspect_id)
        except Suspect.DoesNotExist:
            raise NotFound(f"Suspect with id {suspect_id} not found.")

        # ── Guards ──────────────────────────────────────────────────
        if suspect.sergeant_approval_status != "approved":
            raise DomainError(
                "Suspect must be approved by a sergeant before a "
                "warrant can be issued."
            )

        if suspect.status != SuspectStatus.WANTED:
            raise InvalidTransition(
                current=suspect.status,
                target=SuspectStatus.WANTED,
                reason="Warrant can only be issued for suspects in 'Wanted' status.",
            )

        # Prevent duplicate active warrants
        if suspect.warrants.filter(
            status=Warrant.WarrantStatus.ACTIVE,
        ).exists():
            raise DomainError(
                "An active warrant already exists for this suspect."
            )

        # ── Create warrant record ───────────────────────────────────
        Warrant.objects.create(
            suspect=suspect,
            reason=warrant_reason,
            issued_by=issuing_sergeant,
            status=Warrant.WarrantStatus.ACTIVE,
            priority=priority,
        )

        # ── Notification to Detective ───────────────────────────────
        detective = suspect.identified_by
        if detective:
            NotificationService.create(
                actor=issuing_sergeant,
                recipients=detective,
                event_type="warrant_issued",
                payload={
                    "suspect_id": suspect.id,
                    "suspect_name": suspect.full_name,
                    "case_id": suspect.case_id,
                    "case_title": suspect.case.title,
                    "issued_by": issuing_sergeant.get_full_name(),
                    "priority": priority,
                },
                related_object=suspect,
            )

        logger.info(
            "Warrant issued for suspect %s (pk=%d) by %s",
            suspect.full_name, suspect.id, issuing_sergeant,
        )
        return suspect

    @staticmethod
    @transaction.atomic
    def execute_arrest(
        suspect_id: int,
        arresting_officer: Any,
        arrest_location: str,
        arrest_notes: str = "",
        warrant_override_justification: str = "",
    ) -> Suspect:
        """
        Execute the arrest of a suspect — transition global status to
        ``ARRESTED`` (In Custody).

        This is the **most critical workflow method** in the suspects app.
        It enforces strict validation before allowing the status transition.

        Parameters
        ----------
        suspect_id : int
            PK of the suspect to arrest.
        arresting_officer : User
            The officer performing the arrest.  Must have
            ``CAN_ISSUE_ARREST_WARRANT`` permission (Sergeant level
            or above).
        arrest_location : str
            Physical location where the arrest took place.
        arrest_notes : str
            Additional context about the arrest circumstances.
        warrant_override_justification : str
            If no active warrant exists, this must provide a valid
            justification (e.g., caught in the act).  If empty and
            no warrant exists, the arrest is REJECTED.

        Returns
        -------
        Suspect
            The updated suspect with ``status = ARRESTED``.

        Raises
        ------
        PermissionError
            If ``arresting_officer`` lacks the required permission.
        django.core.exceptions.ValidationError
            - If suspect is not in ``WANTED`` status.
            - If suspect is not approved by a sergeant.
            - If no active warrant exists AND no override justification
              is provided.

        Implementation Contract
        -----------------------
        1. **Permission check:**
           ``if not arresting_officer.has_perm(
               f"suspects.{SuspectsPerms.CAN_ISSUE_ARREST_WARRANT}"
           ):``
           ``    raise PermissionError("Insufficient permissions for arrest.")``

        2. **Fetch suspect:**
           ``suspect = Suspect.objects.select_related("case").get(pk=suspect_id)``

        3. **Status guard:**
           ``if suspect.status != SuspectStatus.WANTED:``
           ``    raise ValidationError(
                   f"Cannot arrest suspect in '{suspect.get_status_display()}' status."
               )``

        4. **Approval guard:**
           ``if suspect.sergeant_approval_status != "approved":``
           ``    raise ValidationError(
                   "Suspect must be approved by a sergeant before arrest."
               )``

        5. **Warrant validation:**
           a. Check if an active warrant exists for this suspect
              (via warrant flag/model — see ``issue_arrest_warrant`` notes).
           b. If NO warrant exists:
              - ``if not warrant_override_justification.strip():``
              - ``    raise ValidationError(
                       "No active warrant. Provide warrant_override_justification."
                   )``
              - If override IS provided, log the warrantless arrest
                with the justification in the audit trail.

        6. **Execute transition:**
           ``suspect.status = SuspectStatus.ARRESTED``
           ``suspect.save(update_fields=["status", "updated_at"])``

        7. **Audit log:**
           Record the arrest event with:
           - ``arresting_officer``
           - ``arrest_location``
           - ``arrest_notes``
           - ``timestamp = timezone.now()``
           - ``warrant_used`` (bool) and ``warrant_override_justification``
           This can be stored in a dedicated ``AuditLog`` model or
           appended to the suspect's description/notes field.

        8. **Notifications:**
           - Notify the Detective assigned to the case.
           - Notify the Captain that a suspect has been arrested.
           - If critical case: notify the Police Chief as well.

        9. Return ``suspect``.

        Security Notes
        --------------
        - Double permission check (view + service) for defence in depth.
        - Warrant validation prevents arbitrary arrests.
        - Override justification creates an auditable paper trail.
        - Status guard prevents double-arrest.
        """
        # ── Permission check ────────────────────────────────────────
        if not arresting_officer.has_perm(
            f"suspects.{SuspectsPerms.CAN_ISSUE_ARREST_WARRANT}"
        ):
            raise PermissionDenied(
                "Insufficient permissions to execute an arrest."
            )

        # ── Fetch suspect with lock ─────────────────────────────────
        try:
            suspect = Suspect.objects.select_for_update().select_related(
                "case", "identified_by",
            ).get(pk=suspect_id)
        except Suspect.DoesNotExist:
            raise NotFound(f"Suspect with id {suspect_id} not found.")

        # ── Status guard ────────────────────────────────────────────
        if suspect.status != SuspectStatus.WANTED:
            raise InvalidTransition(
                current=suspect.status,
                target=SuspectStatus.ARRESTED,
                reason=(
                    f"Cannot arrest suspect in "
                    f"'{suspect.get_status_display()}' status."
                ),
            )

        # ── Approval guard ──────────────────────────────────────────
        if suspect.sergeant_approval_status != "approved":
            raise DomainError(
                "Suspect must be approved by a sergeant before arrest."
            )

        # ── Warrant validation ──────────────────────────────────────
        active_warrant = suspect.warrants.filter(
            status=Warrant.WarrantStatus.ACTIVE,
        ).first()

        if not active_warrant:
            if not warrant_override_justification.strip():
                raise DomainError(
                    "No active warrant exists for this suspect. "
                    "Provide warrant_override_justification for a "
                    "warrantless arrest."
                )
            warrant_used = False
        else:
            # Mark the warrant as executed
            active_warrant.status = Warrant.WarrantStatus.EXECUTED
            active_warrant.save(update_fields=["status", "updated_at"])
            warrant_used = True

        # ── Execute transition ──────────────────────────────────────
        old_status = suspect.status
        suspect.status = SuspectStatus.ARRESTED
        suspect.arrested_at = timezone.now()
        suspect.save(update_fields=["status", "arrested_at", "updated_at"])

        # ── Audit log ──────────────────────────────────────────────
        notes_parts = [f"Arrest location: {arrest_location}"]
        if arrest_notes:
            notes_parts.append(f"Notes: {arrest_notes}")
        if warrant_used:
            notes_parts.append(f"Warrant #{active_warrant.id} executed.")
        else:
            notes_parts.append(
                f"Warrantless arrest — override: "
                f"{warrant_override_justification}"
            )

        SuspectStatusLog.objects.create(
            suspect=suspect,
            from_status=old_status,
            to_status=SuspectStatus.ARRESTED,
            changed_by=arresting_officer,
            notes="\n".join(notes_parts),
        )

        # ── Notifications ──────────────────────────────────────────
        notification_payload = {
            "suspect_id": suspect.id,
            "suspect_name": suspect.full_name,
            "case_id": suspect.case_id,
            "case_title": suspect.case.title,
            "arrested_by": arresting_officer.get_full_name(),
            "arrest_location": arrest_location,
        }

        recipients = []
        detective = suspect.identified_by
        if detective:
            recipients.append(detective)
        sergeant = getattr(suspect.case, "assigned_sergeant", None)
        if sergeant and sergeant != arresting_officer:
            recipients.append(sergeant)

        if recipients:
            NotificationService.create(
                actor=arresting_officer,
                recipients=recipients,
                event_type="suspect_arrested",
                payload=notification_payload,
                related_object=suspect,
            )

        logger.info(
            "Suspect %s (pk=%d) arrested by %s at %s",
            suspect.full_name, suspect.id, arresting_officer,
            arrest_location,
        )
        return suspect

    @staticmethod
    @transaction.atomic
    def transition_status(
        suspect_id: int,
        requesting_user: Any,
        new_status: str,
        reason: str,
    ) -> Suspect:
        """
        Generic status transition for non-arrest state changes.

        Validates that the transition is legal according to the state
        machine and that the user has the appropriate permission.

        Parameters
        ----------
        suspect_id : int
            PK of the suspect.
        requesting_user : User
            The user requesting the transition.
        new_status : str
            Target ``SuspectStatus`` value.
        reason : str
            Justification for the transition.

        Returns
        -------
        Suspect
            The updated suspect.

        Raises
        ------
        PermissionError
            If the user lacks the permission required for the
            specific transition.
        django.core.exceptions.ValidationError
            If the transition is not allowed from the current status.

        Allowed Transitions & Required Permissions
        -------------------------------------------
        ::

            ARRESTED → UNDER_INTERROGATION  (CAN_CONDUCT_INTERROGATION)
            UNDER_INTERROGATION → UNDER_TRIAL  (CAN_RENDER_VERDICT)
            UNDER_TRIAL → CONVICTED  (CAN_JUDGE_TRIAL)
            UNDER_TRIAL → ACQUITTED  (CAN_JUDGE_TRIAL)
            ARRESTED → RELEASED     (CAN_SET_BAIL_AMOUNT — bail posted)
            CONVICTED → RELEASED    (CAN_SET_BAIL_AMOUNT — bail for L3)

        Implementation Contract
        -----------------------
        1. Fetch suspect.
        2. Validate the transition is legal (define ``_ALLOWED_TRANSITIONS``
           dict mapping ``current_status → set(allowed_targets)``).
        3. Check the user has the permission mapped to this transition.
        4. ``suspect.status = new_status``
        5. ``suspect.save(update_fields=["status", "updated_at"])``
        6. Record audit log entry with ``reason``.
        7. Return ``suspect``.
        """
        # ── Fetch suspect with row lock ─────────────────────────────
        try:
            suspect = Suspect.objects.select_for_update().select_related(
                "case",
            ).get(pk=suspect_id)
        except Suspect.DoesNotExist:
            raise NotFound(f"Suspect with id {suspect_id} not found.")

        current = suspect.status

        # ── Validate transition is allowed ──────────────────────────
        allowed_targets = ArrestAndWarrantService._ALLOWED_TRANSITIONS.get(
            current, set(),
        )
        if new_status not in allowed_targets:
            raise InvalidTransition(
                current=current,
                target=new_status,
                reason=(
                    f"Transition from '{suspect.get_status_display()}' "
                    f"to '{new_status}' is not allowed."
                ),
            )

        # ── Permission check for specific transition ────────────────
        perm_entry = ArrestAndWarrantService._TRANSITION_PERMISSION_MAP.get(
            (current, new_status),
        )
        if perm_entry:
            app_label, perm_codename = perm_entry
            if not requesting_user.has_perm(
                f"{app_label}.{perm_codename}"
            ):
                raise PermissionDenied(
                    f"You do not have permission for the transition "
                    f"'{current}' → '{new_status}'."
                )

        # ── Execute transition ──────────────────────────────────────
        old_status = suspect.status
        suspect.status = new_status
        suspect.save(update_fields=["status", "updated_at"])

        # ── Audit log ──────────────────────────────────────────────
        SuspectStatusLog.objects.create(
            suspect=suspect,
            from_status=old_status,
            to_status=new_status,
            changed_by=requesting_user,
            notes=reason,
        )

        logger.info(
            "Suspect %s (pk=%d) transitioned %s → %s by %s",
            suspect.full_name, suspect.id, old_status, new_status,
            requesting_user,
        )
        return suspect

    #: Maps each (current_status, new_status) pair to the required
    #: permission as (app_label, codename).
    _TRANSITION_PERMISSION_MAP: dict[tuple[str, str], tuple[str, str]] = {
        (SuspectStatus.ARRESTED, SuspectStatus.UNDER_INTERROGATION):
            ("suspects", SuspectsPerms.CAN_CONDUCT_INTERROGATION),
        (SuspectStatus.UNDER_INTERROGATION, SuspectStatus.PENDING_CAPTAIN_VERDICT):
            ("suspects", SuspectsPerms.CAN_SCORE_GUILT),
        (SuspectStatus.PENDING_CAPTAIN_VERDICT, SuspectStatus.PENDING_CHIEF_APPROVAL):
            ("suspects", SuspectsPerms.CAN_RENDER_VERDICT),
        (SuspectStatus.PENDING_CAPTAIN_VERDICT, SuspectStatus.UNDER_TRIAL):
            ("suspects", SuspectsPerms.CAN_RENDER_VERDICT),
        (SuspectStatus.PENDING_CHIEF_APPROVAL, SuspectStatus.UNDER_TRIAL):
            ("cases", CasesPerms.CAN_APPROVE_CRITICAL_CASE),
        (SuspectStatus.PENDING_CHIEF_APPROVAL, SuspectStatus.UNDER_INTERROGATION):
            ("cases", CasesPerms.CAN_APPROVE_CRITICAL_CASE),
        (SuspectStatus.UNDER_TRIAL, SuspectStatus.CONVICTED):
            ("suspects", SuspectsPerms.CAN_JUDGE_TRIAL),
        (SuspectStatus.UNDER_TRIAL, SuspectStatus.ACQUITTED):
            ("suspects", SuspectsPerms.CAN_JUDGE_TRIAL),
        (SuspectStatus.ARRESTED, SuspectStatus.RELEASED):
            ("suspects", SuspectsPerms.CAN_SET_BAIL_AMOUNT),
        (SuspectStatus.CONVICTED, SuspectStatus.RELEASED):
            ("suspects", SuspectsPerms.CAN_SET_BAIL_AMOUNT),
    }

    #: Legal transitions in the suspect lifecycle state machine.
    _ALLOWED_TRANSITIONS: dict[str, set[str]] = {
        SuspectStatus.WANTED: {SuspectStatus.ARRESTED},
        SuspectStatus.ARRESTED: {
            SuspectStatus.UNDER_INTERROGATION,
            SuspectStatus.RELEASED,
        },
        SuspectStatus.UNDER_INTERROGATION: {
            SuspectStatus.PENDING_CAPTAIN_VERDICT,
        },
        SuspectStatus.PENDING_CAPTAIN_VERDICT: {
            SuspectStatus.UNDER_TRIAL,
            SuspectStatus.PENDING_CHIEF_APPROVAL,
        },
        SuspectStatus.PENDING_CHIEF_APPROVAL: {
            SuspectStatus.UNDER_TRIAL,
            SuspectStatus.UNDER_INTERROGATION,
        },
        SuspectStatus.UNDER_TRIAL: {
            SuspectStatus.CONVICTED,
            SuspectStatus.ACQUITTED,
        },
        SuspectStatus.CONVICTED: {SuspectStatus.RELEASED},
        SuspectStatus.ACQUITTED: set(),
        SuspectStatus.RELEASED: set(),
    }


# ═══════════════════════════════════════════════════════════════════
#  Interrogation Service
# ═══════════════════════════════════════════════════════════════════


class InterrogationService:
    """
    Manages interrogation session creation and retrieval.

    An interrogation is conducted jointly by the Detective and Sergeant
    after a suspect has been arrested (project-doc §4.5).  Both officers
    assign a guilt probability score from 1 to 10 which is forwarded
    to the Captain.
    """

    @staticmethod
    def get_interrogations_for_suspect(
        suspect_id: int,
        requesting_user: Any,
    ) -> QuerySet[Interrogation]:
        """
        Return all interrogation sessions for a given suspect.

        Role-based scoping:
        - Detective: sees interrogations on cases assigned to them.
        - Sergeant: sees interrogations on cases they supervise.
        - Captain / Chief / Admin / Judge: unrestricted.
        """
        qs = Interrogation.objects.filter(
            suspect_id=suspect_id,
        ).select_related(
            "detective", "sergeant", "suspect", "case",
        ).order_by("-created_at")

        user = requesting_user
        role_name = ""
        if hasattr(user, "role") and user.role:
            role_name = user.role.name.lower()

        high_level_roles = {
            "captain", "police chief", "admin",
            "system administrator", "judge",
        }
        if role_name not in high_level_roles and not user.is_superuser:
            if role_name == "detective":
                qs = qs.filter(
                    Q(case__assigned_detective=user) | Q(detective=user),
                )
            elif role_name == "sergeant":
                qs = qs.filter(
                    Q(case__assigned_sergeant=user) | Q(sergeant=user),
                )
            else:
                qs = qs.filter(
                    Q(case__created_by=user)
                    | Q(case__complainants__user=user),
                ).distinct()

        return qs

    @staticmethod
    def get_interrogation_detail(
        interrogation_id: int,
    ) -> Interrogation:
        """Retrieve a single interrogation by PK with related data."""
        try:
            return Interrogation.objects.select_related(
                "detective", "sergeant", "suspect", "case",
            ).get(pk=interrogation_id)
        except Interrogation.DoesNotExist:
            raise NotFound(
                f"Interrogation with id {interrogation_id} not found.",
            )

    @staticmethod
    def list_interrogations(
        requesting_user: Any,
        filters: dict[str, Any] | None = None,
    ) -> QuerySet[Interrogation]:
        """
        Return all interrogations visible to the requesting user,
        with optional filters (case, suspect).
        """
        qs = Interrogation.objects.select_related(
            "detective", "sergeant", "suspect", "case",
        ).order_by("-created_at")

        user = requesting_user
        role_name = ""
        if hasattr(user, "role") and user.role:
            role_name = user.role.name.lower()

        high_level_roles = {
            "captain", "police chief", "admin",
            "system administrator", "judge",
        }
        if role_name not in high_level_roles and not user.is_superuser:
            if role_name == "detective":
                qs = qs.filter(
                    Q(case__assigned_detective=user) | Q(detective=user),
                )
            elif role_name == "sergeant":
                qs = qs.filter(
                    Q(case__assigned_sergeant=user) | Q(sergeant=user),
                )
            else:
                qs = qs.filter(
                    Q(case__created_by=user)
                    | Q(case__complainants__user=user),
                ).distinct()

        if filters:
            if "case" in filters:
                qs = qs.filter(case_id=filters["case"])
            if "suspect" in filters:
                qs = qs.filter(suspect_id=filters["suspect"])

        return qs

    @staticmethod
    @transaction.atomic
    def create_interrogation(
        suspect_id: int,
        validated_data: dict[str, Any],
        requesting_user: Any,
    ) -> Interrogation:
        """
        Create a new interrogation session for a suspect.

        Validates:
        - Actor has CAN_CONDUCT_INTERROGATION permission.
        - Suspect is in ARRESTED or UNDER_INTERROGATION status.
        - Scores are integers 1-10 (also enforced in serializer).

        Transitions suspect to UNDER_INTERROGATION if currently ARRESTED.
        """
        # ── Permission check ────────────────────────────────────────
        if not requesting_user.has_perm(
            f"suspects.{SuspectsPerms.CAN_CONDUCT_INTERROGATION}"
        ):
            raise PermissionDenied(
                "You do not have permission to conduct interrogations."
            )

        # ── Fetch suspect with lock ─────────────────────────────────
        try:
            suspect = Suspect.objects.select_for_update().select_related(
                "case",
            ).get(pk=suspect_id)
        except Suspect.DoesNotExist:
            raise NotFound(f"Suspect with id {suspect_id} not found.")

        # ── Status guard ────────────────────────────────────────────
        eligible_statuses = {
            SuspectStatus.ARRESTED,
            SuspectStatus.UNDER_INTERROGATION,
        }
        if suspect.status not in eligible_statuses:
            raise DomainError(
                f"Cannot interrogate a suspect in "
                f"'{suspect.get_status_display()}' status. "
                f"Suspect must be Arrested or Under Interrogation."
            )

        # ── Score validation (defence-in-depth) ─────────────────────
        det_score = validated_data.get("detective_guilt_score")
        sgt_score = validated_data.get("sergeant_guilt_score")
        for label, score in [
            ("detective_guilt_score", det_score),
            ("sergeant_guilt_score", sgt_score),
        ]:
            if score is not None and not (1 <= score <= 10):
                raise DomainError(
                    f"{label} must be an integer between 1 and 10 inclusive."
                )

        # ── Transition to UNDER_INTERROGATION if ARRESTED ───────────
        if suspect.status == SuspectStatus.ARRESTED:
            old_status = suspect.status
            suspect.status = SuspectStatus.UNDER_INTERROGATION
            suspect.save(update_fields=["status", "updated_at"])
            SuspectStatusLog.objects.create(
                suspect=suspect,
                from_status=old_status,
                to_status=SuspectStatus.UNDER_INTERROGATION,
                changed_by=requesting_user,
                notes="Automatic transition upon interrogation creation.",
            )

        # ── Resolve detective and sergeant from case assignment ─────
        case = suspect.case
        detective = case.assigned_detective or requesting_user
        sergeant = case.assigned_sergeant or requesting_user

        # ── Create the interrogation record ─────────────────────────
        interrogation = Interrogation.objects.create(
            suspect=suspect,
            case=case,
            detective=detective,
            sergeant=sergeant,
            detective_guilt_score=validated_data["detective_guilt_score"],
            sergeant_guilt_score=validated_data["sergeant_guilt_score"],
            notes=validated_data.get("notes", ""),
        )

        # ── Notify the Captain with the guilt scores ────────────────
        captain = getattr(case, "assigned_captain", None)
        if captain:
            NotificationService.create(
                actor=requesting_user,
                recipients=captain,
                event_type="interrogation_created",
                payload={
                    "suspect_id": suspect.id,
                    "suspect_name": suspect.full_name,
                    "case_id": case.id,
                    "case_title": case.title,
                    "detective_guilt_score": validated_data["detective_guilt_score"],
                    "sergeant_guilt_score": validated_data["sergeant_guilt_score"],
                    "created_by": requesting_user.get_full_name(),
                },
                related_object=interrogation,
            )

        logger.info(
            "Interrogation created for suspect %s (pk=%d) by %s — "
            "det_score=%d, sgt_score=%d",
            suspect.full_name, suspect.id, requesting_user,
            validated_data["detective_guilt_score"],
            validated_data["sergeant_guilt_score"],
        )
        return interrogation


# ═══════════════════════════════════════════════════════════════════
#  Verdict Service — Captain decision + Chief approval gate
# ═══════════════════════════════════════════════════════════════════


class VerdictService:
    """
    Implements the Captain's final verdict workflow and the mandatory
    Police Chief approval gate for cases with CRITICAL crime level.

    Workflow (project-doc §4.5)
    ----------------------------
    1. After interrogation, scores are sent to the Captain.
    2. Captain gives the final verdict.
    3. If crime_level == CRITICAL → status becomes PENDING_CHIEF_APPROVAL
       and a notification is sent to the Police Chief.
    4. If crime_level != CRITICAL → verdict applied directly and suspect
       moves to UNDER_TRIAL.
    5. Police Chief approves → suspect moves to UNDER_TRIAL.
    6. Police Chief rejects → suspect reverts to UNDER_INTERROGATION.
    """

    @staticmethod
    @transaction.atomic
    def submit_captain_verdict(
        actor: Any,
        suspect_id: int,
        verdict: str,
        notes: str = "",
    ) -> Suspect:
        """
        Captain submits their verdict on a suspect after reviewing
        interrogation scores and evidence.

        Parameters
        ----------
        actor : User
            Must be a Captain (have CAN_RENDER_VERDICT permission).
        suspect_id : int
            PK of the suspect.
        verdict : str
            ``"guilty"`` or ``"innocent"`` — the Captain's assessment.
        notes : str
            Captain's notes justifying the decision.

        Returns
        -------
        Suspect
            The updated suspect instance.
        """
        # ── Permission check: must be Captain ───────────────────────
        if not actor.has_perm(
            f"suspects.{SuspectsPerms.CAN_RENDER_VERDICT}"
        ):
            raise PermissionDenied(
                "Only a Captain (or higher) can render a verdict."
            )

        role_name = ""
        if hasattr(actor, "role") and actor.role:
            role_name = actor.role.name.lower()
        if role_name not in ("captain", "police chief", "system administrator") \
                and not actor.is_superuser:
            raise PermissionDenied(
                "Only a Captain can submit a verdict at this stage."
            )

        # ── Fetch suspect with row lock ─────────────────────────────
        try:
            suspect = Suspect.objects.select_for_update().select_related(
                "case", "identified_by",
            ).get(pk=suspect_id)
        except Suspect.DoesNotExist:
            raise NotFound(f"Suspect with id {suspect_id} not found.")

        # ── Status guard ────────────────────────────────────────────
        eligible = {
            SuspectStatus.UNDER_INTERROGATION,
            SuspectStatus.PENDING_CAPTAIN_VERDICT,
        }
        if suspect.status not in eligible:
            raise DomainError(
                f"Cannot render verdict for suspect in "
                f"'{suspect.get_status_display()}' status. "
                f"Suspect must be Under Interrogation or "
                f"Pending Captain Verdict."
            )

        case = suspect.case

        # ── Import CrimeLevel here to avoid top-level circular import
        from cases.models import CrimeLevel

        old_status = suspect.status

        if case.crime_level == CrimeLevel.CRITICAL:
            # CRITICAL: Captain's verdict requires Chief approval
            suspect.status = SuspectStatus.PENDING_CHIEF_APPROVAL
            suspect.save(update_fields=["status", "updated_at"])

            SuspectStatusLog.objects.create(
                suspect=suspect,
                from_status=old_status,
                to_status=SuspectStatus.PENDING_CHIEF_APPROVAL,
                changed_by=actor,
                notes=(
                    f"Captain verdict: {verdict}. "
                    f"Awaiting Police Chief approval (CRITICAL case). "
                    f"Notes: {notes}"
                ),
            )

            # Notify the Police Chief
            from django.contrib.auth import get_user_model
            User = get_user_model()
            chiefs = User.objects.filter(
                role__name__iexact="Police Chief",
                is_active=True,
            )
            if chiefs.exists():
                NotificationService.create(
                    actor=actor,
                    recipients=list(chiefs),
                    event_type="chief_approval_required",
                    payload={
                        "suspect_id": suspect.id,
                        "suspect_name": suspect.full_name,
                        "case_id": case.id,
                        "case_title": case.title,
                        "captain_verdict": verdict,
                        "captain_notes": notes,
                        "captain_name": actor.get_full_name(),
                    },
                    related_object=suspect,
                )

            logger.info(
                "Captain %s submitted verdict '%s' for suspect %s "
                "(pk=%d) on CRITICAL case — awaiting Chief approval",
                actor, verdict, suspect.full_name, suspect.id,
            )
        else:
            # Non-CRITICAL: apply verdict directly → UNDER_TRIAL
            suspect.status = SuspectStatus.UNDER_TRIAL
            suspect.save(update_fields=["status", "updated_at"])

            SuspectStatusLog.objects.create(
                suspect=suspect,
                from_status=old_status,
                to_status=SuspectStatus.UNDER_TRIAL,
                changed_by=actor,
                notes=(
                    f"Captain verdict: {verdict}. "
                    f"Forwarded to judiciary. Notes: {notes}"
                ),
            )

            # Notify detective and sergeant
            recipients = []
            detective = suspect.identified_by
            if detective:
                recipients.append(detective)
            sergeant = getattr(case, "assigned_sergeant", None)
            if sergeant:
                recipients.append(sergeant)

            if recipients:
                NotificationService.create(
                    actor=actor,
                    recipients=recipients,
                    event_type="captain_verdict_applied",
                    payload={
                        "suspect_id": suspect.id,
                        "suspect_name": suspect.full_name,
                        "case_id": case.id,
                        "case_title": case.title,
                        "verdict": verdict,
                        "notes": notes,
                    },
                    related_object=suspect,
                )

            logger.info(
                "Captain %s submitted verdict '%s' for suspect %s "
                "(pk=%d) — forwarded to trial",
                actor, verdict, suspect.full_name, suspect.id,
            )

        return suspect

    @staticmethod
    @transaction.atomic
    def process_chief_approval(
        actor: Any,
        suspect_id: int,
        decision: str,
        notes: str = "",
    ) -> Suspect:
        """
        Police Chief approves or rejects the Captain's verdict for
        a CRITICAL crime case.

        Parameters
        ----------
        actor : User
            Must be a Police Chief (have CAN_APPROVE_CRITICAL_CASE).
        suspect_id : int
            PK of the suspect.
        decision : str
            ``"approve"`` or ``"reject"``.
        notes : str
            Chief's notes/reason.

        Returns
        -------
        Suspect
            The updated suspect instance.
        """
        # ── Permission check: must be Police Chief ──────────────────
        if not actor.has_perm(
            f"cases.{CasesPerms.CAN_APPROVE_CRITICAL_CASE}"
        ):
            raise PermissionDenied(
                "Only the Police Chief can approve or reject "
                "verdicts for critical cases."
            )

        role_name = ""
        if hasattr(actor, "role") and actor.role:
            role_name = actor.role.name.lower()
        if role_name not in ("police chief", "system administrator") \
                and not actor.is_superuser:
            raise PermissionDenied(
                "Only the Police Chief can process this approval."
            )

        # ── Fetch suspect with row lock ─────────────────────────────
        try:
            suspect = Suspect.objects.select_for_update().select_related(
                "case", "identified_by",
            ).get(pk=suspect_id)
        except Suspect.DoesNotExist:
            raise NotFound(f"Suspect with id {suspect_id} not found.")

        # ── Status guard ────────────────────────────────────────────
        if suspect.status != SuspectStatus.PENDING_CHIEF_APPROVAL:
            raise DomainError(
                f"Suspect is not pending Chief approval. "
                f"Current status: '{suspect.get_status_display()}'."
            )

        case = suspect.case
        old_status = suspect.status

        if decision == "approve":
            suspect.status = SuspectStatus.UNDER_TRIAL
            suspect.save(update_fields=["status", "updated_at"])

            SuspectStatusLog.objects.create(
                suspect=suspect,
                from_status=old_status,
                to_status=SuspectStatus.UNDER_TRIAL,
                changed_by=actor,
                notes=(
                    f"Police Chief approved. "
                    f"Forwarded to judiciary. Notes: {notes}"
                ),
            )

            # Notify Captain and Detective
            recipients = []
            captain = getattr(case, "assigned_captain", None)
            if captain:
                recipients.append(captain)
            detective = suspect.identified_by
            if detective:
                recipients.append(detective)

            if recipients:
                NotificationService.create(
                    actor=actor,
                    recipients=recipients,
                    event_type="chief_verdict_approved",
                    payload={
                        "suspect_id": suspect.id,
                        "suspect_name": suspect.full_name,
                        "case_id": case.id,
                        "case_title": case.title,
                        "notes": notes,
                    },
                    related_object=suspect,
                )

            logger.info(
                "Police Chief %s approved verdict for suspect %s "
                "(pk=%d) — forwarded to trial",
                actor, suspect.full_name, suspect.id,
            )

        elif decision == "reject":
            if not notes.strip():
                raise DomainError(
                    "Notes are required when rejecting a verdict."
                )

            suspect.status = SuspectStatus.UNDER_INTERROGATION
            suspect.save(update_fields=["status", "updated_at"])

            SuspectStatusLog.objects.create(
                suspect=suspect,
                from_status=old_status,
                to_status=SuspectStatus.UNDER_INTERROGATION,
                changed_by=actor,
                notes=(
                    f"Police Chief rejected verdict. "
                    f"Reverted to interrogation. Notes: {notes}"
                ),
            )

            # Notify Captain and Detective
            recipients = []
            captain = getattr(case, "assigned_captain", None)
            if captain:
                recipients.append(captain)
            detective = suspect.identified_by
            if detective:
                recipients.append(detective)

            if recipients:
                NotificationService.create(
                    actor=actor,
                    recipients=recipients,
                    event_type="chief_verdict_rejected",
                    payload={
                        "suspect_id": suspect.id,
                        "suspect_name": suspect.full_name,
                        "case_id": case.id,
                        "case_title": case.title,
                        "rejection_notes": notes,
                    },
                    related_object=suspect,
                )

            logger.info(
                "Police Chief %s rejected verdict for suspect %s "
                "(pk=%d) — reverted to interrogation",
                actor, suspect.full_name, suspect.id,
            )
        else:
            raise DomainError(
                f"Invalid decision '{decision}'. "
                f"Must be 'approve' or 'reject'."
            )

        return suspect


# ═══════════════════════════════════════════════════════════════════
#  Trial Service
# ═══════════════════════════════════════════════════════════════════


class TrialService:
    """
    Manages trial record creation and retrieval.

    A trial occurs after the Captain (or Police Chief for critical cases)
    forwards the case to the judiciary (project-doc §4.6).  The Judge
    records the final verdict and, if guilty, the punishment.
    """

    #: Roles with unrestricted trial visibility.
    _HIGH_LEVEL_ROLES: frozenset[str] = frozenset({
        "captain", "police chief", "admin",
        "system administrator", "judge",
    })

    @staticmethod
    def get_trials_for_suspect(
        suspect_id: int,
        requesting_user: Any,
    ) -> QuerySet[Trial]:
        """
        Return all trial records for a given suspect, scoped by the
        requesting user's role.
        """
        return Trial.objects.filter(
            suspect_id=suspect_id,
        ).select_related(
            "judge", "suspect", "case",
        ).order_by("-created_at")

    @classmethod
    def list_trials(
        cls,
        requesting_user: Any,
        filters: dict[str, Any] | None = None,
    ) -> QuerySet[Trial]:
        """
        Return all trials visible to the requesting user, with
        optional filters (case, suspect, verdict).
        """
        qs = Trial.objects.select_related(
            "judge", "suspect", "case",
        ).order_by("-created_at")

        user = requesting_user
        role_name = ""
        if hasattr(user, "role") and user.role:
            role_name = user.role.name.lower()

        if role_name not in cls._HIGH_LEVEL_ROLES and not user.is_superuser:
            if role_name == "detective":
                qs = qs.filter(
                    Q(case__assigned_detective=user)
                    | Q(suspect__identified_by=user),
                )
            elif role_name == "sergeant":
                qs = qs.filter(
                    Q(case__assigned_sergeant=user),
                )
            else:
                # Base users / complainants — see only trials on cases
                # they are associated with.
                qs = qs.filter(
                    Q(case__created_by=user)
                    | Q(case__complainants__user=user),
                ).distinct()

        if filters:
            if "case" in filters:
                qs = qs.filter(case_id=filters["case"])
            if "suspect" in filters:
                qs = qs.filter(suspect_id=filters["suspect"])
            if "verdict" in filters:
                qs = qs.filter(verdict=filters["verdict"])

        return qs

    @staticmethod
    def get_trial_detail(trial_id: int) -> Trial:
        """Retrieve a single trial by PK with related data loaded."""
        try:
            return Trial.objects.select_related(
                "judge", "suspect", "case",
            ).get(pk=trial_id)
        except Trial.DoesNotExist:
            raise NotFound(f"Trial with id {trial_id} not found.")

    @staticmethod
    @transaction.atomic
    def create_trial(
        suspect_id: int,
        validated_data: dict[str, Any],
        requesting_user: Any,
    ) -> Trial:
        """
        Create a trial record for a suspect.

        Validates:
        - Actor has ``CAN_JUDGE_TRIAL`` permission.
        - Actor is the assigned Judge for the case.
        - Suspect is in ``UNDER_TRIAL`` status.
        - The case has passed Captain/Chief approval gates (i.e.
          the case is in JUDICIARY status or the suspect is
          UNDER_TRIAL).
        - If verdict is guilty, punishment_title and
          punishment_description must be provided.
        - If verdict is innocent, punishment fields must be empty.

        Creates the Trial record, transitions suspect and case
        status, writes audit logs, and dispatches notifications.
        """
        from cases.models import CaseStatus

        # ── Permission check ────────────────────────────────────────
        if not requesting_user.has_perm(
            f"suspects.{SuspectsPerms.CAN_JUDGE_TRIAL}"
        ):
            raise PermissionDenied(
                "Only a Judge can preside over a trial."
            )

        # ── Fetch suspect with row lock ─────────────────────────────
        try:
            suspect = Suspect.objects.select_for_update().select_related(
                "case",
            ).get(pk=suspect_id)
        except Suspect.DoesNotExist:
            raise NotFound(f"Suspect with id {suspect_id} not found.")

        case = suspect.case

        # ── Actor must be the assigned Judge for the case ───────────
        if case.assigned_judge_id != requesting_user.id:
            raise PermissionDenied(
                "You are not the assigned Judge for this case."
            )

        # ── Suspect status guard ────────────────────────────────────
        if suspect.status != SuspectStatus.UNDER_TRIAL:
            raise DomainError(
                f"Cannot record a trial for a suspect in "
                f"'{suspect.get_status_display()}' status. "
                f"Suspect must be Under Trial."
            )

        # ── Verdict / punishment validation ─────────────────────────
        verdict = validated_data["verdict"]

        if verdict == VerdictChoice.GUILTY:
            punishment_title = validated_data.get("punishment_title", "").strip()
            punishment_description = validated_data.get("punishment_description", "").strip()
            if not punishment_title:
                raise DomainError(
                    "Punishment title is required when the verdict is Guilty."
                )
            if not punishment_description:
                raise DomainError(
                    "Punishment description is required when the verdict is Guilty."
                )
        else:
            # Innocent — ensure punishment fields are empty
            validated_data["punishment_title"] = ""
            validated_data["punishment_description"] = ""

        # ── Create the Trial record ─────────────────────────────────
        trial = Trial.objects.create(
            suspect=suspect,
            case=case,
            judge=requesting_user,
            verdict=validated_data["verdict"],
            punishment_title=validated_data.get("punishment_title", ""),
            punishment_description=validated_data.get("punishment_description", ""),
        )

        # ── Transition suspect status ──────────────────────────────
        old_suspect_status = suspect.status
        if verdict == VerdictChoice.GUILTY:
            suspect.status = SuspectStatus.CONVICTED
        else:
            suspect.status = SuspectStatus.ACQUITTED
        suspect.save(update_fields=["status", "updated_at"])

        SuspectStatusLog.objects.create(
            suspect=suspect,
            from_status=old_suspect_status,
            to_status=suspect.status,
            changed_by=requesting_user,
            notes=(
                f"Trial verdict: {verdict}. "
                f"Judge: {requesting_user.get_full_name()}."
            ),
        )

        # ── Transition case status to CLOSED ────────────────────────
        # A case is closed when the judge records the verdict.
        # Only close if all suspects in the case have been resolved.
        all_suspects = Suspect.objects.filter(case=case)
        unresolved = all_suspects.exclude(
            status__in=[
                SuspectStatus.CONVICTED,
                SuspectStatus.ACQUITTED,
                SuspectStatus.RELEASED,
            ],
        )
        if not unresolved.exists():
            old_case_status = case.status
            case.status = CaseStatus.CLOSED
            case.save(update_fields=["status", "updated_at"])

            from cases.models import CaseStatusLog as CaseLog
            CaseLog.objects.create(
                case=case,
                from_status=old_case_status,
                to_status=CaseStatus.CLOSED,
                changed_by=requesting_user,
                message=(
                    f"Case closed after trial. All suspects resolved."
                ),
            )

        # ── Notifications ──────────────────────────────────────────
        notification_recipients = []
        detective = getattr(case, "assigned_detective", None)
        if detective:
            notification_recipients.append(detective)
        captain = getattr(case, "assigned_captain", None)
        if captain:
            notification_recipients.append(captain)

        if notification_recipients:
            NotificationService.create(
                actor=requesting_user,
                recipients=notification_recipients,
                event_type="trial_created",
                payload={
                    "suspect_id": suspect.id,
                    "suspect_name": suspect.full_name,
                    "case_id": case.id,
                    "case_title": case.title,
                    "verdict": verdict,
                    "punishment_title": validated_data.get("punishment_title", ""),
                    "judge_name": requesting_user.get_full_name(),
                },
                related_object=trial,
            )

        logger.info(
            "Trial created for suspect %s (pk=%d) — verdict=%s, "
            "judge=%s, case #%d",
            suspect.full_name, suspect.id, verdict,
            requesting_user, case.id,
        )
        return trial


# ═══════════════════════════════════════════════════════════════════
#  Bounty Tip Service
# ═══════════════════════════════════════════════════════════════════


class BountyTipService:
    """
    Manages the bounty tip lifecycle: submission by citizens, review
    by officers, verification by detectives, and reward lookup.

    Workflow (project-doc §4.8)
    ----------------------------
    1. Citizen submits info → status = PENDING
    2. Police Officer reviews → OFFICER_REVIEWED or REJECTED
    3. Detective verifies → VERIFIED → unique_code generated
    4. Citizen presents unique_code at station to claim reward.
    """

    # 32-byte hex string → 64 characters; cryptographically secure
    _CODE_BYTE_LENGTH: int = 16

    @staticmethod
    def _generate_secure_code() -> str:
        """
        Generate a cryptographically secure, unguessable reward code.

        Uses ``secrets.token_hex`` (backed by ``os.urandom``) which is
        explicitly designed for security tokens and is resistant to
        brute-force / prediction attacks.

        Returns
        -------
        str
            32-character uppercase hex string (128-bit entropy).
        """
        return secrets.token_hex(BountyTipService._CODE_BYTE_LENGTH).upper()

    @staticmethod
    def get_bounty_tips(
        requesting_user: Any,
        filters: dict[str, Any] | None = None,
    ) -> QuerySet[BountyTip]:
        """
        Return bounty tips visible to the requesting user.

        Base users see only their own submitted tips.
        Officers/Detectives see all tips for their cases.
        Admin/Chief see all tips.
        """
        qs = BountyTip.objects.select_related(
            "suspect", "case", "informant", "reviewed_by", "verified_by",
        )

        user = requesting_user
        role_name = ""
        if hasattr(user, "role") and user.role:
            role_name = user.role.name.lower()

        high_level_roles = {
            "captain", "police chief", "admin", "system administrator",
            "judge", "officer", "police officer",
        }
        if role_name not in high_level_roles and not user.is_superuser:
            if role_name == "detective":
                qs = qs.filter(
                    Q(case__assigned_detective=user)
                    | Q(suspect__identified_by=user)
                )
            elif role_name == "sergeant":
                qs = qs.filter(case__assigned_sergeant=user)
            else:
                # Base user / citizen — only their own tips
                qs = qs.filter(informant=user)

        if filters:
            if "status" in filters:
                qs = qs.filter(status=filters["status"])
            if "suspect" in filters:
                qs = qs.filter(suspect_id=filters["suspect"])
            if "case" in filters:
                qs = qs.filter(case_id=filters["case"])

        return qs.order_by("-created_at")

    @staticmethod
    @transaction.atomic
    def submit_tip(
        validated_data: dict[str, Any],
        requesting_user: Any,
    ) -> BountyTip:
        """
        Citizen submits a bounty tip about a suspect or case.

        Creates a new tip with status PENDING. No unique code is
        generated yet.
        """
        suspect = validated_data.get("suspect")
        case = validated_data.get("case")

        if suspect and case and suspect.case_id != case.id:
            raise DomainError(
                "The provided suspect does not belong to the provided case.",
            )

        if suspect:
            if suspect.status != SuspectStatus.WANTED:
                raise DomainError(
                    "Bounty tips can only be submitted for suspects in wanted status.",
                )
            if not suspect.case.is_open:
                raise DomainError(
                    "Bounty tips can only be submitted for suspects linked to open cases.",
                )

        effective_case = case or (suspect.case if suspect else None)
        if effective_case and not effective_case.is_open:
            raise DomainError("Bounty tips can only be submitted for open cases.")

        # If the caller submits only a suspect, persist the suspect's case too.
        if case is None and suspect is not None:
            validated_data = {**validated_data, "case": suspect.case}

        tip = BountyTip.objects.create(
            informant=requesting_user,
            status=BountyTipStatus.PENDING,
            **validated_data,
        )

        logger.info(
            "BountyTip #%d submitted by user=%s", tip.pk, requesting_user,
        )

        # Notify officers that a new tip has been submitted
        NotificationService.create(
            actor=requesting_user,
            recipients=requesting_user,
            event_type="bounty_tip_submitted",
            payload={"tip_id": tip.pk},
            related_object=tip,
        )

        return tip

    @staticmethod
    @transaction.atomic
    def officer_review_tip(
        tip_id: int,
        officer_user: Any,
        decision: str,
        review_notes: str = "",
    ) -> BountyTip:
        """
        Police Officer reviews a bounty tip.

        Validation: Only users with CAN_REVIEW_BOUNTY_TIP permission
        (Officer role or higher admins) can review.

        If decision is 'reject', update status to REJECTED and notify
        the citizen.
        If decision is 'accept', update status to OFFICER_REVIEWED and
        notify the assigned Detective of the related case/suspect.
        """
        perm = f"suspects.{SuspectsPerms.CAN_REVIEW_BOUNTY_TIP}"
        if not officer_user.has_perm(perm):
            raise PermissionDenied(
                "You do not have permission to review bounty tips.",
            )

        try:
            tip = BountyTip.objects.select_related(
                "suspect", "case", "informant",
                "suspect__case__assigned_detective",
            ).select_for_update().get(pk=tip_id)
        except BountyTip.DoesNotExist:
            raise NotFound(f"Bounty tip with id {tip_id} not found.")

        if tip.status != BountyTipStatus.PENDING:
            raise InvalidTransition(
                current=tip.status,
                target="officer_reviewed / rejected",
                reason="Only tips in PENDING status can be reviewed.",
            )

        tip.reviewed_by = officer_user

        if decision == "reject":
            tip.status = BountyTipStatus.REJECTED
            tip.save(update_fields=["status", "reviewed_by", "updated_at"])

            # Notify the citizen that their tip was rejected
            NotificationService.create(
                actor=officer_user,
                recipients=tip.informant,
                event_type="bounty_tip_rejected",
                payload={
                    "tip_id": tip.pk,
                    "review_notes": review_notes,
                },
                related_object=tip,
            )
        else:
            # decision == "accept" → forward to detective
            tip.status = BountyTipStatus.OFFICER_REVIEWED
            tip.save(update_fields=["status", "reviewed_by", "updated_at"])

            # Notify the assigned detective (from case or suspect's case)
            detective = None
            case = tip.case or (tip.suspect.case if tip.suspect else None)
            if case and hasattr(case, "assigned_detective") and case.assigned_detective:
                detective = case.assigned_detective

            if detective:
                NotificationService.create(
                    actor=officer_user,
                    recipients=detective,
                    event_type="bounty_tip_reviewed",
                    payload={
                        "tip_id": tip.pk,
                        "review_notes": review_notes,
                    },
                    related_object=tip,
                )

        logger.info(
            "BountyTip #%d reviewed by officer=%s decision=%s",
            tip.pk, officer_user, decision,
        )

        return tip

    @staticmethod
    @transaction.atomic
    def detective_verify_tip(
        tip_id: int,
        detective_user: Any,
        decision: str,
        verification_notes: str = "",
    ) -> BountyTip:
        """
        Detective verifies a bounty tip after officer review.

        Validation: Actor MUST have CAN_VERIFY_BOUNTY_TIP permission and
        MUST be the assigned Detective for the suspect/case.

        If REJECTED, update status and notify the citizen.
        If VERIFIED, update status to VERIFIED, generate a secure unique_code,
        save it, compute reward_amount, and dispatch a notification containing
        the code to the citizen.
        """
        perm = f"suspects.{SuspectsPerms.CAN_VERIFY_BOUNTY_TIP}"
        if not detective_user.has_perm(perm):
            raise PermissionDenied(
                "You do not have permission to verify bounty tips.",
            )

        try:
            tip = BountyTip.objects.select_related(
                "suspect", "case", "informant",
            ).select_for_update().get(pk=tip_id)
        except BountyTip.DoesNotExist:
            raise NotFound(f"Bounty tip with id {tip_id} not found.")

        if tip.status != BountyTipStatus.OFFICER_REVIEWED:
            raise InvalidTransition(
                current=tip.status,
                target="verified / rejected",
                reason="Only tips in OFFICER_REVIEWED status can be verified.",
            )

        # Validate the detective is assigned to the related case
        case = tip.case or (tip.suspect.case if tip.suspect else None)
        if case and hasattr(case, "assigned_detective"):
            if case.assigned_detective and case.assigned_detective != detective_user:
                raise PermissionDenied(
                    "You are not the assigned detective for this case.",
                )

        tip.verified_by = detective_user

        if decision == "reject":
            tip.status = BountyTipStatus.REJECTED
            tip.save(update_fields=["status", "verified_by", "updated_at"])

            NotificationService.create(
                actor=detective_user,
                recipients=tip.informant,
                event_type="bounty_tip_rejected",
                payload={
                    "tip_id": tip.pk,
                    "verification_notes": verification_notes,
                },
                related_object=tip,
            )
        else:
            # decision == "verify"
            tip.status = BountyTipStatus.VERIFIED

            # Generate cryptographically secure unique code
            tip.unique_code = BountyTipService._generate_secure_code()

            # Compute reward amount from suspect's reward_amount property
            if tip.suspect:
                tip.reward_amount = tip.suspect.reward_amount
            elif tip.case:
                # Fallback: use the highest reward among wanted suspects
                # in the case.  Use select_related("case") so that the
                # ``reward_amount`` property (which reads case.crime_level)
                # does not trigger an extra query per suspect.
                from suspects.models import Suspect as SuspectModel
                suspects_in_case = SuspectModel.objects.filter(
                    case=tip.case, status=SuspectStatus.WANTED,
                ).select_related("case")
                max_reward = 0
                for s in suspects_in_case:
                    max_reward = max(max_reward, s.reward_amount)
                tip.reward_amount = max_reward if max_reward else 0
            else:
                tip.reward_amount = 0

            tip.save(update_fields=[
                "status", "verified_by", "unique_code",
                "reward_amount", "updated_at",
            ])

            # Notify the citizen with the unique code
            NotificationService.create(
                actor=detective_user,
                recipients=tip.informant,
                event_type="bounty_tip_verified",
                payload={
                    "tip_id": tip.pk,
                    "unique_code": tip.unique_code,
                    "reward_amount": str(tip.reward_amount),
                    "verification_notes": verification_notes,
                },
                related_object=tip,
            )

        logger.info(
            "BountyTip #%d verified by detective=%s decision=%s",
            tip.pk, detective_user, decision,
        )

        return tip

    @staticmethod
    def lookup_reward(
        national_id: str,
        unique_code: str,
        requesting_user: Any,
    ) -> dict[str, Any]:
        """
        Look up bounty reward info using national ID and unique code.

        Searches for a VERIFIED tip matching BOTH the citizen's
        national_id and the exact unique_code. Returns the reward status
        and details. If not found, raises NotFound.
        """
        tip = BountyTip.objects.select_related(
            "suspect", "case", "informant",
        ).filter(
            informant__national_id=national_id,
            unique_code=unique_code,
            status=BountyTipStatus.VERIFIED,
        ).first()

        if tip is None:
            raise NotFound(
                "No verified bounty tip found matching the provided "
                "national ID and unique code.",
            )

        return {
            "tip_id": tip.pk,
            "informant_name": tip.informant.get_full_name(),
            "informant_national_id": national_id,
            "reward_amount": tip.reward_amount,
            "is_claimed": tip.is_claimed,
            "suspect_name": tip.suspect.full_name if tip.suspect else None,
            "case_id": tip.case_id or (tip.suspect.case_id if tip.suspect else None),
        }


# ═══════════════════════════════════════════════════════════════════
#  Bail Service
# ═══════════════════════════════════════════════════════════════════


class BailService:
    """
    Manages bail/fine records for suspects.

    Only applicable to Level 2 / Level 3 suspects and Level 3 convicted
    criminals (project-doc §4.9).  The amount is decided by the Sergeant.

    Eligibility Rules
    -----------------
    - **Level 1 (Major) / Critical**: Bail is **never** allowed.
    - **Level 2 (Medium)**: Bail allowed for ``ARRESTED`` suspects only.
      The actor must have at least a Sergeant role (``CAN_SET_BAIL_AMOUNT``).
    - **Level 3 (Minor)**: Bail allowed for ``ARRESTED`` suspects **and**
      ``CONVICTED`` criminals. Sergeant approval required.
    """

    #: Role-based scope config for bail visibility.
    #: Mirrors the pattern used by CaseQueryService's ``CASE_SCOPE_CONFIG``.
    BAIL_SCOPE_CONFIG: dict[str, Any] = {
        # Detectives see bails for suspects on their assigned cases
        "detective":      lambda qs, u: qs.filter(
                              Q(case__assigned_detective=u) | Q(suspect__identified_by=u)
                          ),
        # Sergeants see bails for suspects on cases they supervise
        "sergeant":       lambda qs, u: qs.filter(
                              Q(case__assigned_sergeant=u) | Q(approved_by=u)
                          ),
        # Senior / admin roles — unrestricted
        "captain":        lambda qs, u: qs,
        "police_chief":   lambda qs, u: qs,
        "system_admin":   lambda qs, u: qs,
        # Judge — only bails on cases assigned to them
        "judge":          lambda qs, u: qs.filter(case__assigned_judge=u),
    }

    # Roles considered at least Sergeant rank or higher for bail authorization
    _SERGEANT_OR_HIGHER = {
        "sergeant", "captain", "police_chief", "system_admin",
    }

    @staticmethod
    def _get_suspect_or_404(suspect_id: int) -> Suspect:
        """Fetch suspect with related case, or raise ``NotFound``."""
        try:
            return Suspect.objects.select_related("case").get(pk=suspect_id)
        except Suspect.DoesNotExist:
            raise NotFound(f"Suspect #{suspect_id} not found.")

    @classmethod
    def _check_eligibility(cls, suspect: Suspect, actor: Any) -> None:
        """
        Enforce bail eligibility business rules.

        Raises ``DomainError`` or ``PermissionDenied`` when bail is not
        allowed for the given suspect/actor combination.
        """
        crime_level = suspect.case.crime_level
        suspect_status = suspect.status

        # ── Rule 1: Level 1 and Critical crimes are never bail-eligible ──
        if crime_level >= CrimeLevel.LEVEL_1:
            raise DomainError(
                "Bail is not allowed for Level 1 (major) or Critical crimes."
            )

        # ── Rule 2: Suspect must be ARRESTED or CONVICTED ───────────────
        allowed_statuses = {SuspectStatus.ARRESTED}
        if crime_level == CrimeLevel.LEVEL_3:
            # Level 3 convicted criminals are also eligible
            allowed_statuses.add(SuspectStatus.CONVICTED)

        if suspect_status not in allowed_statuses:
            if crime_level == CrimeLevel.LEVEL_3:
                raise DomainError(
                    f"Bail for Level 3 crimes requires the suspect to be "
                    f"arrested or convicted. Current status: {suspect_status}."
                )
            raise DomainError(
                f"Bail for Level 2 crimes requires the suspect to be "
                f"arrested. Current status: {suspect_status}."
            )

        # ── Rule 3: Actor must be Sergeant or higher ────────────────────
        role_name = get_user_role_name(actor)
        if role_name not in cls._SERGEANT_OR_HIGHER:
            raise PermissionDenied(
                "Only a Sergeant or higher rank can set bail amounts."
            )

    @classmethod
    def get_bails_for_suspect(
        cls,
        suspect_id: int,
        requesting_user: Any,
    ) -> QuerySet[Bail]:
        """
        Return all bail records for a given suspect, scoped to the
        requesting user's role.

        Parameters
        ----------
        suspect_id : int
            PK of the suspect.
        requesting_user : User
            Authenticated user; used for role-based scoping.

        Returns
        -------
        QuerySet[Bail]
            Filtered, ``select_related`` queryset.
        """
        # Ensure suspect exists
        cls._get_suspect_or_404(suspect_id)

        qs = Bail.objects.filter(suspect_id=suspect_id).select_related(
            "suspect", "case", "approved_by",
        )

        # Apply role scoping
        qs = apply_role_filter(
            qs,
            requesting_user,
            scope_config=cls.BAIL_SCOPE_CONFIG,
            default="none",
        )

        return qs.order_by("-created_at")

    @classmethod
    def get_bail_detail(
        cls,
        suspect_id: int,
        bail_id: int,
        requesting_user: Any,
    ) -> Bail:
        """
        Return a single bail record, scoped to the requesting user's role.

        Parameters
        ----------
        suspect_id : int
        bail_id : int
        requesting_user : User

        Returns
        -------
        Bail

        Raises
        ------
        NotFound
            If the bail does not exist or is not visible to the user.
        """
        qs = Bail.objects.filter(
            pk=bail_id,
            suspect_id=suspect_id,
        ).select_related("suspect", "case", "approved_by")

        qs = apply_role_filter(
            qs,
            requesting_user,
            scope_config=cls.BAIL_SCOPE_CONFIG,
            default="none",
        )

        try:
            return qs.get()
        except Bail.DoesNotExist:
            raise NotFound(
                f"Bail #{bail_id} not found or not accessible."
            )

    @classmethod
    @transaction.atomic
    def create_bail(
        cls,
        actor: Any,
        suspect_id: int,
        amount: Any,
        conditions: str | None = None,
    ) -> Bail:
        """
        Create a bail record for a suspect after checking eligibility.

        Parameters
        ----------
        actor : User
            The Sergeant (or higher) setting the bail.
        suspect_id : int
            PK of the suspect.
        amount : Decimal | int
            Bail amount in Rials. Must be positive.
        conditions : str | None
            Optional bail conditions text.

        Returns
        -------
        Bail
            The newly created bail record. Payment-related fields
            (``is_paid``, ``payment_reference``, ``paid_at``) are left
            at their defaults.

        Raises
        ------
        PermissionDenied
            If the actor lacks the required rank.
        DomainError
            If the suspect/case is ineligible for bail.
        NotFound
            If the suspect does not exist.
        """
        suspect = cls._get_suspect_or_404(suspect_id)
        cls._check_eligibility(suspect, actor)

        bail = Bail.objects.create(
            suspect=suspect,
            case=suspect.case,
            amount=amount,
            conditions=conditions or "",
            approved_by=actor,
        )

        logger.info(
            "Bail #%d created for Suspect #%d (Case #%d) by %s — amount: %s",
            bail.pk, suspect.pk, suspect.case_id, actor, amount,
        )

        return bail

    @staticmethod
    @transaction.atomic
    def process_bail_payment(
        bail_id: int,
        payment_reference: str,
        requesting_user: Any,
    ) -> Bail:
        """
        Mark a bail as paid and release the suspect.

        Parameters
        ----------
        bail_id : int
            PK of the bail record.
        payment_reference : str
            Reference string from the payment gateway.
        requesting_user : User
            The user processing the payment.

        Returns
        -------
        Bail
            The updated bail record with ``is_paid=True``.

        Raises
        ------
        NotFound
            If the bail does not exist.
        DomainError
            If the bail is already paid.
        """
        try:
            bail = Bail.objects.select_related("suspect", "case").get(pk=bail_id)
        except Bail.DoesNotExist:
            raise NotFound(f"Bail with id {bail_id} not found.")

        if bail.is_paid:
            raise DomainError("This bail has already been paid.")

        bail.is_paid = True
        bail.payment_reference = payment_reference
        bail.paid_at = timezone.now()
        bail.save(update_fields=["is_paid", "payment_reference", "paid_at"])

        # Transition suspect to RELEASED if currently eligible
        suspect = bail.suspect
        if suspect.status == SuspectStatus.CONVICTED:
            suspect.status = SuspectStatus.RELEASED
            suspect.save(update_fields=["status"])
            logger.info(
                "Suspect #%d released after bail #%d payment by %s",
                suspect.pk, bail.pk, requesting_user,
            )

        logger.info(
            "Bail #%d paid — ref: %s, by: %s",
            bail.pk, payment_reference, requesting_user,
        )

        return bail
