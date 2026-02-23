"""
Cases app Service Layer.

This module is the **single source of truth** for all business logic
in the ``cases`` app.  Views must remain thin: validate input via
serializers, call a service method, and return the result wrapped in
a DRF ``Response``.

Architecture
------------
- ``CaseQueryService``        — Filtered queryset construction.
- ``CaseCreationService``     — Draft creation for complaint & crime-scene paths.
- ``CaseWorkflowService``     — 16-stage state-machine transitions.
- ``CaseAssignmentService``   — Assign/unassign personnel to a case.
- ``CaseComplainantService``  — Complainant lifetime management (add / review).
- ``CaseWitnessService``      — Witness registration (crime-scene path).
- ``CaseCalculationService``  — Reward & tracking-threshold formulas.

Workflow State-Machine Overview
--------------------------------
The two creation paths share a common post-opening pipeline:

  COMPLAINT PATH
  ──────────────
  COMPLAINT_REGISTERED
    → CADET_REVIEW             (complainant submits for review)
    → RETURNED_TO_COMPLAINANT  (cadet finds defects; +rejection_count)
       ↺ CADET_REVIEW          (complainant re-submits after editing)
    → OFFICER_REVIEW           (cadet approves; forwards to officer)
    → RETURNED_TO_CADET        (officer finds defects)
       ↺ OFFICER_REVIEW        (cadet re-submits)
    → OPEN                     (officer approves)
  * 3rd rejection → VOIDED (auto-triggered in service, no manual step)

  CRIME-SCENE PATH
  ─────────────────
  PENDING_APPROVAL
    → OPEN (one superior approves)
  * If creator is Police Chief → OPEN immediately on creation

  COMMON PIPELINE (after OPEN)
  ─────────────────────────────
  OPEN → INVESTIGATION         (detective assigned)
  INVESTIGATION → SUSPECT_IDENTIFIED
  SUSPECT_IDENTIFIED → SERGEANT_REVIEW
  SERGEANT_REVIEW → ARREST_ORDERED  (sergeant approves)
  SERGEANT_REVIEW → INVESTIGATION   (sergeant rejects; case back to detective)
  ARREST_ORDERED → INTERROGATION
  INTERROGATION → CAPTAIN_REVIEW
  CAPTAIN_REVIEW → CHIEF_REVIEW     (only if crime_level == CRITICAL)
  CAPTAIN_REVIEW → JUDICIARY        (non-critical cases)
  CHIEF_REVIEW → JUDICIARY          (critical; chief approves)
  JUDICIARY → CLOSED

Permission constants used here (from ``core.permissions_constants.CasesPerms``):
  - CAN_REVIEW_COMPLAINT    → Cadet
  - CAN_APPROVE_CASE        → Officer (complaint) / Superior (crime-scene)
  - CAN_ASSIGN_DETECTIVE    → Sergeant / Captain
  - CAN_CHANGE_CASE_STATUS  → Detective, Sergeant, Captain, Chief
  - CAN_FORWARD_TO_JUDICIARY→ Captain, Chief
  - CAN_APPROVE_CRITICAL_CASE → Police Chief
"""

from __future__ import annotations

import datetime
import re
from typing import Any

from django.db import transaction
from django.db.models import Count, Max, Prefetch, Q, QuerySet
from django.utils import timezone

from core.constants import REWARD_MULTIPLIER
from core.domain.access import apply_role_filter, get_user_role_name
from core.domain.exceptions import DomainError, InvalidTransition, NotFound, PermissionDenied
from core.domain.notifications import NotificationService
from core.permissions_constants import CasesPerms

from .models import (
    Case,
    CaseComplainant,
    CaseCreationType,
    CaseStatus,
    CaseStatusLog,
    CaseWitness,
    ComplainantStatus,
    CrimeLevel,
)

# ── Roles that are NOT allowed to create crime-scene cases ──────────
_CRIME_SCENE_FORBIDDEN_ROLES: set[str] = {"cadet", "base_user", "complainant"}

# ── Role name that auto-approves crime-scene cases ──────────────────
_CHIEF_ROLE: str = "police_chief"

# ── Valid role-field names for unassign ──────────────────────────────
_VALID_ROLE_FIELDS: set[str] = {
    "assigned_detective",
    "assigned_sergeant",
    "assigned_captain",
    "assigned_judge",
}

# ── Phone number regex (Iranian mobile format) ──────────────────────
_PHONE_REGEX = re.compile(r"^\+?\d{7,15}$")


# ═══════════════════════════════════════════════════════════════════
#  Valid transition map
# ═══════════════════════════════════════════════════════════════════

#: Maps (from_status, to_status) → set of *permission codenames* that
#: allow the transition.  A user must have AT LEAST ONE of the listed
#: permissions (OR-logic).  Transitions not present here are illegal.
ALLOWED_TRANSITIONS: dict[tuple[str, str], set[str]] = {
    # ── Complaint workflow ──────────────────────────────────────────
    (CaseStatus.COMPLAINT_REGISTERED, CaseStatus.CADET_REVIEW): {CasesPerms.ADD_CASE},
    (CaseStatus.CADET_REVIEW, CaseStatus.RETURNED_TO_COMPLAINANT): {CasesPerms.CAN_REVIEW_COMPLAINT},
    (CaseStatus.CADET_REVIEW, CaseStatus.OFFICER_REVIEW): {CasesPerms.CAN_REVIEW_COMPLAINT},
    (CaseStatus.CADET_REVIEW, CaseStatus.VOIDED): {CasesPerms.CAN_REVIEW_COMPLAINT},
    (CaseStatus.RETURNED_TO_COMPLAINANT, CaseStatus.CADET_REVIEW): {CasesPerms.ADD_CASE},
    (CaseStatus.OFFICER_REVIEW, CaseStatus.RETURNED_TO_CADET): {CasesPerms.CAN_APPROVE_CASE},
    (CaseStatus.OFFICER_REVIEW, CaseStatus.OPEN): {CasesPerms.CAN_APPROVE_CASE},
    (CaseStatus.RETURNED_TO_CADET, CaseStatus.OFFICER_REVIEW): {CasesPerms.CAN_REVIEW_COMPLAINT},
    # ── Crime-scene workflow ────────────────────────────────────────
    (CaseStatus.PENDING_APPROVAL, CaseStatus.OPEN): {CasesPerms.CAN_APPROVE_CASE},
    # ── Common investigation pipeline ──────────────────────────────
    (CaseStatus.OPEN, CaseStatus.INVESTIGATION): {CasesPerms.CAN_ASSIGN_DETECTIVE},
    (CaseStatus.INVESTIGATION, CaseStatus.SUSPECT_IDENTIFIED): {CasesPerms.CAN_CHANGE_CASE_STATUS},
    (CaseStatus.SUSPECT_IDENTIFIED, CaseStatus.SERGEANT_REVIEW): {CasesPerms.CAN_CHANGE_CASE_STATUS},
    (CaseStatus.SERGEANT_REVIEW, CaseStatus.ARREST_ORDERED): {CasesPerms.CAN_CHANGE_CASE_STATUS},
    (CaseStatus.SERGEANT_REVIEW, CaseStatus.INVESTIGATION): {CasesPerms.CAN_CHANGE_CASE_STATUS},
    (CaseStatus.ARREST_ORDERED, CaseStatus.INTERROGATION): {CasesPerms.CAN_CHANGE_CASE_STATUS},
    (CaseStatus.INTERROGATION, CaseStatus.CAPTAIN_REVIEW): {CasesPerms.CAN_CHANGE_CASE_STATUS},
    (CaseStatus.CAPTAIN_REVIEW, CaseStatus.CHIEF_REVIEW): {CasesPerms.CAN_APPROVE_CRITICAL_CASE},
    (CaseStatus.CAPTAIN_REVIEW, CaseStatus.JUDICIARY): {CasesPerms.CAN_FORWARD_TO_JUDICIARY},
    (CaseStatus.CHIEF_REVIEW, CaseStatus.JUDICIARY): {CasesPerms.CAN_FORWARD_TO_JUDICIARY},
    (CaseStatus.JUDICIARY, CaseStatus.CLOSED): {CasesPerms.CAN_CHANGE_CASE_STATUS},
}

#: Maximum number of complaint rejections before automatic voiding.
MAX_REJECTION_COUNT: int = 3


# ═══════════════════════════════════════════════════════════════════
#  Case Query Service
# ═══════════════════════════════════════════════════════════════════


# ── Role-scoped visibility constants ────────────────────────────────

