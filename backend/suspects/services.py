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
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from core.domain.exceptions import DomainError, InvalidTransition, NotFound, PermissionDenied
from core.domain.notifications import NotificationService
from core.permissions_constants import SuspectsPerms

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
            qs = qs.filter(status=SuspectStatus.WANTED, wanted_since__lte=cutoff)
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
    def get_most_wanted_list() -> QuerySet[Suspect]:
        """
        Return suspects qualifying for the Most Wanted page.

        A suspect is "most wanted" when they have been wanted for
        over 30 days in any open case (project-doc §4.7).

        Returns
        -------
        QuerySet[Suspect]
            Suspects with ``days_wanted > 30`` and status ``WANTED``,
            ordered by ``most_wanted_score`` descending.

        Implementation Contract
        -----------------------
        1. Filter suspects where ``status = WANTED`` and
           ``wanted_since`` is more than 30 days ago.
        2. ``select_related("case")``.
        3. Return queryset (the view will handle serialisation).

        Notes
        -----
        The ``most_wanted_score`` is a Python property, so true
        ordering by score requires either annotation at the DB level
        or in-memory sorting.  For the structural draft, return
        the filtered queryset and note that final ordering may
        require ``sorted()`` on the serialised list.
        """
        cutoff = timezone.now() - timedelta(days=30)
        return (
            Suspect.objects.filter(
                status=SuspectStatus.WANTED,
                wanted_since__lte=cutoff,
            )
            .select_related("case")
            .order_by("wanted_since")
        )


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
        perm_codename = ArrestAndWarrantService._TRANSITION_PERMISSION_MAP.get(
            (current, new_status),
        )
        if perm_codename and not requesting_user.has_perm(
            f"suspects.{perm_codename}"
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
    #: permission codename.
    _TRANSITION_PERMISSION_MAP: dict[tuple[str, str], str] = {
        (SuspectStatus.ARRESTED, SuspectStatus.UNDER_INTERROGATION):
            SuspectsPerms.CAN_CONDUCT_INTERROGATION,
        (SuspectStatus.UNDER_INTERROGATION, SuspectStatus.UNDER_TRIAL):
            SuspectsPerms.CAN_RENDER_VERDICT,
        (SuspectStatus.UNDER_TRIAL, SuspectStatus.CONVICTED):
            SuspectsPerms.CAN_JUDGE_TRIAL,
        (SuspectStatus.UNDER_TRIAL, SuspectStatus.ACQUITTED):
            SuspectsPerms.CAN_JUDGE_TRIAL,
        (SuspectStatus.ARRESTED, SuspectStatus.RELEASED):
            SuspectsPerms.CAN_SET_BAIL_AMOUNT,
        (SuspectStatus.CONVICTED, SuspectStatus.RELEASED):
            SuspectsPerms.CAN_SET_BAIL_AMOUNT,
    }

    #: Legal transitions in the suspect lifecycle state machine.
    _ALLOWED_TRANSITIONS: dict[str, set[str]] = {
        SuspectStatus.WANTED: {SuspectStatus.ARRESTED},
        SuspectStatus.ARRESTED: {
            SuspectStatus.UNDER_INTERROGATION,
            SuspectStatus.RELEASED,
        },
        SuspectStatus.UNDER_INTERROGATION: {SuspectStatus.UNDER_TRIAL},
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

        Parameters
        ----------
        suspect_id : int
            PK of the suspect.
        requesting_user : User
            Used for permission-based scoping.

        Returns
        -------
        QuerySet[Interrogation]
            Interrogations ordered by ``-created_at``.

        Implementation Contract
        -----------------------
        1. Assert the user has ``VIEW_INTERROGATION`` permission.
        2. Return ``Interrogation.objects.filter(
               suspect_id=suspect_id
           ).select_related(
               "detective", "sergeant", "suspect", "case"
           ).order_by("-created_at")``.
        """
        raise NotImplementedError

    @staticmethod
    @transaction.atomic
    def create_interrogation(
        suspect_id: int,
        validated_data: dict[str, Any],
        requesting_user: Any,
    ) -> Interrogation:
        """
        Create a new interrogation session for a suspect.

        Parameters
        ----------
        suspect_id : int
            PK of the suspect being interrogated.
        validated_data : dict
            Cleaned data from ``InterrogationCreateSerializer``.
            Keys: ``detective_guilt_score``, ``sergeant_guilt_score``,
            ``notes``.
        requesting_user : User
            The user (Detective or Sergeant) creating the record.
            Must have ``CAN_CONDUCT_INTERROGATION`` permission.

        Returns
        -------
        Interrogation
            The newly created interrogation session.

        Raises
        ------
        PermissionError
            If the user lacks ``CAN_CONDUCT_INTERROGATION``.
        django.core.exceptions.ValidationError
            - If the suspect is not in ``ARRESTED`` or
              ``UNDER_INTERROGATION`` status.
            - If the suspect is not approved by a sergeant.

        Implementation Contract
        -----------------------
        1. Assert ``CAN_CONDUCT_INTERROGATION`` permission.
        2. Fetch suspect: ``suspect = Suspect.objects.get(pk=suspect_id)``.
        3. Guard: suspect status must be ``ARRESTED`` or
           ``UNDER_INTERROGATION``.
        4. If suspect is ``ARRESTED``, transition to
           ``UNDER_INTERROGATION`` (call
           ``ArrestAndWarrantService.transition_status``).
        5. Inject:
           - ``suspect = suspect``
           - ``case = suspect.case``
           - ``detective = requesting_user`` (or resolve from case assignment)
           - ``sergeant = requesting_user`` (or resolve from case assignment)
        6. ``interrogation = Interrogation.objects.create(**validated_data)``.
        7. Dispatch notification to the Captain with the guilt scores.
        8. Return ``interrogation``.
        """
        raise NotImplementedError


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

    @staticmethod
    def get_trials_for_suspect(
        suspect_id: int,
        requesting_user: Any,
    ) -> QuerySet[Trial]:
        """
        Return all trial records for a given suspect.

        Parameters
        ----------
        suspect_id : int
            PK of the suspect.
        requesting_user : User
            Used for permission-based scoping.

        Returns
        -------
        QuerySet[Trial]
            Trials ordered by ``-created_at``.

        Implementation Contract
        -----------------------
        1. Assert ``VIEW_TRIAL`` permission.
        2. Return ``Trial.objects.filter(
               suspect_id=suspect_id
           ).select_related("judge", "suspect", "case").order_by("-created_at")``.
        """
        raise NotImplementedError

    @staticmethod
    @transaction.atomic
    def create_trial(
        suspect_id: int,
        validated_data: dict[str, Any],
        requesting_user: Any,
    ) -> Trial:
        """
        Create a trial record for a suspect.

        Parameters
        ----------
        suspect_id : int
            PK of the suspect on trial.
        validated_data : dict
            Cleaned data from ``TrialCreateSerializer``.
            Keys: ``verdict``, ``punishment_title``, ``punishment_description``.
        requesting_user : User
            The Judge presiding.  Must have ``CAN_JUDGE_TRIAL``.

        Returns
        -------
        Trial
            The newly created trial record.

        Raises
        ------
        PermissionError
            If the user lacks ``CAN_JUDGE_TRIAL``.
        django.core.exceptions.ValidationError
            - If suspect is not in ``UNDER_TRIAL`` status.
            - If verdict is guilty but punishment fields are empty.

        Implementation Contract
        -----------------------
        1. Assert ``CAN_JUDGE_TRIAL`` permission.
        2. Fetch suspect.
        3. Guard: ``status == UNDER_TRIAL``.
        4. Inject:
           - ``suspect = suspect``
           - ``case = suspect.case``
           - ``judge = requesting_user``
        5. Create trial.
        6. Transition suspect status:
           - If ``verdict == "guilty"`` → ``CONVICTED``.
           - If ``verdict == "innocent"`` → ``ACQUITTED``.
        7. Return ``trial``.
        """
        raise NotImplementedError


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

    @staticmethod
    def get_bounty_tips(
        requesting_user: Any,
        filters: dict[str, Any] | None = None,
    ) -> QuerySet[BountyTip]:
        """
        Return bounty tips visible to the requesting user.

        Parameters
        ----------
        requesting_user : User
        filters : dict, optional
            Optional filter parameters.

        Returns
        -------
        QuerySet[BountyTip]

        Implementation Contract
        -----------------------
        Base users see only their own submitted tips.
        Officers/Detectives see all tips for their cases.
        Admin/Chief see all tips.
        """
        raise NotImplementedError

    @staticmethod
    @transaction.atomic
    def submit_tip(
        validated_data: dict[str, Any],
        requesting_user: Any,
    ) -> BountyTip:
        """
        Citizen submits a bounty tip about a suspect or case.

        Parameters
        ----------
        validated_data : dict
            From ``BountyTipCreateSerializer``.
            Keys: ``suspect``, ``case``, ``information``.
        requesting_user : User
            The citizen submitting the tip.

        Returns
        -------
        BountyTip
            The newly created tip.

        Implementation Contract
        -----------------------
        1. Inject ``informant = requesting_user``.
        2. Inject ``status = BountyTipStatus.PENDING``.
        3. Create and return the tip.
        """
        raise NotImplementedError

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

        Parameters
        ----------
        tip_id : int
            PK of the tip.
        officer_user : User
            Must have ``CAN_REVIEW_BOUNTY_TIP``.
        decision : str
            ``"accept"`` or ``"reject"``.
        review_notes : str

        Returns
        -------
        BountyTip

        Raises
        ------
        PermissionError
            If lacking review permission.
        django.core.exceptions.ValidationError
            If tip is not in ``PENDING`` status.

        Implementation Contract
        -----------------------
        1. Assert permission.
        2. Fetch tip, guard status == PENDING.
        3. If accept: status → OFFICER_REVIEWED, set reviewed_by.
        4. If reject: status → REJECTED, set reviewed_by.
        5. Save and return.
        """
        raise NotImplementedError

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

        Upon verification, a unique reward code is generated.

        Parameters
        ----------
        tip_id : int
            PK of the tip.
        detective_user : User
            Must have ``CAN_VERIFY_BOUNTY_TIP``.
        decision : str
            ``"verify"`` or ``"reject"``.
        verification_notes : str

        Returns
        -------
        BountyTip

        Raises
        ------
        PermissionError
            If lacking verify permission.
        django.core.exceptions.ValidationError
            If tip is not in ``OFFICER_REVIEWED`` status.

        Implementation Contract
        -----------------------
        1. Assert permission.
        2. Fetch tip, guard status == OFFICER_REVIEWED.
        3. If verify:
           - status → VERIFIED
           - set verified_by
           - call ``tip.generate_unique_code()``
           - calculate and set ``reward_amount`` from suspect's
             ``reward_amount`` property
           - Notify the informant with the unique code.
        4. If reject: status → REJECTED, set verified_by.
        5. Save and return.
        """
        raise NotImplementedError

    @staticmethod
    def lookup_reward(
        national_id: str,
        unique_code: str,
        requesting_user: Any,
    ) -> dict[str, Any]:
        """
        Look up bounty reward info using national ID and unique code.

        Any police rank can use this to verify a citizen's reward claim
        at the station (project-doc §4.8).

        Parameters
        ----------
        national_id : str
            The citizen's national ID.
        unique_code : str
            The reward claim code.
        requesting_user : User
            Must be a police rank.

        Returns
        -------
        dict
            Contains: ``tip_id``, ``informant_name``, ``informant_national_id``,
            ``reward_amount``, ``is_claimed``, ``suspect_name``, ``case_id``.

        Raises
        ------
        PermissionError
            If the user lacks police rank permissions.
        django.core.exceptions.ValidationError
            If no matching tip is found.

        Implementation Contract
        -----------------------
        1. Assert user is a police rank.
        2. Fetch ``BountyTip`` where:
           - ``informant__national_id == national_id`` (user's national_id)
           - ``unique_code == unique_code``
           - ``status == VERIFIED``
        3. If not found, raise ValidationError.
        4. Return dict with reward information.
        """
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════
#  Bail Service
# ═══════════════════════════════════════════════════════════════════


class BailService:
    """
    Manages bail/fine records for suspects.

    Only applicable to Level 2 / Level 3 suspects and Level 3 convicted
    criminals (project-doc §4.9).  The amount is decided by the Sergeant
    and payment is processed via a payment gateway.
    """

    @staticmethod
    def get_bails_for_suspect(
        suspect_id: int,
        requesting_user: Any,
    ) -> QuerySet[Bail]:
        """
        Return all bail records for a given suspect.

        Parameters
        ----------
        suspect_id : int
        requesting_user : User

        Returns
        -------
        QuerySet[Bail]

        Implementation Contract
        -----------------------
        1. Assert VIEW_BAIL permission.
        2. Return filtered, select_related queryset.
        """
        raise NotImplementedError

    @staticmethod
    @transaction.atomic
    def create_bail(
        suspect_id: int,
        validated_data: dict[str, Any],
        requesting_user: Any,
    ) -> Bail:
        """
        Create a bail record for a suspect.

        Parameters
        ----------
        suspect_id : int
            PK of the suspect.
        validated_data : dict
            From ``BailCreateSerializer``.  Keys: ``amount``.
        requesting_user : User
            The Sergeant setting the bail.  Must have
            ``CAN_SET_BAIL_AMOUNT``.

        Returns
        -------
        Bail
            The newly created bail record.

        Raises
        ------
        PermissionError
            If lacking ``CAN_SET_BAIL_AMOUNT``.
        django.core.exceptions.ValidationError
            - If suspect's case is not Level 2 or Level 3.
            - If suspect is not in ``ARRESTED`` or ``CONVICTED`` status.

        Implementation Contract
        -----------------------
        1. Assert ``CAN_SET_BAIL_AMOUNT`` permission.
        2. Fetch suspect with ``select_related("case")``.
        3. Guard: ``case.crime_level`` must be 2 or 3 (Level 2 or Level 3).
           For convicted criminals, only Level 3 is eligible.
        4. Guard: suspect status must be ``ARRESTED`` or ``CONVICTED``.
        5. Inject:
           - ``suspect = suspect``
           - ``case = suspect.case``
           - ``approved_by = requesting_user``
        6. Create bail record.
        7. Return ``bail``.
        """
        raise NotImplementedError

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
            Payment gateway reference/transaction ID.
        requesting_user : User

        Returns
        -------
        Bail
            The updated bail record.

        Implementation Contract
        -----------------------
        1. Fetch bail.
        2. Guard: bail must not already be paid.
        3. Set ``is_paid = True``, ``payment_reference``,
           ``paid_at = timezone.now()``.
        4. Save bail.
        5. Transition suspect status to ``RELEASED``
           (via ``ArrestAndWarrantService.transition_status``).
        6. Return bail.
        """
        raise NotImplementedError
