"""
Core app services — **Service Layer**.

Contains cross-app aggregation and search logic.  Views delegate all
business logic to the service classes defined here, keeping views thin
and ensuring testability.

╔══════════════════════════════════════════════════════════════════════╗
║  CROSS-APP IMPORT RULEBOOK                                         ║
║                                                                    ║
║  The core app is the ONLY app allowed to query models from other   ║
║  apps.  To prevent circular imports at module load time:           ║
║                                                                    ║
║  1. NEVER import models from other apps at the **module level**.   ║
║     Always import inside the method/function that needs them.      ║
║                                                                    ║
║  2. Preferred pattern:                                             ║
║       from django.apps import apps                                 ║
║       Case = apps.get_model("cases", "Case")                      ║
║                                                                    ║
║     OR, when type hints are needed at module level, use            ║
║     ``TYPE_CHECKING``:                                             ║
║       from __future__ import annotations                           ║
║       from typing import TYPE_CHECKING                             ║
║       if TYPE_CHECKING:                                            ║
║           from cases.models import Case                            ║
║                                                                    ║
║  3. Choice/enum classes (e.g. CrimeLevel, CaseStatus) live in     ║
║     the respective app's ``models.py`` alongside the models.       ║
║     Import them lazily inside methods too.                          ║
║                                                                    ║
║  4. Use ``select_related`` / ``prefetch_related`` to minimise DB   ║
║     queries when aggregating across apps.                          ║
║                                                                    ║
║  5. For heavy aggregations, prefer Django ORM ``.aggregate()``     ║
║     and ``.values().annotate()`` over Python-side loops.           ║
║                                                                    ║
║  Following these rules guarantees:                                 ║
║    • No import cycles at any point.                                ║
║    • Safe ``makemigrations`` / ``migrate`` regardless of app       ║
║      registration order.                                           ║
║    • Easy unit-testing via model mocking.                          ║
╚══════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, TYPE_CHECKING

from django.apps import apps
from django.db.models import (
    Count,
    ExpressionWrapper,
    F,
    FloatField,
    IntegerField,
    Max,
    Q,
    QuerySet,
    Value,
)
from django.db.models.functions import Cast, Coalesce, Greatest, Now
from django.utils import timezone

from core.constants import REWARD_MULTIPLIER
from core.domain.access import apply_permission_scope
from core.permissions_constants import CasesPerms, CorePerms

if TYPE_CHECKING:
    from accounts.models import User


# ════════════════════════════════════════════════════════════════════
#  Reward Calculator Service — Single Source of Truth
# ════════════════════════════════════════════════════════════════════

class RewardCalculatorService:
    """
    **Single Source of Truth** for all Most-Wanted ranking and reward
    calculations.

    Both the ``cases`` and ``suspects`` apps MUST delegate to this
    service instead of computing formulas independently, ensuring
    mathematical consistency across the entire system.

    Formulas (project-doc §4.7)
    ---------------------------
    **Score** (tracking threshold / ranking):

    .. math::

        \\text{score} = \\max(L_j) \\times \\max(D_i)

    Where:
        - :math:`L_j` = days the suspect has been wanted in each
          *open* case (computed from ``Suspect.wanted_since``).
        - :math:`D_i` = crime degree (``Case.crime_level``, 1–4)
          across *all* cases (open or closed) the suspect is linked to.

    **Reward** (bounty in Rials):

    .. math::

        \\text{reward} = \\text{score} \\times 20\\,000\\,000

    **Most-Wanted eligibility**:
        A suspect qualifies when they have been in the ``wanted``
        status for **strictly more than 30 days** AND are linked to
        at least one **open** case.

    Constants
    ---------
    - ``REWARD_MULTIPLIER`` — imported from ``core.constants``
      (currently 20,000,000 Rials).
    - ``MOST_WANTED_THRESHOLD_DAYS`` — 30 days.
    """

    #: Number of days after which a suspect is eligible for Most-Wanted.
    MOST_WANTED_THRESHOLD_DAYS: int = 30

    # ── Pure calculation helpers ────────────────────────────────────

    @staticmethod
    def compute_days_wanted(wanted_since) -> int:
        """
        Compute the number of days a suspect has been wanted.

        Parameters
        ----------
        wanted_since : datetime
            The ``Suspect.wanted_since`` timestamp.

        Returns
        -------
        int
            Non-negative day count.
        """
        return max((timezone.now() - wanted_since).days, 0)

    @staticmethod
    def compute_score(max_days_wanted: int, max_crime_degree: int) -> int:
        """
        Compute the Most-Wanted ranking score.

        Parameters
        ----------
        max_days_wanted : int
            Maximum ``days_wanted`` across all *open* cases for
            the suspect (grouped by ``national_id``).
        max_crime_degree : int
            Maximum ``case.crime_level`` (1–4) across *all* cases
            (open or closed) for the suspect.

        Returns
        -------
        int
            ``max_days_wanted × max_crime_degree``.
        """
        return max_days_wanted * max_crime_degree

    @staticmethod
    def compute_reward(score: int) -> int:
        """
        Compute the bounty reward in Rials.

        Parameters
        ----------
        score : int
            The Most-Wanted score (from ``compute_score``).

        Returns
        -------
        int
            ``score × REWARD_MULTIPLIER`` (Rials).
        """
        return score * REWARD_MULTIPLIER

    @staticmethod
    def is_most_wanted(days_wanted: int) -> bool:
        """
        Determine whether a suspect qualifies for the Most Wanted page.

        Parameters
        ----------
        days_wanted : int
            Number of days the suspect has been wanted.

        Returns
        -------
        bool
            ``True`` when ``days_wanted`` is **strictly greater** than
            ``MOST_WANTED_THRESHOLD_DAYS`` (30).
        """
        return days_wanted > RewardCalculatorService.MOST_WANTED_THRESHOLD_DAYS

    # ── Per-case threshold (used by CaseCalculationService) ─────────

    @staticmethod
    def compute_case_tracking_threshold(crime_level: int, days: int) -> int:
        """
        Compute the tracking threshold for a single case.

        This is the case-level simplification of the score formula
        where ``max(D_i)`` reduces to the case's own crime level, and
        ``max(L_j)`` reduces to the number of days since the case was
        created (or the suspect's wanted_since in that case).

        Parameters
        ----------
        crime_level : int
            ``Case.crime_level`` integer (1–4).
        days : int
            Days elapsed (since creation or since wanted).

        Returns
        -------
        int
            ``crime_level × max(days, 0)``.
        """
        return crime_level * max(days, 0)

    @staticmethod
    def compute_case_reward(crime_level: int, days: int) -> int:
        """
        Compute the bounty reward for a single case.

        Parameters
        ----------
        crime_level : int
        days : int

        Returns
        -------
        int
            ``threshold × REWARD_MULTIPLIER``.
        """
        threshold = RewardCalculatorService.compute_case_tracking_threshold(
            crime_level, days,
        )
        return threshold * REWARD_MULTIPLIER


# ════════════════════════════════════════════════════════════════════
#  Dashboard Aggregation Service
# ════════════════════════════════════════════════════════════════════

class DashboardAggregationService:
    """
    Produces an aggregated statistics dict consumed by
    ``DashboardStatsSerializer``.

    The statistics are **role-aware**:

    * **Police Chief / Captain / System Admin (superuser)**:
      Department-wide aggregate statistics across all cases, suspects,
      and evidence.
    * **Detective**:
      Statistics scoped to cases where the requesting user is the
      ``assigned_detective``.
    * **Sergeant**:
      Statistics scoped to cases where the requesting user is the
      ``assigned_sergeant``.
    * **Other authenticated roles** (Cadet, Officer, Coroner, Judge,
      Complainant, Base User, etc.):
      Limited public-facing statistics only (total solved cases, total
      employees, number of active cases).
    """

    #: Maximum number of top-wanted suspects to return.
    TOP_WANTED_LIMIT: int = 10

    #: Maximum number of recent activity items to return.
    RECENT_ACTIVITY_LIMIT: int = 20

    #: Permission-based scope rules for dashboard case scoping.
    _DASHBOARD_SCOPE_RULES: list[tuple[str, Any]] = [
        (f"core.{CorePerms.CAN_VIEW_FULL_DASHBOARD}", lambda qs, u: qs),
        (f"cases.{CasesPerms.CAN_SCOPE_SUPERVISED_CASES}",
         lambda qs, u: qs.filter(
             Q(assigned_sergeant=u) | Q(assigned_detective__isnull=False)
         )),
        (f"cases.{CasesPerms.CAN_SCOPE_ASSIGNED_CASES}",
         lambda qs, u: qs.filter(assigned_detective=u)),
    ]

    def __init__(self, user: User) -> None:
        self.user = user

    # ── Public API ──────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Return the full dashboard statistics dictionary."""
        from cases.models import CaseStatus

        case_qs = self._get_case_queryset()

        # Single aggregate query for scalar counts
        aggregates = case_qs.aggregate(
            total_cases=Count("id"),
            active_cases=Count(
                "id",
                filter=~Q(status__in=[CaseStatus.CLOSED, CaseStatus.VOIDED]),
            ),
            closed_cases=Count(
                "id",
                filter=Q(status=CaseStatus.CLOSED),
            ),
            voided_cases=Count(
                "id",
                filter=Q(status=CaseStatus.VOIDED),
            ),
        )

        Evidence = apps.get_model("evidence", "Evidence")
        Suspect = apps.get_model("suspects", "Suspect")

        # Scope suspects/evidence to the same cases the user can see
        case_ids_qs = case_qs.values_list("id", flat=True)
        total_suspects = Suspect.objects.filter(case_id__in=case_ids_qs).count()
        total_evidence = Evidence.objects.filter(case_id__in=case_ids_qs).count()

        return {
            "total_cases": aggregates["total_cases"],
            "active_cases": aggregates["active_cases"],
            "closed_cases": aggregates["closed_cases"],
            "voided_cases": aggregates["voided_cases"],
            "total_suspects": total_suspects,
            "total_evidence": total_evidence,
            "total_employees": self._get_employee_count(),
            "unassigned_evidence_count": self._get_unassigned_evidence_count(case_qs),
            "cases_by_status": self._get_cases_by_status(case_qs),
            "cases_by_crime_level": self._get_cases_by_crime_level(case_qs),
            "top_wanted_suspects": self._get_top_wanted_suspects(),
            "recent_activity": self._get_recent_activity(),
        }

    # ── Private helpers ─────────────────────────────────────────────

    def _get_case_queryset(self) -> QuerySet:
        """Return a ``Case`` queryset scoped to the requesting user's permissions."""
        Case = apps.get_model("cases", "Case")
        qs = Case.objects.all()
        return apply_permission_scope(
            qs,
            self.user,
            scope_rules=self._DASHBOARD_SCOPE_RULES,
            default="all",
        )

    def _get_cases_by_status(self, case_qs: QuerySet) -> list[dict[str, Any]]:
        """Group ``case_qs`` by status and return a list of dicts."""
        from cases.models import CaseStatus

        status_label_map = dict(CaseStatus.choices)
        rows = (
            case_qs
            .values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        return [
            {
                "status": row["status"],
                "label": status_label_map.get(row["status"], row["status"]),
                "count": row["count"],
            }
            for row in rows
        ]

    def _get_cases_by_crime_level(
        self,
        case_qs: QuerySet,
    ) -> list[dict[str, Any]]:
        """Group ``case_qs`` by crime level and return a list of dicts."""
        from cases.models import CrimeLevel

        level_label_map = dict(CrimeLevel.choices)
        rows = (
            case_qs
            .values("crime_level")
            .annotate(count=Count("id"))
            .order_by("crime_level")
        )
        return [
            {
                "crime_level": row["crime_level"],
                "label": level_label_map.get(row["crime_level"], str(row["crime_level"])),
                "count": row["count"],
            }
            for row in rows
        ]

    def _get_top_wanted_suspects(self) -> list[dict[str, Any]]:
        """Return the top N most-wanted suspects ordered by score descending.

        Uses the DB-level annotated queryset from
        ``SuspectProfileService.get_most_wanted_list()`` to avoid the
        N+1 caused by the ``most_wanted_score`` property.
        """
        from suspects.services import SuspectProfileService

        qs = (
            SuspectProfileService.get_most_wanted_list()
            [:self.TOP_WANTED_LIMIT]
        )

        return [
            {
                "id": s.pk,
                "full_name": s.full_name,
                "national_id": s.national_id,
                "photo_url": s.photo.url if s.photo else None,
                "most_wanted_score": s.computed_score,
                "reward_amount": s.computed_reward,
                "days_wanted": s.computed_days_wanted,
                "case_id": s.case_id,
                "case_title": s.case.title,
            }
            for s in qs
        ]

    def _get_recent_activity(self) -> list[dict[str, Any]]:
        """Return the latest activity feed items."""
        CaseStatusLog = apps.get_model("cases", "CaseStatusLog")

        log_qs = CaseStatusLog.objects.select_related("changed_by", "case")

        # Scope activity to user's visible cases unless they have full access
        if not self.user.has_perm(f"core.{CorePerms.CAN_VIEW_FULL_DASHBOARD}"):
            visible_case_ids = self._get_case_queryset().values_list("id", flat=True)
            log_qs = log_qs.filter(case_id__in=visible_case_ids)

        logs = log_qs.order_by("-created_at")[: self.RECENT_ACTIVITY_LIMIT]

        return [
            {
                "timestamp": log.created_at,
                "type": "case_status_change",
                "description": (
                    f"Case #{log.case_id} moved from "
                    f"{log.from_status} to {log.to_status}"
                ),
                "actor": (
                    log.changed_by.username if log.changed_by else None
                ),
            }
            for log in logs
        ]

    def _get_employee_count(self) -> int:
        """Return the total number of organisation employees (staff users)."""
        User = apps.get_model("accounts", "User")
        return User.objects.filter(role__hierarchy_level__gt=0).count()

    def _get_unassigned_evidence_count(
        self,
        case_qs: QuerySet,
    ) -> int:
        """Count evidence items whose parent case has no assigned detective."""
        Evidence = apps.get_model("evidence", "Evidence")
        return (
            Evidence.objects
            .filter(
                case__in=case_qs,
                case__assigned_detective__isnull=True,
            )
            .count()
        )


# ════════════════════════════════════════════════════════════════════
#  Global Search Service
# ════════════════════════════════════════════════════════════════════

class GlobalSearchService:
    """
    Performs a unified search across Cases, Suspects, and Evidence,
    returning categorised results.

    * **Security**: Results are filtered based on the requesting user's
      permissions.  A Detective only sees cases/suspects/evidence they
      have access to; a Captain sees everything.
    """

    #: Default maximum results per category.
    DEFAULT_LIMIT: int = 10

    #: Absolute maximum results per category (guard against abuse).
    MAX_LIMIT: int = 50

    #: Minimum query length.
    MIN_QUERY_LENGTH: int = 2

    #: Permission-based scope rules for search case scoping.
    _SEARCH_SCOPE_RULES: list[tuple[str, Any]] = [
        (f"core.{CorePerms.CAN_SEARCH_ALL}", lambda qs, u: qs),
        (f"cases.{CasesPerms.CAN_SCOPE_SUPERVISED_CASES}",
         lambda qs, u: qs.filter(
             Q(assigned_sergeant=u) | Q(assigned_detective__isnull=False)
         )),
        (f"cases.{CasesPerms.CAN_SCOPE_ASSIGNED_CASES}",
         lambda qs, u: qs.filter(assigned_detective=u)),
    ]

    def __init__(
        self,
        query: str,
        user: User,
        category: str | None = None,
        limit: int = DEFAULT_LIMIT,
    ) -> None:
        self.query = query.strip()
        self.user = user
        self.category = category
        self.limit = min(limit, self.MAX_LIMIT)

    # ── Public API ──────────────────────────────────────────────────

    def search(self) -> dict[str, Any]:
        """Execute the search and return the unified result dict."""
        cases: list[dict[str, Any]] = []
        suspects: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []

        if len(self.query) < self.MIN_QUERY_LENGTH:
            return {
                "query": self.query,
                "total_results": 0,
                "cases": cases,
                "suspects": suspects,
                "evidence": evidence,
            }

        if self.category is None or self.category == "cases":
            cases = self._search_cases()
        if self.category is None or self.category == "suspects":
            suspects = self._search_suspects()
        if self.category is None or self.category == "evidence":
            evidence = self._search_evidence()

        return {
            "query": self.query,
            "total_results": len(cases) + len(suspects) + len(evidence),
            "cases": cases,
            "suspects": suspects,
            "evidence": evidence,
        }

    # ── Private helpers ─────────────────────────────────────────────

    def _search_cases(self) -> list[dict[str, Any]]:
        """Search ``Case`` records by title and description."""
        from cases.models import CrimeLevel

        Case = apps.get_model("cases", "Case")
        qs = Case.objects.all()
        qs = apply_permission_scope(
            qs,
            self.user,
            scope_rules=self._SEARCH_SCOPE_RULES,
            default="all",
        )
        qs = qs.filter(
            Q(title__icontains=self.query)
            | Q(description__icontains=self.query)
        )

        level_label_map = dict(CrimeLevel.choices)
        results = []
        for case in qs[: self.limit]:
            results.append({
                "id": case.pk,
                "title": case.title,
                "status": case.status,
                "crime_level": case.crime_level,
                "crime_level_label": level_label_map.get(
                    case.crime_level, str(case.crime_level),
                ),
                "created_at": case.created_at,
            })
        return results

    def _search_suspects(self) -> list[dict[str, Any]]:
        """Search ``Suspect`` records by full name, national ID, and description."""
        Suspect = apps.get_model("suspects", "Suspect")

        accessible_ids = self._get_accessible_case_ids()
        qs = Suspect.objects.select_related("case")
        if accessible_ids is not None:
            qs = qs.filter(case_id__in=accessible_ids)

        qs = qs.filter(
            Q(full_name__icontains=self.query)
            | Q(national_id__icontains=self.query)
            | Q(description__icontains=self.query)
        )

        results = []
        for suspect in qs[: self.limit]:
            results.append({
                "id": suspect.pk,
                "full_name": suspect.full_name,
                "national_id": suspect.national_id,
                "status": suspect.status,
                "case_id": suspect.case_id,
                "case_title": suspect.case.title,
            })
        return results

    def _search_evidence(self) -> list[dict[str, Any]]:
        """Search ``Evidence`` records by title and description."""
        from evidence.models import EvidenceType

        Evidence = apps.get_model("evidence", "Evidence")

        accessible_ids = self._get_accessible_case_ids()
        qs = Evidence.objects.select_related("case")
        if accessible_ids is not None:
            qs = qs.filter(case_id__in=accessible_ids)

        qs = qs.filter(
            Q(title__icontains=self.query)
            | Q(description__icontains=self.query)
        )

        type_label_map = dict(EvidenceType.choices)
        results = []
        for ev in qs[: self.limit]:
            results.append({
                "id": ev.pk,
                "title": ev.title,
                "evidence_type": ev.evidence_type,
                "evidence_type_label": type_label_map.get(
                    ev.evidence_type, ev.evidence_type,
                ),
                "case_id": ev.case_id,
                "case_title": ev.case.title,
            })
        return results

    def _get_accessible_case_ids(self) -> QuerySet | None:
        """
        Return a queryset of Case PKs the user is allowed to see, or
        ``None`` if the user has unrestricted access.
        """
        if self.user.has_perm(f"core.{CorePerms.CAN_SEARCH_ALL}"):
            return None

        Case = apps.get_model("cases", "Case")
        qs = Case.objects.all()
        scoped = apply_permission_scope(
            qs,
            self.user,
            scope_rules=self._SEARCH_SCOPE_RULES,
            default="all",
        )
        return scoped.values_list("id", flat=True)


# ════════════════════════════════════════════════════════════════════
#  System Constants Service
# ════════════════════════════════════════════════════════════════════

class SystemConstantsService:
    """
    Gathers all system-wide choice enumerations and role hierarchies
    into a single dict for the frontend.

    This service is **stateless** — it does not depend on the requesting
    user.  All constants are public information needed by the frontend
    to render dropdowns and labels.
    """

    @staticmethod
    def get_constants() -> dict[str, Any]:
        """Return all system constants as a dict."""
        from cases.models import (
            CaseCreationType,
            CaseStatus,
            ComplainantStatus,
            CrimeLevel,
        )
        from evidence.models import EvidenceType, FileType
        from suspects.models import BountyTipStatus, SuspectStatus, VerdictChoice

        Role = apps.get_model("accounts", "Role")

        to_list = SystemConstantsService._choices_to_list

        roles = list(
            Role.objects
            .order_by("-hierarchy_level")
            .values("id", "name", "hierarchy_level")
        )

        return {
            "crime_levels": to_list(CrimeLevel),
            "case_statuses": to_list(CaseStatus),
            "case_creation_types": to_list(CaseCreationType),
            "evidence_types": to_list(EvidenceType),
            "evidence_file_types": to_list(FileType),
            "suspect_statuses": to_list(SuspectStatus),
            "verdict_choices": to_list(VerdictChoice),
            "bounty_tip_statuses": to_list(BountyTipStatus),
            "complainant_statuses": to_list(ComplainantStatus),
            "role_hierarchy": roles,
        }

    @staticmethod
    def _choices_to_list(
        choices_class: type,
    ) -> list[dict[str, str]]:
        """
        Convert a Django ``TextChoices`` or ``IntegerChoices`` class to
        a list of ``{"value": ..., "label": ...}`` dicts.
        """
        return [
            {"value": str(value), "label": str(label)}
            for value, label in choices_class.choices
        ]


# ═══════════════════════════════════════════════════════════════════
#  Notification Service
# ═══════════════════════════════════════════════════════════════════

class NotificationService:
    """
    Handles listing and marking notifications as read for a given user.
    """

    def __init__(self, user: Any) -> None:
        self.user = user

    def list_notifications(self) -> Any:
        """Return all notifications for ``self.user``, ordered most recent first."""
        from core.models import Notification

        return (
            Notification.objects
            .filter(recipient=self.user)
            .select_related("content_type")
            .order_by("-created_at")
        )

    def mark_as_read(self, notification_id: int) -> Any:
        """Mark a single notification as read."""
        from core.models import Notification

        notification = Notification.objects.get(
            pk=notification_id,
            recipient=self.user,
        )
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return notification