#: Statuses visible to Cadets (early complaint pipeline).
CADET_VISIBLE_STATUSES: set[str] = {
    CaseStatus.COMPLAINT_REGISTERED,
    CaseStatus.CADET_REVIEW,
    CaseStatus.RETURNED_TO_COMPLAINANT,
    CaseStatus.RETURNED_TO_CADET,
}

#: Statuses excluded for Officer-level roles (complaint-only early stages).
OFFICER_EXCLUDED_STATUSES: set[str] = {
    CaseStatus.COMPLAINT_REGISTERED,
    CaseStatus.CADET_REVIEW,
    CaseStatus.RETURNED_TO_COMPLAINANT,
    CaseStatus.VOIDED,
}

#: Statuses visible to Judges.
JUDGE_VISIBLE_STATUSES: set[str] = {
    CaseStatus.JUDICIARY,
    CaseStatus.CLOSED,
}

#: Role → queryset filter config for ``apply_role_filter``.
CASE_SCOPE_CONFIG: dict[str, Any] = {
    # Civilians — only cases where they are a complainant
    "complainant":    lambda qs, u: qs.filter(complainants__user=u),
    "base_user":      lambda qs, u: qs.filter(complainants__user=u),
    # Cadet — early complaint stages
    "cadet":          lambda qs, u: qs.filter(status__in=CADET_VISIBLE_STATUSES),
    # Officers — everything past the complaint-screening phase
    "police_officer": lambda qs, u: qs.exclude(status__in=OFFICER_EXCLUDED_STATUSES),
    "patrol_officer": lambda qs, u: qs.exclude(status__in=OFFICER_EXCLUDED_STATUSES),
    # Detective — only their assigned cases
    "detective":      lambda qs, u: qs.filter(assigned_detective=u),
    # Sergeant — their assigned cases
    "sergeant":       lambda qs, u: qs.filter(
                          Q(assigned_sergeant=u) | Q(assigned_detective__isnull=False)
                      ),
    # Senior / admin roles — unrestricted
    "captain":        lambda qs, u: qs,
    "police_chief":   lambda qs, u: qs,
    "system_admin":   lambda qs, u: qs,
    # Judge — only judiciary/closed cases assigned to them
    "judge":          lambda qs, u: qs.filter(
                          status__in=JUDGE_VISIBLE_STATUSES,
                          assigned_judge=u,
                      ),
}


class CaseQueryService:
    """
    Constructs filtered, annotated querysets for listing cases.

    All heavy query concerns (filter assembly, annotation, ordering)
    live here so the view stays thin.
    """

    # ── Shared select_related fields ────────────────────────────────
    _LIST_SELECT_RELATED: list[str] = [
        "created_by",
        "assigned_detective",
        "assigned_sergeant",
        "assigned_captain",
    ]

    _DETAIL_SELECT_RELATED: list[str] = [
        "created_by",
        "approved_by",
        "assigned_detective",
        "assigned_sergeant",
        "assigned_captain",
        "assigned_judge",
    ]

    @staticmethod
    def _apply_filters(qs: QuerySet, filters: dict[str, Any]) -> QuerySet:
        """Apply explicit query-parameter filters on top of a scoped queryset."""
        if status := filters.get("status"):
            qs = qs.filter(status=status)
        if crime_level := filters.get("crime_level"):
            qs = qs.filter(crime_level=crime_level)
        if detective := filters.get("detective"):
            qs = qs.filter(assigned_detective_id=detective)
        if creation_type := filters.get("creation_type"):
            qs = qs.filter(creation_type=creation_type)
        if created_after := filters.get("created_after"):
            qs = qs.filter(created_at__date__gte=created_after)
        if created_before := filters.get("created_before"):
            qs = qs.filter(created_at__date__lte=created_before)
        if search := filters.get("search"):
            qs = qs.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        return qs

    @classmethod
    def get_filtered_queryset(
        cls,
        requesting_user: Any,
        filters: dict[str, Any],
    ) -> QuerySet:
        """
        Build a role-scoped, filtered queryset of ``Case`` objects.

        Parameters
        ----------
        requesting_user : User
            From ``request.user``.  Used to apply role-based ownership
            scoping before applying explicit filters.
        filters : dict
            Cleaned query-parameter dict from ``CaseFilterSerializer``.

        Returns
        -------
        QuerySet[Case]
            Filtered, annotated, ``select_related`` queryset ready for
            serialisation by ``CaseListSerializer``.
        """
        # 1. Base queryset
        qs = Case.objects.all()

        # 2. Role-scoped filtering
        qs = apply_role_filter(
            qs,
            requesting_user,
            scope_config=CASE_SCOPE_CONFIG,
            default="none",
        )

        # 3. Explicit filters on top of scoped queryset
        qs = cls._apply_filters(qs, filters)

        # 4. DB optimisations — select_related + annotation
        qs = (
            qs
            .select_related(*cls._LIST_SELECT_RELATED)
            .annotate(complainant_count=Count("complainants"))
            .distinct()
        )

        return qs

    @classmethod
    def get_case_detail(
        cls,
        requesting_user: Any,
        case_id: int,
    ) -> Case:
        """
        Return a single ``Case`` instance with all nested sub-resources
        pre-fetched, scoped to the requesting user's role.

        Parameters
        ----------
        requesting_user : User
            From ``request.user``.
        case_id : int
            Primary key of the case.

        Returns
        -------
        Case
            Fully pre-fetched case instance.

        Raises
        ------
        core.domain.exceptions.NotFound
            If the case does not exist or is not visible to the user.
        """
        # 1. Build role-scoped base queryset
        qs = apply_role_filter(
            Case.objects.all(),
            requesting_user,
            scope_config=CASE_SCOPE_CONFIG,
            default="none",
        )

        # 2. Optimise for the detail serializer
        qs = qs.select_related(*cls._DETAIL_SELECT_RELATED).prefetch_related(
            Prefetch(
                "complainants",
                queryset=CaseComplainant.objects.select_related("user", "reviewed_by"),
            ),
            "witnesses",
            Prefetch(
                "status_logs",
                queryset=CaseStatusLog.objects.select_related("changed_by"),
            ),
        )

        # 3. Fetch or raise
        try:
            return qs.get(pk=case_id)
        except Case.DoesNotExist:
            raise NotFound(f"Case #{case_id} not found or not accessible.")


# ═══════════════════════════════════════════════════════════════════
#  Case Creation Service
# ═══════════════════════════════════════════════════════════════════


