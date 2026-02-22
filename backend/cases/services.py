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
from typing import Any

from django.db import transaction
from django.db.models import Count, Max, Q, QuerySet
from django.utils import timezone

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

# Reward multiplier defined in project-doc §4.7 Note 2.
_REWARD_MULTIPLIER: int = 20_000_000  # Rials


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


class CaseQueryService:
    """
    Constructs filtered, annotated querysets for listing cases.

    All heavy query concerns (filter assembly, annotation, ordering)
    live here so the view stays thin.
    """

    @staticmethod
    def get_filtered_queryset(
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
            Supported keys:
            - ``status``         : str  (``CaseStatus`` value)
            - ``crime_level``    : int  (``CrimeLevel`` value)
            - ``detective``      : int  (user PK)
            - ``creation_type``  : str  (``CaseCreationType`` value)
            - ``created_after``  : date
            - ``created_before`` : date
            - ``search``         : str  (full-text on title/description)

        Returns
        -------
        QuerySet[Case]
            Filtered, ``select_related`` queryset ready for serialisation.

        Role Scoping Rules
        ------------------
        - **Complainant / Base User**: sees only cases they are a
          complainant on.
        - **Cadet**: sees cases in ``COMPLAINT_REGISTERED`` or
          ``CADET_REVIEW`` status.
        - **Officer**: sees cases in ``OFFICER_REVIEW`` or above.
        - **Detective**: sees cases where
          ``assigned_detective == requesting_user``.
        - **Sergeant**: sees cases where
          ``assigned_sergeant == requesting_user`` or detective cases
          under their supervision.
        - **Captain / Chief / Admin**: unrestricted (all cases).
        - **Judge**: sees cases in ``JUDICIARY`` or ``CLOSED`` status
          that are assigned to them.

        Implementation Contract
        -----------------------
        1. Determine the user's highest-ranked role.
        2. Apply the appropriate scope filter.
        3. Apply explicit ``filters`` on top of the scoped queryset.
        4. ``select_related("created_by", "assigned_detective",
                            "assigned_sergeant", "assigned_captain")``.
        5. Return queryset.
        """
        raise NotImplementedError


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
        raise NotImplementedError

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
        raise NotImplementedError


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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError


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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError


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
        raise NotImplementedError

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
        raise NotImplementedError


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
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════
#  Case Calculation Service
# ═══════════════════════════════════════════════════════════════════


class CaseCalculationService:
    """
    Houses the two core formulas from project-doc §4.7.

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

            threshold = max(L_j) × max(D_i)

        At the case level this simplifies to::

            threshold = case.crime_level × days_since_creation

        Parameters
        ----------
        case : Case
            The case to compute the threshold for.

        Returns
        -------
        int
            The tracking threshold value.

        Implementation Contract
        -----------------------
        1. ``degree = case.crime_level``  (already stores the int 1–4).
        2. ``days = (timezone.now().date() - case.created_at.date()).days``.
        3. Return ``degree * days``.

        Notes
        -----
        - When the suspects app is fully wired, replace ``days_since_creation``
          with ``max(suspect.days_wanted for suspect in case.suspects.all())``.
        - The final "max across all cases" aggregation for the Most-Wanted page
          is performed in the *suspects* app, not here.
        """
        raise NotImplementedError

    @staticmethod
    def calculate_reward(case: Case) -> int:
        """
        Compute the **Bounty Reward** for information leading to a suspect
        on this case.

        Formula (project-doc §4.7 Note 2)::

            reward = max(L_j) × max(D_i) × 20,000,000  (Rials)

        Parameters
        ----------
        case : Case
            The case to compute the reward for.

        Returns
        -------
        int
            The reward amount in Rials.

        Implementation Contract
        -----------------------
        1. ``threshold = CaseCalculationService.calculate_tracking_threshold(case)``.
        2. Return ``threshold * _REWARD_MULTIPLIER``.
        """
        raise NotImplementedError

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

        Implementation Contract
        -----------------------
        Delegate to ``calculate_tracking_threshold`` and ``calculate_reward``;
        include the two sub-inputs for transparency.
        """
        raise NotImplementedError