class CaseCreationService:
    """
    Handles the two distinct case creation flows described in §4.2 of
    the project document.
    """

    @staticmethod
    @transaction.atomic
    def create_complaint_case(
        validated_data: dict[str, Any],
        requesting_user: Any,
    ) -> Case:
        """
        Create a new case via the **complaint registration** workflow.

        The case starts in ``COMPLAINT_REGISTERED`` status.  The complainant
        is the requesting user and is automatically linked as the primary
        ``CaseComplainant``.

        Parameters
        ----------
        validated_data : dict
            Cleaned data from ``ComplaintCaseCreateSerializer``.
            Required fields: ``title``, ``description``, ``crime_level``.
            Optional: ``incident_date``, ``location``.
        requesting_user : User
            The citizen filing the complaint (becomes primary complainant).

        Returns
        -------
        Case
            The newly created case at ``COMPLAINT_REGISTERED`` status.

        Implementation Contract
        -----------------------
        1. Set ``creation_type = CaseCreationType.COMPLAINT``.
        2. Set ``status = CaseStatus.COMPLAINT_REGISTERED``.
        3. Set ``created_by = requesting_user``.
        4. ``case = Case.objects.create(**validated_data)``.
        5. Create ``CaseComplainant(case=case, user=requesting_user, is_primary=True)``.
        6. Create initial ``CaseStatusLog(from_status="", to_status=COMPLAINT_REGISTERED, ...)``.
        7. Return ``case``.
        """
        validated_data["creation_type"] = CaseCreationType.COMPLAINT
        validated_data["status"] = CaseStatus.COMPLAINT_REGISTERED
        validated_data["created_by"] = requesting_user

        case = Case.objects.create(**validated_data)

        CaseComplainant.objects.create(
            case=case,
            user=requesting_user,
            is_primary=True,
        )

        CaseStatusLog.objects.create(
            case=case,
            from_status="",
            to_status=CaseStatus.COMPLAINT_REGISTERED,
            changed_by=requesting_user,
            message="Complaint case created.",
        )

        return case

    @staticmethod
    @transaction.atomic
    def create_crime_scene_case(
        validated_data: dict[str, Any],
        requesting_user: Any,
    ) -> Case:
        """
        Create a new case via the **crime-scene registration** workflow.

        Status depends on the creator's rank:
        - If ``requesting_user`` has the ``Police Chief`` role →
          status is ``OPEN`` immediately (no approval needed, §4.2.2).
        - Otherwise → status is ``PENDING_APPROVAL``.

        Parameters
        ----------
        validated_data : dict
            Cleaned data from ``CrimeSceneCaseCreateSerializer``.
            Required: ``title``, ``description``, ``crime_level``,
            ``incident_date``, ``location``.
            Optional: ``witnesses`` (list of witness dicts).
        requesting_user : User
            Police rank registering the crime scene.

        Returns
        -------
        Case
            The newly created case.

        Implementation Contract
        -----------------------
        1. Determine initial status (OPEN if Chief, else PENDING_APPROVAL).
        2. ``case = Case.objects.create(creation_type=CRIME_SCENE, status=..., created_by=requesting_user, **validated_data_minus_witnesses)``.
        3. If ``validated_data`` includes ``witnesses``:
           bulk-create ``CaseWitness`` records.
        4. Log the initial status transition.
        5. If status == OPEN, automatically set ``approved_by = requesting_user``.
        6. Return ``case``.
        """
        # ── Role guard: Cadets / base users cannot create crime-scene cases
        role_name = get_user_role_name(requesting_user)
        if role_name in _CRIME_SCENE_FORBIDDEN_ROLES or role_name is None:
            raise PermissionDenied(
                "Your role is not permitted to create a crime-scene case."
            )

        # ── Determine initial status based on rank
        is_chief = role_name == _CHIEF_ROLE
        initial_status = CaseStatus.OPEN if is_chief else CaseStatus.PENDING_APPROVAL

        # ── Extract nested witnesses before creating case
        witnesses_data = validated_data.pop("witnesses", []) or []

        validated_data["creation_type"] = CaseCreationType.CRIME_SCENE
        validated_data["status"] = initial_status
        validated_data["created_by"] = requesting_user

        if is_chief:
            validated_data["approved_by"] = requesting_user

        case = Case.objects.create(**validated_data)

        # ── Bulk-create witnesses
        if witnesses_data:
            CaseWitness.objects.bulk_create([
                CaseWitness(case=case, **w) for w in witnesses_data
            ])

        # ── Log the initial status
        log_message = (
            "Crime-scene case created and auto-approved (Police Chief)."
            if is_chief
            else "Crime-scene case created — pending superior approval."
        )
        CaseStatusLog.objects.create(
            case=case,
            from_status="",
            to_status=initial_status,
            changed_by=requesting_user,
            message=log_message,
        )

        # ── Notify approvers if pending
        if not is_chief:
            NotificationService.create(
                actor=requesting_user,
                recipients=[requesting_user],  # placeholder — ideally superiors
                event_type="case_status_changed",
                related_object=case,
            )

        return case


# ═══════════════════════════════════════════════════════════════════
#  Case Workflow Service
# ═══════════════════════════════════════════════════════════════════


class CaseWorkflowService:
    """
    Manages **all** status transitions in the case lifecycle.

    This is the core of the system.  A single ``transition_state`` method
    acts as the validated gateway through the state machine defined by
    ``ALLOWED_TRANSITIONS``.  Role-specific convenience methods (``submit_for_review``,
    ``approve_case``, ``reject_case``) delegate to it after performing
    pre-condition checks.

    Design Pattern: State Machine + Command
    ----------------------------------------
    Each transition is a command: ``(case, target_status, actor, message)``.
    The service validates the command against the state-machine table
    and the actor's permissions, executes it atomically, records the
    ``CaseStatusLog`` entry, and (in the future) dispatches notifications.
    """

    @staticmethod
    @transaction.atomic
    def transition_state(
        case: Case,
        target_status: str,
        requesting_user: Any,
        message: str = "",
    ) -> Case:
        """
        **The central state-machine gateway.**

        Move a case from its current status to ``target_status``, enforcing
        the full permission + validity matrix.

        Parameters
        ----------
        case : Case
            The case to transition.
        target_status : str
            The desired ``CaseStatus`` value.
        requesting_user : User
            The user initiating the transition.
        message : str
            Optional explanation (required for rejection transitions so the
            message reaches the next actor).

        Returns
        -------
        Case
            The updated case instance (``status`` field updated in DB).

        Raises
        ------
        PermissionError
            If ``requesting_user`` does not have any of the permissions
            listed in ``ALLOWED_TRANSITIONS[(current, target)]``.
        django.core.exceptions.ValidationError
            - If ``(case.status, target_status)`` is not a key in
              ``ALLOWED_TRANSITIONS`` (illegal transition).
            - If ``target_status == CHIEF_REVIEW`` but
              ``case.crime_level != CrimeLevel.CRITICAL``.
            - If ``message`` is blank on a rejection transition
              (``RETURNED_TO_COMPLAINANT``, ``RETURNED_TO_CADET``,
              ``INVESTIGATION`` from ``SERGEANT_REVIEW``).

        Implementation Contract
        -----------------------
        1. key = (case.status, target_status)
        2. If key not in ALLOWED_TRANSITIONS → raise ValidationError.
        3. required_perms = ALLOWED_TRANSITIONS[key]
        4. If not any(requesting_user.has_perm(f"cases.{p}") for p in required_perms) → raise PermissionError.
        5. Extra guards:
           a. CHIEF_REVIEW target: assert case.crime_level == CRITICAL.
           b. Rejection targets: assert message is non-blank.
           c. VOIDED path: handled separately by _auto_void.
        6. prev_status = case.status
        7. case.status = target_status
        8. case.save(update_fields=["status", "updated_at"])
        9. CaseStatusLog.objects.create(case=case, from_status=prev_status,
               to_status=target_status, changed_by=requesting_user, message=message)
        10. _dispatch_notifications(case, target_status, requesting_user)
        11. Return case.
        """
        # 1. Lock the row for concurrency safety
        case = Case.objects.select_for_update().get(pk=case.pk)

        # 2. Validate transition exists
        key = (case.status, target_status)
        if key not in ALLOWED_TRANSITIONS:
            raise InvalidTransition(
                current=case.status,
                target=target_status,
                reason="This transition is not allowed.",
            )

        # 3. Permission check (OR-logic)
        required_perms = ALLOWED_TRANSITIONS[key]
        if not any(
            requesting_user.has_perm(f"cases.{p}") for p in required_perms
        ):
            raise PermissionDenied(
                "You do not have permission to perform this transition."
            )

        # 4. Extra guards
        # a. CHIEF_REVIEW target requires CRITICAL crime level
        if target_status == CaseStatus.CHIEF_REVIEW:
            if case.crime_level != CrimeLevel.CRITICAL:
                raise InvalidTransition(
                    current=case.status,
                    target=target_status,
                    reason="Only critical-level cases require Chief Review.",
                )

        # b. Rejection transitions require non-blank message
        _rejection_transitions = {
            (CaseStatus.CADET_REVIEW, CaseStatus.RETURNED_TO_COMPLAINANT),
            (CaseStatus.OFFICER_REVIEW, CaseStatus.RETURNED_TO_CADET),
            (CaseStatus.SERGEANT_REVIEW, CaseStatus.INVESTIGATION),
        }
        if key in _rejection_transitions and not message.strip():
            raise DomainError(
                "A rejection message is required for this transition."
            )

        # 5. Perform the transition
        prev_status = case.status
        case.status = target_status
        case.save(update_fields=["status", "updated_at"])

        # 6. Log the transition
        CaseStatusLog.objects.create(
            case=case,
            from_status=prev_status,
            to_status=target_status,
            changed_by=requesting_user,
            message=message,
        )

        # 7. Dispatch notifications
        CaseWorkflowService._dispatch_notifications(case, target_status, requesting_user)

        return case

    @staticmethod
    @transaction.atomic
    def submit_for_review(case: Case, requesting_user: Any) -> Case:
        """
        **Complainant submits the initial complaint draft for Cadet review.**

        Transitions: ``COMPLAINT_REGISTERED`` → ``CADET_REVIEW``.

        Parameters
        ----------
        case : Case
            The case in ``COMPLAINT_REGISTERED`` status.
        requesting_user : User
            Must be the primary complainant of this case.

        Returns
        -------
        Case
            Updated case instance.

        Raises
        ------
        PermissionError
            If ``requesting_user`` is not the primary complainant.
        django.core.exceptions.ValidationError
            If ``case.status != COMPLAINT_REGISTERED``.

        Implementation Contract
        -----------------------
        1. Assert case.status == COMPLAINT_REGISTERED.
        2. Assert CaseComplainant.objects.filter(case=case, user=requesting_user, is_primary=True).exists().
        3. Delegate to ``transition_state(case, CADET_REVIEW, requesting_user)``.
        """
        if case.status != CaseStatus.COMPLAINT_REGISTERED:
            raise InvalidTransition(
                current=case.status,
                target=CaseStatus.CADET_REVIEW,
                reason="Case must be in COMPLAINT_REGISTERED status to submit.",
            )

        if not CaseComplainant.objects.filter(
            case=case, user=requesting_user, is_primary=True
        ).exists():
            raise PermissionDenied(
                "Only the primary complainant can submit this case for review."
            )

        return CaseWorkflowService.transition_state(
            case, CaseStatus.CADET_REVIEW, requesting_user
        )

    @staticmethod
    @transaction.atomic
    def resubmit_complaint(
        case: Case,
        validated_data: dict[str, Any],
        requesting_user: Any,
    ) -> Case:
        """
        **Complainant edits and re-submits a returned complaint.**

        Transitions: ``RETURNED_TO_COMPLAINANT`` → ``CADET_REVIEW``.

        The complainant may update ``title``, ``description``, ``incident_date``,
        and ``location`` before re-submitting.

        Parameters
        ----------
        case : Case
            Case currently in ``RETURNED_TO_COMPLAINANT`` status.
        validated_data : dict
            Partial update fields allowed during re-submission.
        requesting_user : User
            Must be the primary complainant.

        Returns
        -------
        Case
            Updated case.

        Implementation Contract
        -----------------------
        1. Assert case.status == RETURNED_TO_COMPLAINANT.
        2. Assert primary complainant ownership.
        3. Update allowed mutable fields on case.
        4. Delegate to ``transition_state(case, CADET_REVIEW, requesting_user)``.
        """
        if case.status != CaseStatus.RETURNED_TO_COMPLAINANT:
            raise InvalidTransition(
                current=case.status,
                target=CaseStatus.CADET_REVIEW,
                reason="Case must be in RETURNED_TO_COMPLAINANT status to resubmit.",
            )

        if not CaseComplainant.objects.filter(
            case=case, user=requesting_user, is_primary=True
        ).exists():
            raise PermissionDenied(
                "Only the primary complainant can resubmit this case."
            )

        # Update allowed mutable fields
        mutable_fields = ["title", "description", "incident_date", "location"]
        update_fields = []
        for field in mutable_fields:
            if field in validated_data:
                setattr(case, field, validated_data[field])
                update_fields.append(field)
        if update_fields:
            update_fields.append("updated_at")
            case.save(update_fields=update_fields)

        return CaseWorkflowService.transition_state(
            case, CaseStatus.CADET_REVIEW, requesting_user
        )

    @staticmethod
    @transaction.atomic
    def process_cadet_review(
        case: Case,
        decision: str,
        message: str,
        requesting_user: Any,
    ) -> Case:
        """
        **Cadet approves or rejects a complaint-sourced case.**

        Decision ``"approve"`` → ``OFFICER_REVIEW``.
        Decision ``"reject"``  → ``RETURNED_TO_COMPLAINANT`` (rejection
        message sent back to complainant); auto-voids if ``rejection_count``
        reaches ``MAX_REJECTION_COUNT``.

        Parameters
        ----------
        case : Case
            Case in ``CADET_REVIEW`` status.
        decision : str
            ``"approve"`` or ``"reject"``.
        message : str
            Required when decision is ``"reject"``.
        requesting_user : User
            Must have ``CAN_REVIEW_COMPLAINT`` permission.

        Returns
        -------
        Case
            Updated case.

        Raises
        ------
        django.core.exceptions.ValidationError
            If ``decision`` is ``"reject"`` and ``message`` is blank.
        django.core.exceptions.ValidationError
            If the case is already ``VOIDED``.

        Implementation Contract
        -----------------------
        1. Assert case.status == CADET_REVIEW.
        2. Assert permission.
        3. If decision == "reject":
           a. case.rejection_count += 1
           b. case.save(update_fields=["rejection_count", "updated_at"])
           c. If rejection_count >= MAX_REJECTION_COUNT:
              transition_state(case, VOIDED, requesting_user, message)
           else:
              transition_state(case, RETURNED_TO_COMPLAINANT, requesting_user, message)
        4. If decision == "approve":
           transition_state(case, OFFICER_REVIEW, requesting_user)
        5. Return case.
        """
        if case.status != CaseStatus.CADET_REVIEW:
            raise InvalidTransition(
                current=case.status,
                target="approve/reject",
                reason="Case must be in CADET_REVIEW status for cadet review.",
            )

        if not requesting_user.has_perm(f"cases.{CasesPerms.CAN_REVIEW_COMPLAINT}"):
            raise PermissionDenied(
                "You do not have permission to review complaints."
            )

        if decision == "reject":
            # Lock the row before modifying rejection_count
            case = Case.objects.select_for_update().get(pk=case.pk)
            case.rejection_count += 1
            case.save(update_fields=["rejection_count", "updated_at"])

            if case.rejection_count >= MAX_REJECTION_COUNT:
                case = CaseWorkflowService.transition_state(
                    case, CaseStatus.VOIDED, requesting_user, message,
                )
            else:
                case = CaseWorkflowService.transition_state(
                    case, CaseStatus.RETURNED_TO_COMPLAINANT, requesting_user, message,
                )
        else:
            # approve
            case = CaseWorkflowService.transition_state(
                case, CaseStatus.OFFICER_REVIEW, requesting_user,
            )

        return case

    @staticmethod
    @transaction.atomic
    def process_officer_review(
        case: Case,
        decision: str,
        message: str,
        requesting_user: Any,
    ) -> Case:
        """
        **Officer approves or rejects a complaint forwarded by the Cadet.**

        Decision ``"approve"`` → ``OPEN``.
        Decision ``"reject"``  → ``RETURNED_TO_CADET`` (does NOT increment
        ``rejection_count``; rejection is addressed by the Cadet, not
        the complainant directly per §4.2.1).

        Parameters
        ----------
        case : Case
            Case in ``OFFICER_REVIEW`` status.
        decision : str
            ``"approve"`` or ``"reject"``.
        message : str
            Required when decision is ``"reject"``.
        requesting_user : User
            Must have ``CAN_APPROVE_CASE`` permission.

        Returns
        -------
        Case
            Updated case with ``approved_by`` set on approval.

        Implementation Contract
        -----------------------
        1. Assert case.status == OFFICER_REVIEW.
        2. Assert requesting_user.has_perm("cases.can_approve_case").
        3. If "approve": set case.approved_by = requesting_user; transition to OPEN.
        4. If "reject": transition to RETURNED_TO_CADET with message.
        5. Return case.
        """
        if case.status != CaseStatus.OFFICER_REVIEW:
            raise InvalidTransition(
                current=case.status,
                target="approve/reject",
                reason="Case must be in OFFICER_REVIEW status for officer review.",
            )

        if not requesting_user.has_perm(f"cases.{CasesPerms.CAN_APPROVE_CASE}"):
            raise PermissionDenied(
                "You do not have permission to approve or reject cases."
            )

        if decision == "approve":
            case = Case.objects.select_for_update().get(pk=case.pk)
            case.approved_by = requesting_user
            case.save(update_fields=["approved_by", "updated_at"])
            case = CaseWorkflowService.transition_state(
                case, CaseStatus.OPEN, requesting_user,
            )
        else:
            # reject → return to cadet
            case = CaseWorkflowService.transition_state(
                case, CaseStatus.RETURNED_TO_CADET, requesting_user, message,
            )

        return case

    @staticmethod
    @transaction.atomic
    def approve_crime_scene_case(
        case: Case,
        requesting_user: Any,
    ) -> Case:
        """
        **Superior approves a crime-scene case pending approval.**

        Transitions: ``PENDING_APPROVAL`` → ``OPEN``.
        Only one superior's approval is needed (§4.2.2).

        Parameters
        ----------
        case : Case
            Case in ``PENDING_APPROVAL`` status with
            ``creation_type == CRIME_SCENE``.
        requesting_user : User
            Must have ``CAN_APPROVE_CASE`` and rank ≥ Officer.

        Returns
        -------
        Case
            Opened case.

        Implementation Contract
        -----------------------
        1. Assert case.status == PENDING_APPROVAL.
        2. Assert case.creation_type == CRIME_SCENE.
        3. Set case.approved_by = requesting_user.
        4. transition_state(case, OPEN, requesting_user).
        5. Return case.
        """
        if case.status != CaseStatus.PENDING_APPROVAL:
            raise InvalidTransition(
                current=case.status,
                target=CaseStatus.OPEN,
                reason="Case must be in PENDING_APPROVAL status.",
            )

        if case.creation_type != CaseCreationType.CRIME_SCENE:
            raise DomainError(
                "Only crime-scene cases can be approved via this endpoint."
            )

        # Set approved_by before transitioning
        case = Case.objects.select_for_update().get(pk=case.pk)
        case.approved_by = requesting_user
        case.save(update_fields=["approved_by", "updated_at"])

        return CaseWorkflowService.transition_state(
            case, CaseStatus.OPEN, requesting_user,
            message="Crime-scene case approved by superior.",
        )

    @staticmethod
    @transaction.atomic
    def declare_suspects_identified(
        case: Case,
        requesting_user: Any,
    ) -> Case:
        """
        **Detective declares the primary suspects and moves the case to
        Sergeant review.**

        Transitions: ``INVESTIGATION`` → ``SUSPECT_IDENTIFIED`` →
        (immediately or via a second call) ``SERGEANT_REVIEW``.

        In this draft the two transitions are combined: the detective calls
        this method once after linking suspects via the suspects app.

        Parameters
        ----------
        case : Case
            Case in ``INVESTIGATION`` status.
        requesting_user : User
            Must be ``case.assigned_detective``.

        Returns
        -------
        Case
            Case moved to ``SERGEANT_REVIEW``.

        Implementation Contract
        -----------------------
        1. Assert case.status == INVESTIGATION.
        2. Assert requesting_user == case.assigned_detective.
        3. transition_state(case, SUSPECT_IDENTIFIED, requesting_user).
        4. transition_state(case, SERGEANT_REVIEW, requesting_user).
        5. Return case.
        """
        if case.status != CaseStatus.INVESTIGATION:
            raise InvalidTransition(
                current=case.status,
                target=CaseStatus.SUSPECT_IDENTIFIED,
                reason="Case must be in INVESTIGATION status.",
            )

        if requesting_user != case.assigned_detective:
            raise PermissionDenied(
                "Only the assigned detective can declare suspects."
            )

        case = CaseWorkflowService.transition_state(
            case, CaseStatus.SUSPECT_IDENTIFIED, requesting_user,
        )
        case = CaseWorkflowService.transition_state(
            case, CaseStatus.SERGEANT_REVIEW, requesting_user,
        )
        return case

    @staticmethod
    @transaction.atomic
    def process_sergeant_review(
        case: Case,
        decision: str,
        message: str,
        requesting_user: Any,
    ) -> Case:
        """
        **Sergeant approves or rejects the detective's suspect declaration.**

        Decision ``"approve"`` → ``ARREST_ORDERED``.
        Decision ``"reject"``  → ``INVESTIGATION`` (case returned to detective
        with a rejection message, per §4.4).

        Parameters
        ----------
        case : Case
            Case in ``SERGEANT_REVIEW`` status.
        decision : str
            ``"approve"`` or ``"reject"``.
        message : str
            Required on rejection (the objection returned to detective).
        requesting_user : User
            Must be ``case.assigned_sergeant`` and have
            ``CAN_CHANGE_CASE_STATUS`` permission.

        Returns
        -------
        Case
            Updated case.

        Implementation Contract
        -----------------------
        1. Assert case.status == SERGEANT_REVIEW.
        2. Assert requesting_user == case.assigned_sergeant.
        3. If "approve": transition to ARREST_ORDERED.
        4. If "reject":  transition to INVESTIGATION with non-blank message.
        5. Return case.
        """
        if case.status != CaseStatus.SERGEANT_REVIEW:
            raise InvalidTransition(
                current=case.status,
                target="approve/reject",
                reason="Case must be in SERGEANT_REVIEW status.",
            )

        if requesting_user != case.assigned_sergeant:
            raise PermissionDenied(
                "Only the assigned sergeant can perform this review."
            )

        if decision == "approve":
            case = CaseWorkflowService.transition_state(
                case, CaseStatus.ARREST_ORDERED, requesting_user,
            )
        else:
            case = CaseWorkflowService.transition_state(
                case, CaseStatus.INVESTIGATION, requesting_user, message,
            )
        return case

    @staticmethod
    @transaction.atomic
    def forward_to_judiciary(
        case: Case,
        requesting_user: Any,
    ) -> Case:
        """
        **Captain (or Chief for critical cases) forwards the case to the
        judiciary system.**

        Transitions:
        - Non-critical: ``CAPTAIN_REVIEW`` → ``JUDICIARY``
        - Critical:     ``CHIEF_REVIEW``   → ``JUDICIARY``

        Parameters
        ----------
        case : Case
            Case in ``CAPTAIN_REVIEW`` or ``CHIEF_REVIEW``.
        requesting_user : User
            Must have ``CAN_FORWARD_TO_JUDICIARY``; for critical cases also
            needs ``CAN_APPROVE_CRITICAL_CASE``.

        Returns
        -------
        Case
            Case now in ``JUDICIARY`` status.

        Implementation Contract
        -----------------------
        1. Assert case.status in (CAPTAIN_REVIEW, CHIEF_REVIEW).
        2. If case.status == CAPTAIN_REVIEW and case.crime_level == CRITICAL:
           transition to CHIEF_REVIEW first.
        3. transition_state(case, JUDICIARY, requesting_user).
        4. Return case.
        """
        if case.status not in (CaseStatus.CAPTAIN_REVIEW, CaseStatus.CHIEF_REVIEW):
            raise InvalidTransition(
                current=case.status,
                target=CaseStatus.JUDICIARY,
                reason="Case must be in CAPTAIN_REVIEW or CHIEF_REVIEW.",
            )

        # Critical cases must go through CHIEF_REVIEW first
        if (
            case.status == CaseStatus.CAPTAIN_REVIEW
            and case.crime_level == CrimeLevel.CRITICAL
        ):
            case = CaseWorkflowService.transition_state(
                case, CaseStatus.CHIEF_REVIEW, requesting_user,
            )

        case = CaseWorkflowService.transition_state(
            case, CaseStatus.JUDICIARY, requesting_user,
        )
        return case

    @staticmethod
    def _dispatch_notifications(
        case: Case,
        new_status: str,
        actor: Any,
    ) -> None:
        """
        Dispatch ``Notification`` records to relevant users after a
        status transition.

        Called internally by ``transition_state``.  Must NOT be called
        directly from views.

        Notification routing table (to be implemented):
        ┌──────────────────────────┬────────────────────────────────────┐
        │ new_status               │ recipient(s)                       │
        ├──────────────────────────┼────────────────────────────────────┤
        │ RETURNED_TO_COMPLAINANT  │ primary complainant                │
        │ OFFICER_REVIEW           │ assigned officer / first officer   │
        │ OPEN                     │ case created_by                    │
        │ INVESTIGATION            │ assigned_detective                 │
        │ SUSPECT_IDENTIFIED       │ assigned_sergeant                  │
        │ SERGEANT_REVIEW          │ assigned_sergeant                  │
        │ ARREST_ORDERED           │ assigned_detective                 │
        │ CAPTAIN_REVIEW           │ assigned_captain                   │
        │ CHIEF_REVIEW             │ police chief                       │
        │ JUDICIARY                │ assigned_judge                     │
        │ CLOSED                   │ case created_by, detective         │
        └──────────────────────────┴────────────────────────────────────┘

        Implementation Contract
        -----------------------
        Import and use ``core.models.Notification`` to create records.
        Do NOT send push/email here — that belongs in a Celery task
        triggered after the transaction commits.
        """
        recipients = []
        event_type = "case_status_changed"

        if new_status == CaseStatus.RETURNED_TO_COMPLAINANT:
            primary = case.complainants.filter(
                is_primary=True,
            ).select_related("user").first()
            if primary:
                recipients = [primary.user]
            event_type = "complaint_returned"

        elif new_status == CaseStatus.VOIDED:
            primary = case.complainants.filter(
                is_primary=True,
            ).select_related("user").first()
            if primary:
                recipients = [primary.user]
            event_type = "case_rejected"

        elif new_status == CaseStatus.OPEN:
            if case.created_by:
                recipients = [case.created_by]
            event_type = "case_approved"

        elif new_status == CaseStatus.RETURNED_TO_CADET:
            event_type = "case_rejected"

        elif new_status == CaseStatus.INVESTIGATION:
            if case.assigned_detective:
                recipients = [case.assigned_detective]
            event_type = "assignment_changed"

        elif new_status in (
            CaseStatus.SUSPECT_IDENTIFIED,
            CaseStatus.SERGEANT_REVIEW,
        ):
            if case.assigned_sergeant:
                recipients = [case.assigned_sergeant]

        elif new_status == CaseStatus.ARREST_ORDERED:
            if case.assigned_detective:
                recipients = [case.assigned_detective]

        elif new_status == CaseStatus.CAPTAIN_REVIEW:
            if case.assigned_captain:
                recipients = [case.assigned_captain]

        elif new_status == CaseStatus.JUDICIARY:
            if case.assigned_judge:
                recipients = [case.assigned_judge]

        elif new_status == CaseStatus.CLOSED:
            close_recipients = []
            if case.created_by:
                close_recipients.append(case.created_by)
            if case.assigned_detective:
                close_recipients.append(case.assigned_detective)
            recipients = close_recipients

        if recipients:
            NotificationService.create(
                actor=actor,
                recipients=recipients,
                event_type=event_type,
                related_object=case,
            )


# ═══════════════════════════════════════════════════════════════════
#  Case Assignment Service
# ═══════════════════════════════════════════════════════════════════


class CaseAssignmentService:
    """
    Manages assignment of personnel roles (detective, sergeant,
    captain, judge) to a case.
    """

    @staticmethod
    @transaction.atomic
    def assign_detective(
        case: Case,
        detective: Any,
        requesting_user: Any,
    ) -> Case:
        """
        Assign a detective to an open case and move it to ``INVESTIGATION``.

        Parameters
        ----------
        case : Case
            Must be in ``OPEN`` status.
        detective : User
            The user to assign.  Must hold the ``Detective`` role.
        requesting_user : User
            Must have ``CAN_ASSIGN_DETECTIVE`` permission.

        Returns
        -------
        Case
            Updated case with ``assigned_detective`` set and status
            transitioned to ``INVESTIGATION``.

        Raises
        ------
        PermissionError
            If ``requesting_user`` lacks assignment permission.
        django.core.exceptions.ValidationError
            If ``detective`` does not have the ``Detective`` role,
            or ``case.status != OPEN``.

        Implementation Contract
        -----------------------
        1. Assert permission.
        2. Assert case.status == OPEN.
        3. Assert detective has "Detective" role.
        4. case.assigned_detective = detective.
        5. case.save(update_fields=["assigned_detective", "updated_at"]).
        6. CaseWorkflowService.transition_state(case, INVESTIGATION, requesting_user).
        7. Return case.
        """
        if not requesting_user.has_perm(f"cases.{CasesPerms.CAN_ASSIGN_DETECTIVE}"):
            raise PermissionDenied(
                "You do not have permission to assign a detective."
            )

        if case.status != CaseStatus.OPEN:
            raise InvalidTransition(
                current=case.status,
                target=CaseStatus.INVESTIGATION,
                reason="Case must be in OPEN status to assign a detective.",
            )

        detective_role = get_user_role_name(detective)
        if detective_role != "detective":
            raise DomainError(
                "The assigned user must hold the 'Detective' role."
            )

        case = Case.objects.select_for_update().get(pk=case.pk)
        case.assigned_detective = detective
        case.save(update_fields=["assigned_detective", "updated_at"])

        case = CaseWorkflowService.transition_state(
            case, CaseStatus.INVESTIGATION, requesting_user,
        )

        # Notify the detective of their assignment
        NotificationService.create(
            actor=requesting_user,
            recipients=[detective],
            event_type="assignment_changed",
            related_object=case,
        )

        return case

    @staticmethod
    @transaction.atomic
    def assign_sergeant(
        case: Case,
        sergeant: Any,
        requesting_user: Any,
    ) -> Case:
        """
        Assign a sergeant to the case.

        Parameters
        ----------
        case : Case
        sergeant : User
            Must hold the ``Sergeant`` role.
        requesting_user : User
            Must have ``CAN_ASSIGN_DETECTIVE`` permission (or a dedicated
            assign-sergeant permission if added later).

        Returns
        -------
        Case
            Updated case.

        Implementation Contract
        -----------------------
        1. Assert permission.
        2. Assert sergeant has "Sergeant" role.
        3. case.assigned_sergeant = sergeant.
        4. case.save(update_fields=["assigned_sergeant", "updated_at"]).
        5. Return case.
        """
        if not requesting_user.has_perm(f"cases.{CasesPerms.CAN_ASSIGN_DETECTIVE}"):
            raise PermissionDenied(
                "You do not have permission to assign a sergeant."
            )

        sergeant_role = get_user_role_name(sergeant)
        if sergeant_role != "sergeant":
            raise DomainError(
                "The assigned user must hold the 'Sergeant' role."
            )

        case = Case.objects.select_for_update().get(pk=case.pk)
        case.assigned_sergeant = sergeant
        case.save(update_fields=["assigned_sergeant", "updated_at"])

        # Log the assignment
        CaseStatusLog.objects.create(
            case=case,
            from_status=case.status,
            to_status=case.status,
            changed_by=requesting_user,
            message=f"Sergeant {sergeant.get_full_name()} assigned to case.",
        )

        NotificationService.create(
            actor=requesting_user,
            recipients=[sergeant],
            event_type="assignment_changed",
            related_object=case,
        )

        return case

    @staticmethod
    @transaction.atomic
    def assign_captain(
        case: Case,
        captain: Any,
        requesting_user: Any,
    ) -> Case:
        """
        Assign a captain to the case.

        Parameters
        ----------
        case : Case
        captain : User
            Must hold the ``Captain`` role.
        requesting_user : User

        Returns
        -------
        Case
            Updated case.

        Implementation Contract
        -----------------------
        Same pattern as ``assign_sergeant`` with role = "Captain".
        """
        if not requesting_user.has_perm(f"cases.{CasesPerms.CAN_ASSIGN_DETECTIVE}"):
            raise PermissionDenied(
                "You do not have permission to assign a captain."
            )

        captain_role = get_user_role_name(captain)
        if captain_role != "captain":
            raise DomainError(
                "The assigned user must hold the 'Captain' role."
            )

        case = Case.objects.select_for_update().get(pk=case.pk)
        case.assigned_captain = captain
        case.save(update_fields=["assigned_captain", "updated_at"])

        CaseStatusLog.objects.create(
            case=case,
            from_status=case.status,
            to_status=case.status,
            changed_by=requesting_user,
            message=f"Captain {captain.get_full_name()} assigned to case.",
        )

        NotificationService.create(
            actor=requesting_user,
            recipients=[captain],
            event_type="assignment_changed",
            related_object=case,
        )

        return case

    @staticmethod
    @transaction.atomic
    def assign_judge(
        case: Case,
        judge: Any,
        requesting_user: Any,
    ) -> Case:
        """
        Assign a judge to the case (used when forwarding to judiciary).

        Parameters
        ----------
        case : Case
            Typically in ``JUDICIARY`` status.
        judge : User
            Must hold the ``Judge`` role.
        requesting_user : User
            Must have ``CAN_FORWARD_TO_JUDICIARY``.

        Returns
        -------
        Case
            Updated case.
        """
        if not requesting_user.has_perm(f"cases.{CasesPerms.CAN_FORWARD_TO_JUDICIARY}"):
            raise PermissionDenied(
                "You do not have permission to assign a judge."
            )

        judge_role = get_user_role_name(judge)
        if judge_role != "judge":
            raise DomainError(
                "The assigned user must hold the 'Judge' role."
            )

        case = Case.objects.select_for_update().get(pk=case.pk)
        case.assigned_judge = judge
        case.save(update_fields=["assigned_judge", "updated_at"])

        CaseStatusLog.objects.create(
            case=case,
            from_status=case.status,
            to_status=case.status,
            changed_by=requesting_user,
            message=f"Judge {judge.get_full_name()} assigned to case.",
        )

        NotificationService.create(
            actor=requesting_user,
            recipients=[judge],
            event_type="assignment_changed",
            related_object=case,
        )

    @staticmethod
    @transaction.atomic
    def unassign_role(
        case: Case,
        role_field: str,
        requesting_user: Any,
    ) -> Case:
        """
        Remove a personnel assignment from a case.

        Parameters
        ----------
        case : Case
        role_field : str
            One of ``"assigned_detective"``, ``"assigned_sergeant"``,
            ``"assigned_captain"``, ``"assigned_judge"``.
        requesting_user : User
            Must have appropriate permission.

        Returns
        -------
        Case
            Updated case with the specified field set to ``None``.

        Implementation Contract
        -----------------------
        1. Assert role_field in VALID_ROLE_FIELDS.
        2. setattr(case, role_field, None).
        3. case.save(update_fields=[role_field, "updated_at"]).
        4. Return case.
        """
        if role_field not in _VALID_ROLE_FIELDS:
            raise DomainError(
                f"Invalid role field: {role_field}. "
                f"Must be one of {_VALID_ROLE_FIELDS}."
            )

        if not requesting_user.has_perm(f"cases.{CasesPerms.CAN_ASSIGN_DETECTIVE}"):
            raise PermissionDenied(
                "You do not have permission to unassign personnel."
            )

        case = Case.objects.select_for_update().get(pk=case.pk)
        setattr(case, role_field, None)
        case.save(update_fields=[role_field, "updated_at"])

        CaseStatusLog.objects.create(
            case=case,
            from_status=case.status,
            to_status=case.status,
            changed_by=requesting_user,
            message=f"{role_field.replace('assigned_', '').title()} unassigned from case.",
        )

        return case


# ═══════════════════════════════════════════════════════════════════
#  Case Complainant Service
# ═══════════════════════════════════════════════════════════════════


class CaseComplainantService:
    """
    Manages the registration and review of complainants on a case.
    """

    @staticmethod
    @transaction.atomic
    def add_complainant(
        case: Case,
        user: Any,
        requesting_user: Any,
        is_primary: bool = False,
    ) -> CaseComplainant:
        """
        Link an additional complainant to an existing case.

        Parameters
        ----------
        case : Case
        user : User
            The complainant to add.
        requesting_user : User
            Must have ``ADD_CASECOMPLAINANT`` permission or be an admin.
        is_primary : bool
            Should only be ``True`` for the initial complainant (usually
            set automatically on creation).

        Returns
        -------
        CaseComplainant
            The newly created junction record.

        Raises
        ------
        django.core.exceptions.ValidationError
            If ``user`` is already registered as a complainant on ``case``.

        Implementation Contract
        -----------------------
        1. Guard permission.
        2. Check uniqueness: ``CaseComplainant.objects.filter(case=case, user=user).exists()``.
        3. ``CaseComplainant.objects.create(case=case, user=user, is_primary=is_primary)``.
        4. Return the created record.
        """
        if not (
            requesting_user.has_perm(f"cases.{CasesPerms.ADD_CASECOMPLAINANT}")
            or requesting_user.is_staff
        ):
            raise PermissionDenied(
                "You do not have permission to add complainants."
            )

        if CaseComplainant.objects.filter(case=case, user=user).exists():
            raise DomainError(
                "This user is already registered as a complainant on this case."
            )

        complainant = CaseComplainant.objects.create(
            case=case,
            user=user,
            is_primary=is_primary,
        )
        return complainant

    @staticmethod
    @transaction.atomic
    def review_complainant(
        complainant: CaseComplainant,
        decision: str,
        requesting_user: Any,
    ) -> CaseComplainant:
        """
        **Cadet approves or rejects an individual complainant's information.**

        Parameters
        ----------
        complainant : CaseComplainant
            The record to review.
        decision : str
            ``"approve"`` or ``"reject"``.
        requesting_user : User
            Must have ``CAN_REVIEW_COMPLAINT`` permission.

        Returns
        -------
        CaseComplainant
            Updated record with new ``status`` and ``reviewed_by`` set.

        Implementation Contract
        -----------------------
        1. Assert permission.
        2. status_map = {"approve": ComplainantStatus.APPROVED, "reject": ComplainantStatus.REJECTED}.
        3. complainant.status = status_map[decision].
        4. complainant.reviewed_by = requesting_user.
        5. complainant.save(update_fields=["status", "reviewed_by", "updated_at"]).
        6. Return complainant.
        """
        if not requesting_user.has_perm(f"cases.{CasesPerms.CAN_REVIEW_COMPLAINT}"):
            raise PermissionDenied(
                "You do not have permission to review complainants."
            )

        status_map = {
            "approve": ComplainantStatus.APPROVED,
            "reject": ComplainantStatus.REJECTED,
        }
        complainant.status = status_map[decision]
        complainant.reviewed_by = requesting_user
        complainant.save(update_fields=["status", "reviewed_by", "updated_at"])
        return complainant


# ═══════════════════════════════════════════════════════════════════
#  Case Witness Service
# ═══════════════════════════════════════════════════════════════════


class CaseWitnessService:
    """
    Manages witness registration on crime-scene cases.
    """

    @staticmethod
    @transaction.atomic
    def add_witness(
        case: Case,
        validated_data: dict[str, Any],
        requesting_user: Any,
    ) -> CaseWitness:
        """
        Add a witness to a case.

        Parameters
        ----------
        case : Case
        validated_data : dict
            Cleaned data from ``CaseWitnessCreateSerializer``
            (fields: ``full_name``, ``phone_number``, ``national_id``).
        requesting_user : User
            Must have write access to the case.

        Returns
        -------
        CaseWitness
            The created witness record.

        Implementation Contract
        -----------------------
        1. Assert case is not CLOSED / VOIDED.
        2. ``CaseWitness.objects.create(case=case, **validated_data)``.
        3. Return the witness.
        """
        if case.status in (CaseStatus.CLOSED, CaseStatus.VOIDED):
            raise DomainError(
                "Cannot add witnesses to a closed or voided case."
            )

        # Validate phone number format
        phone = validated_data.get("phone_number", "")
        if not _PHONE_REGEX.match(phone):
            raise DomainError(
                "Phone number must be 7-15 digits, optionally prefixed with '+'."
            )

        # Validate national_id (10 digits)
        national_id = validated_data.get("national_id", "")
        if not national_id.isdigit() or len(national_id) != 10:
            raise DomainError(
                "National ID must be exactly 10 digits."
            )

        witness = CaseWitness.objects.create(case=case, **validated_data)
        return witness


# ═══════════════════════════════════════════════════════════════════
#  Case Calculation Service
# ═══════════════════════════════════════════════════════════════════


class CaseCalculationService:
    """
    Houses the two core formulas from project-doc §4.7.

    **Delegates all math** to ``core.services.RewardCalculatorService``
    to maintain a single source of truth.  This class provides
    case-specific convenience wrappers.

    Formula context
    ---------------
    The formulas require two inputs:
    - **L_j** = the integer crime-level degree of the case
      (``CrimeLevel`` value: 1 = Level3, 2 = Level2, 3 = Level1, 4 = Critical).
    - **D_i** = max days for which a suspect has been in "wanted" status
      on any **open case** (computed across the suspects app).

    At the *case* level (this service), we use:
    - ``L_j`` = ``case.crime_level`` (the degree integer from ``CrimeLevel``).
    - ``D_i`` = days elapsed since ``case.created_at`` (approximate proxy
      until the suspects app provides the exact wanted timestamp).

    Final formula resolution must be re-evaluated once the suspects app
    exposes ``Suspect.wanted_since`` via a service call.
    """

    @staticmethod
    def calculate_tracking_threshold(case: Case) -> int:
        """
        Compute the **Most-Wanted Tracking Threshold** for one case.

        Formula (project-doc §4.7 Note 1)::

            threshold = case.crime_level × days_since_creation

        Delegates to ``RewardCalculatorService.compute_case_tracking_threshold``.

        Parameters
        ----------
        case : Case
            The case to compute the threshold for.

        Returns
        -------
        int
            The tracking threshold value.
        """
        from core.services import RewardCalculatorService

        days = max((timezone.now().date() - case.created_at.date()).days, 0)
        return RewardCalculatorService.compute_case_tracking_threshold(
            case.crime_level, days,
        )

    @staticmethod
    def calculate_reward(case: Case) -> int:
        """
        Compute the **Bounty Reward** for information leading to a suspect
        on this case.

        Formula (project-doc §4.7 Note 2)::

            reward = threshold × 20,000,000  (Rials)

        Delegates to ``RewardCalculatorService.compute_case_reward``.

        Parameters
        ----------
        case : Case
            The case to compute the reward for.

        Returns
        -------
        int
            The reward amount in Rials.
        """
        from core.services import RewardCalculatorService

        days = max((timezone.now().date() - case.created_at.date()).days, 0)
        return RewardCalculatorService.compute_case_reward(
            case.crime_level, days,
        )

    @staticmethod
    def get_calculations_dict(case: Case) -> dict[str, int]:
        """
        Return both computed values as a dict for the API response.

        Parameters
        ----------
        case : Case

        Returns
        -------
        dict
            ``{"tracking_threshold": <int>, "reward_rials": <int>,
               "crime_level_degree": <int>, "days_since_creation": <int>}``
        """
        degree = case.crime_level
        days = max((timezone.now().date() - case.created_at.date()).days, 0)
        threshold = CaseCalculationService.calculate_tracking_threshold(case)
        reward = CaseCalculationService.calculate_reward(case)
        return {
            "crime_level_degree": degree,
            "days_since_creation": days,
            "tracking_threshold": threshold,
            "reward_rials": reward,
        }


# ═══════════════════════════════════════════════════════════════════
#  Case Reporting Service
# ═══════════════════════════════════════════════════════════════════


class CaseReportingService:
    """
    Aggregates a comprehensive case report for the judiciary / senior
    officers (project-doc §4.6, §5.7).

    The Judge, Captain, and Police Chief need a consolidated view that
    includes every sub-resource attached to a case:
      - Case main fields + status history (``CaseStatusLog``)
      - Linked complainants and witnesses
      - Summary of all linked evidence (metadata, no raw blobs)
      - Linked suspects (status, interrogation summaries, approval trails)
      - Involved personnel assignments

    Access is restricted to users whose role is Judge, Captain,
    Police Chief, or System Administrator.
    """

    #: Roles that are allowed to pull the full case report.
    _REPORT_ALLOWED_ROLES: frozenset[str] = frozenset({
        "judge",
        "captain",
        "police_chief",
        "system_administrator",
    })

    @classmethod
    def get_case_report(cls, user: Any, case_id: int) -> dict[str, Any]:
        """
        Build and return a comprehensive case report dictionary.

        Parameters
        ----------
        user : User
            The requesting user.  Must have an allowed role.
        case_id : int
            Primary key of the case to report on.

        Returns
        -------
        dict
            A structured dictionary containing all aggregated data.

        Raises
        ------
        core.domain.exceptions.PermissionDenied
            If the user's role is not in ``_REPORT_ALLOWED_ROLES``.
        core.domain.exceptions.NotFound
            If the case does not exist.
        """
        # ── Access enforcement ──────────────────────────────────────
        role_name = get_user_role_name(user)
        if role_name not in cls._REPORT_ALLOWED_ROLES and not user.is_superuser:
            raise PermissionDenied(
                "Only a Judge, Captain, or Police Chief may access "
                "the full case report."
            )

        # ── Fetch the case with all related data ────────────────────
        try:
            case = (
                Case.objects
                .select_related(
                    "created_by",
                    "approved_by",
                    "assigned_detective",
                    "assigned_sergeant",
                    "assigned_captain",
                    "assigned_judge",
                )
                .prefetch_related(
                    Prefetch(
                        "complainants",
                        queryset=CaseComplainant.objects.select_related(
                            "user", "reviewed_by",
                        ),
                    ),
                    "witnesses",
                    Prefetch(
                        "status_logs",
                        queryset=CaseStatusLog.objects.select_related(
                            "changed_by",
                        ).order_by("created_at"),
                    ),
                )
                .get(pk=case_id)
            )
        except Case.DoesNotExist:
            raise NotFound(f"Case #{case_id} not found.")

        # ── Lazy-import cross-app models to avoid circular deps ─────
        from evidence.models import Evidence
        from suspects.models import Interrogation, Suspect, Trial

        # ── Evidence summary (metadata only, no raw file blobs) ─────
        evidences_qs = (
            Evidence.objects
            .filter(case=case)
            .select_related("registered_by")
            .order_by("-created_at")
        )
        evidence_list = []
        for ev in evidences_qs:
            evidence_list.append({
                "id": ev.id,
                "evidence_type": ev.evidence_type,
                "title": ev.title,
                "description": ev.description,
                "registered_by": _user_summary(ev.registered_by),
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
            })

        # ── Suspects with interrogation & trial summaries ───────────
        suspects_qs = (
            Suspect.objects
            .filter(case=case)
            .select_related("identified_by", "approved_by_sergeant", "user")
            .prefetch_related(
                Prefetch(
                    "interrogations",
                    queryset=Interrogation.objects.select_related(
                        "detective", "sergeant",
                    ).order_by("-created_at"),
                ),
                Prefetch(
                    "trials",
                    queryset=Trial.objects.select_related("judge").order_by("-created_at"),
                ),
            )
            .order_by("-wanted_since")
        )
        suspects_list = []
        for s in suspects_qs:
            interrogation_summaries = [
                {
                    "id": i.id,
                    "detective": _user_summary(i.detective),
                    "sergeant": _user_summary(i.sergeant),
                    "detective_guilt_score": i.detective_guilt_score,
                    "sergeant_guilt_score": i.sergeant_guilt_score,
                    "notes": i.notes,
                    "created_at": i.created_at.isoformat() if i.created_at else None,
                }
                for i in s.interrogations.all()
            ]
            trial_summaries = [
                {
                    "id": t.id,
                    "judge": _user_summary(t.judge),
                    "verdict": t.verdict,
                    "punishment_title": t.punishment_title,
                    "punishment_description": t.punishment_description,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in s.trials.all()
            ]
            suspects_list.append({
                "id": s.id,
                "full_name": s.full_name,
                "national_id": s.national_id,
                "status": s.status,
                "status_display": s.get_status_display(),
                "wanted_since": s.wanted_since.isoformat() if s.wanted_since else None,
                "days_wanted": s.days_wanted,
                "identified_by": _user_summary(s.identified_by),
                "sergeant_approval_status": s.sergeant_approval_status,
                "approved_by_sergeant": _user_summary(s.approved_by_sergeant),
                "sergeant_rejection_message": s.sergeant_rejection_message,
                "interrogations": interrogation_summaries,
                "trials": trial_summaries,
            })

        # ── Complainants ────────────────────────────────────────────
        complainants_list = [
            {
                "id": c.id,
                "user": _user_summary(c.user),
                "is_primary": c.is_primary,
                "status": c.status,
                "reviewed_by": _user_summary(c.reviewed_by),
            }
            for c in case.complainants.all()
        ]

        # ── Witnesses ──────────────────────────────────────────────
        witnesses_list = [
            {
                "id": w.id,
                "full_name": w.full_name,
                "phone_number": w.phone_number,
                "national_id": w.national_id,
            }
            for w in case.witnesses.all()
        ]

        # ── Status history (full audit trail) ──────────────────────
        status_history = [
            {
                "id": log.id,
                "from_status": log.from_status,
                "to_status": log.to_status,
                "changed_by": _user_summary(log.changed_by),
                "message": log.message,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in case.status_logs.all()
        ]

        # ── Personnel assignments ──────────────────────────────────
        personnel = {
            "created_by": _user_summary(case.created_by),
            "approved_by": _user_summary(case.approved_by),
            "assigned_detective": _user_summary(case.assigned_detective),
            "assigned_sergeant": _user_summary(case.assigned_sergeant),
            "assigned_captain": _user_summary(case.assigned_captain),
            "assigned_judge": _user_summary(case.assigned_judge),
        }

        # ── Calculations ───────────────────────────────────────────
        calculations = CaseCalculationService.get_calculations_dict(case)

        return {
            "case": {
                "id": case.id,
                "title": case.title,
                "description": case.description,
                "crime_level": case.crime_level,
                "crime_level_display": case.get_crime_level_display(),
                "status": case.status,
                "status_display": case.get_status_display(),
                "creation_type": case.creation_type,
                "rejection_count": case.rejection_count,
                "incident_date": case.incident_date.isoformat() if case.incident_date else None,
                "location": case.location,
                "created_at": case.created_at.isoformat() if case.created_at else None,
                "updated_at": case.updated_at.isoformat() if case.updated_at else None,
            },
            "personnel": personnel,
            "complainants": complainants_list,
            "witnesses": witnesses_list,
            "evidence": evidence_list,
            "suspects": suspects_list,
            "status_history": status_history,
            "calculations": calculations,
        }


def _user_summary(user: Any) -> dict[str, Any] | None:
    """Return a compact user dict, or ``None`` if user is None."""
    if user is None:
        return None
    role_name = None
    if hasattr(user, "role") and user.role:
        role_name = user.role.name
    return {
        "id": user.id,
        "full_name": user.get_full_name() or str(user),
        "role": role_name,
    }
